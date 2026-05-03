import time

from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure, task_postrun, task_prerun

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("celery")

celery_app = Celery("optiflow", broker=settings.redis_url or "redis://redis:6379/0")
celery_app.autodiscover_tasks(["app.tasks"])

# --- Defaults globaux (voir docs/CELERY.md) ---
# acks_late=True : ack apres execution → resilience crash worker (tache replayee)
# task_reject_on_worker_lost=True : un worker SIGKILL renvoie en queue
# soft/hard time limits : eviter qu'une tache pendue bloque un worker eternellement
# task_default_queue / DLQ : routing par defaut + queue dead-letter pour analyse
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=300,   # 5 min : SoftTimeLimitExceeded levable
    task_time_limit=360,        # 6 min : SIGKILL force
    task_default_queue="default",
    task_routes={
        "app.tasks.email_tasks.*": {"queue": "email"},
        "app.tasks.sync_tasks.*": {"queue": "sync"},
        "app.tasks.extraction_tasks.*": {"queue": "extraction"},
        "app.tasks.batch_tasks.*": {"queue": "batch"},
        "app.tasks.reminder_tasks.*": {"queue": "reminder"},
    },
    # Cleanup resultats apres 24h pour eviter de remplir Redis
    result_expires=86400,
)

celery_app.conf.beat_schedule = {
    # Heartbeat : detecte si le scheduler est mort (voir /api/v1/admin/beat-status)
    "beat-heartbeat": {
        "task": "app.tasks.heartbeat_tasks.beat_heartbeat",
        "schedule": crontab(minute="*"),  # chaque minute
    },
    # NOTE: Pas de relance automatique — l'utilisateur veut valider avant tout envoi client
    # Les relances sont uniquement manuelles via la page Relances
    "sync-cosium-daily": {
        "task": "app.tasks.sync_tasks.sync_all_tenants",
        "schedule": crontab(hour=6, minute=0),  # Every day at 6 AM
    },
    "test-cosium-connection": {
        "task": "app.tasks.sync_tasks.test_cosium_connection",
        "schedule": crontab(minute=0, hour="*/4"),  # Every 4 hours
    },
    "check-expiring-prescriptions": {
        "task": "app.tasks.sync_tasks.check_expiring_prescriptions",
        "schedule": crontab(hour=10, minute=0, day_of_week=1),  # Monday 10 AM
    },
    "purge-refresh-tokens": {
        "task": "app.tasks.cleanup_tasks.purge_refresh_tokens",
        "schedule": crontab(hour=3, minute=30),  # Daily 3:30 AM
    },
    "apply-retention-policy": {
        "task": "app.tasks.cleanup_tasks.apply_retention_policy",
        "schedule": crontab(hour=3, minute=45),  # Daily 3:45 AM
    },
    "weekly-report": {
        "task": "app.tasks.weekly_report_tasks.send_weekly_reports",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Lundi 8h
    },
    "expire-devis": {
        "task": "app.tasks.devis_tasks.expire_devis",
        "schedule": crontab(hour=3, minute=15),  # Quotidien 3h15
    },
    # PEC V12 : rejoue le matching customer_id pour les factures orphelines.
    # Tourne avant la sync Cosium (6h) pour matcher d'abord les nouveaux
    # clients importes la veille via le sync precedent.
    "reconcile-orphan-invoices": {
        "task": "app.tasks.orphan_invoice_task.reconcile_all_tenants_orphans",
        "schedule": crontab(hour=4, minute=15),  # Quotidien 4h15
    },
}
celery_app.conf.timezone = "Europe/Paris"


# --- Dead-letter queue : log structure pour les taches qui depassent max_retries ---
# Le worker doit etre lance avec : -Q default,email,sync,extraction,batch,reminder,dlq
# --- Profiling : duree + RSS memoire par tache, alerte si > 60s ou > 500MB ---
_task_start_times: dict[str, float] = {}


@task_prerun.connect
def _on_task_prerun(task_id=None, task=None, **kw):
    if task_id:
        _task_start_times[task_id] = time.time()


@task_postrun.connect
def _on_task_postrun(task_id=None, task=None, retval=None, state=None, **kw):
    if not task_id or task_id not in _task_start_times:
        return
    duration = time.time() - _task_start_times.pop(task_id)
    rss_mb: float | None = None
    try:
        import resource  # unix only
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_mb = rss / 1024.0  # ru_maxrss is KB on linux
    except (ImportError, AttributeError):
        pass
    level = "warning" if duration > 60 or (rss_mb and rss_mb > 500) else "info"
    log_method = logger.warning if level == "warning" else logger.info
    log_method(
        "celery_task_profile",
        task=task.name if task else "unknown",
        task_id=task_id,
        duration_s=round(duration, 3),
        rss_mb=round(rss_mb, 1) if rss_mb else None,
        state=state,
    )


@task_failure.connect
def _on_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, **kw):
    """Capture toutes les failures pour Sentry + log structure (DLQ-like)."""
    logger.error(
        "celery_task_failed",
        task=sender.name if sender else "unknown",
        task_id=task_id,
        error=str(exception),
        error_type=type(exception).__name__ if exception else "unknown",
        args=str(args)[:500] if args else None,
        kwargs=str(kwargs)[:500] if kwargs else None,
    )
    # Sentry capture automatique via celery integration si SENTRY_DSN configure


# Import explicite des modules de taches pour que les decorateurs @celery_app.task
# enregistrent les taches dans le registre au demarrage du worker/beat.
# Sans ca, le worker lance avec `-A app.tasks` ne voit pas les taches.
from app.tasks import (  # noqa: E402, F401
    batch_tasks,
    cleanup_tasks,
    devis_tasks,
    email_tasks,
    extraction_tasks,
    heartbeat_tasks,
    reminder_tasks,
    sync_tasks,
    weekly_report_tasks,
)
