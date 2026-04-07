"""Celery tasks for async batch processing (Groupes marketing).

Large batches (50+ clients) can take minutes to consolidate.
This task runs the processing in the background so the API
returns immediately and the frontend polls for status.
"""

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("batch_tasks")


@celery_app.task(
    name="app.tasks.batch_tasks.process_batch_async",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def process_batch_async(self, tenant_id: int, batch_id: int, user_id: int) -> dict:
    """Process a batch operation asynchronously via Celery.

    The frontend should poll GET /api/v1/batch/{batch_id} to track progress.
    """
    from app.db.session import SessionLocal
    from app.services import batch_operation_service

    db = SessionLocal()
    try:
        logger.info(
            "batch_async_started",
            tenant_id=tenant_id,
            batch_id=batch_id,
            user_id=user_id,
        )

        result = batch_operation_service.process_batch(
            db,
            tenant_id=tenant_id,
            batch_id=batch_id,
            user_id=user_id,
        )

        logger.info(
            "batch_async_completed",
            tenant_id=tenant_id,
            batch_id=batch_id,
            prets=result.clients_prets,
            incomplets=result.clients_incomplets,
            erreurs=result.clients_erreur,
        )

        return {
            "batch_id": batch_id,
            "status": result.status,
            "total": result.total_clients,
            "prets": result.clients_prets,
            "incomplets": result.clients_incomplets,
            "erreurs": result.clients_erreur,
        }

    except Exception as exc:
        logger.error(
            "batch_async_failed",
            tenant_id=tenant_id,
            batch_id=batch_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)
    finally:
        db.close()
