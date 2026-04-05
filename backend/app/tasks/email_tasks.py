"""Celery tasks for asynchronous email delivery with automatic retry."""

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("email_tasks")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_async(self, to: str, subject: str, body_html: str) -> None:
    from app.integrations.email_sender import email_sender

    try:
        success = email_sender.send_email(to, subject, body_html)
        if not success:
            raise RuntimeError("Email send returned False")
        logger.info("email_sent_async", to=to, subject=subject)
    except Exception as exc:
        logger.warning("email_retry", to=to, attempt=self.request.retries, error=str(exc))
        self.retry(exc=exc)
