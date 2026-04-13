"""Tests config Celery : routing par queue, time limits, dead-letter handler."""
from app.tasks import celery_app


def test_celery_acks_late_enabled():
    """acks_late=True garantit qu'une tache crashee est replayee (resilience)."""
    assert celery_app.conf.task_acks_late is True


def test_celery_reject_on_worker_lost():
    """SIGKILL sur worker doit renvoyer la tache en queue (pas perte silencieuse)."""
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_celery_time_limits():
    """Soft + hard time limits configures pour eviter taches pendues."""
    assert celery_app.conf.task_soft_time_limit == 300
    assert celery_app.conf.task_time_limit == 360
    # Hard > soft : laisse le temps de catch SoftTimeLimitExceeded
    assert celery_app.conf.task_time_limit > celery_app.conf.task_soft_time_limit


def test_celery_results_expire():
    """Resultats expirent apres 24h pour eviter de remplir Redis."""
    assert celery_app.conf.result_expires == 86400


def test_celery_routing_per_queue():
    """Chaque domaine a sa propre queue (isolation des charges)."""
    routes = celery_app.conf.task_routes
    assert routes["app.tasks.email_tasks.*"] == {"queue": "email"}
    assert routes["app.tasks.sync_tasks.*"] == {"queue": "sync"}
    assert routes["app.tasks.extraction_tasks.*"] == {"queue": "extraction"}
    assert routes["app.tasks.batch_tasks.*"] == {"queue": "batch"}
    assert routes["app.tasks.reminder_tasks.*"] == {"queue": "reminder"}


def test_celery_failure_handler_registered():
    """Le handler task_failure (DLQ) est connecte au signal Celery."""
    from celery.signals import task_failure
    receivers = task_failure.receivers
    assert len(receivers) > 0, "Aucun handler de failure enregistre"


def test_celery_beat_schedule_configured():
    """Au moins 3 taches planifiees (sync daily, cosium connection, prescriptions)."""
    schedule = celery_app.conf.beat_schedule
    assert "sync-cosium-daily" in schedule
    assert "test-cosium-connection" in schedule
    assert "check-expiring-prescriptions" in schedule


def test_celery_timezone_paris():
    """Timezone fixe a Europe/Paris pour beat schedule coherent."""
    assert celery_app.conf.timezone == "Europe/Paris"
