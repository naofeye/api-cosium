from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("optiflow", broker=settings.redis_url or "redis://redis:6379/0")
celery_app.autodiscover_tasks(["app.tasks"])

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
