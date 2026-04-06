"""Celery tasks for asynchronous document extraction.

Tasks:
- extract_document: extract a single document by ID
- extract_all_client_documents: batch-extract all documents for a customer
"""

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("extraction_tasks")


@celery_app.task(
    name="app.tasks.extraction_tasks.extract_document",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def extract_document(self, tenant_id: int, document_id: int) -> dict:
    """Extract text from a single document (async Celery task)."""
    from app.db.session import SessionLocal
    from app.services import extraction_service

    db = SessionLocal()
    try:
        result = extraction_service.extract_document(db, tenant_id=tenant_id, document_id=document_id)
        logger.info("task_extract_document_done", document_id=document_id, doc_type=result.document_type)
        return {"document_id": document_id, "document_type": result.document_type, "status": "ok"}
    except Exception as exc:
        logger.error("task_extract_document_failed", document_id=document_id, error=str(exc))
        db.rollback()
        raise self.retry(exc=exc) from exc
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.extraction_tasks.extract_all_client_documents",
    bind=True,
    max_retries=1,
    default_retry_delay=120,
)
def extract_all_client_documents(self, tenant_id: int, customer_id: int) -> dict:
    """Batch-extract all documents for a customer across all their cases."""
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Case, Document
    from app.services import extraction_service

    db = SessionLocal()
    try:
        # Find all documents for this customer's cases
        case_ids = [
            row[0]
            for row in db.execute(
                select(Case.id).where(Case.customer_id == customer_id, Case.tenant_id == tenant_id)
            ).all()
        ]

        if not case_ids:
            logger.info("no_cases_for_customer", customer_id=customer_id)
            return {"customer_id": customer_id, "extracted": 0, "errors": 0}

        documents = db.execute(
            select(Document).where(Document.case_id.in_(case_ids), Document.tenant_id == tenant_id)
        ).scalars().all()

        extracted = 0
        errors = 0
        for doc in documents:
            try:
                extraction_service.extract_document(db, tenant_id=tenant_id, document_id=doc.id)
                extracted += 1
            except Exception as exc:
                logger.warning("batch_extract_doc_failed", document_id=doc.id, error=str(exc))
                db.rollback()
                errors += 1

        logger.info(
            "batch_extraction_done",
            customer_id=customer_id,
            extracted=extracted,
            errors=errors,
        )
        return {"customer_id": customer_id, "extracted": extracted, "errors": errors}
    except Exception as exc:
        logger.error("task_batch_extract_failed", customer_id=customer_id, error=str(exc))
        raise self.retry(exc=exc) from exc
    finally:
        db.close()
