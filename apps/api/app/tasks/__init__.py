from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure

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
}
celery_app.conf.timezone = "Europe/Paris"


# --- Dead-letter queue : log structure pour les taches qui depassent max_retries ---
# Le worker doit etre lance avec : -Q default,email,sync,extraction,batch,reminder,dlq
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
