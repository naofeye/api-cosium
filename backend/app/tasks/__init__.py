from celery import Celery

from app.core.config import settings

celery_app = Celery("optiflow", broker=settings.redis_url)
celery_app.autodiscover_tasks(["app.tasks"])
