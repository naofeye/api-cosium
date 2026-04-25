"""Task Celery : bulk_download_cosium_documents — téléchargement de masse MinIO."""

from celery.exceptions import SoftTimeLimitExceeded

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("sync_tasks")


@celery_app.task(
    name="app.tasks.sync_tasks.bulk_download_cosium_documents",
    bind=True,
    max_retries=0,
    soft_time_limit=25200,  # 7h — graceful stop
    time_limit=27000,       # 7h30 — hard kill safety net
    acks_late=False,        # ACK immediately: killed task must NOT be re-queued
)
def bulk_download_cosium_documents(
    self,
    tenant_id: int,
    user_id: int = 0,
    max_customers: int | None = None,
    delay_docs: float = 1.0,
    delay_customers: float = 2.0,
) -> dict:
    """Background task for bulk document download from Cosium to MinIO.

    Designed to run for hours. Rate-limited to avoid overloading Cosium.
    """
    from app.db.session import SessionLocal
    from app.services.cosium_document_sync import sync_all_documents

    db = SessionLocal()
    try:
        logger.info(
            "bulk_download_start",
            tenant_id=tenant_id,
            user_id=user_id,
            max_customers=max_customers,
        )
        result = sync_all_documents(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            delay_between_customers=delay_customers,
            delay_between_docs=delay_docs,
            max_customers=max_customers,
        )
        logger.info("bulk_download_complete", tenant_id=tenant_id, result=result)
        return result
    except SoftTimeLimitExceeded:
        logger.warning(
            "bulk_download_soft_timeout",
            tenant_id=tenant_id,
            msg="7h soft limit reached — stopping gracefully. "
            "Re-run to resume (already-processed customers are skipped).",
        )
        return {"error": "soft_time_limit", "resumable": True}
    except Exception as e:
        logger.error("bulk_download_failed", tenant_id=tenant_id, error=str(e))
        from app.core.sentry_helpers import report_incident_to_sentry

        report_incident_to_sentry(
            e,
            "cosium_bulk_download_failed",
            category="sync",
            tenant_id=tenant_id,
        )
        return {"error": str(e)}
    finally:
        db.close()
