"""Service for downloading Cosium customer documents and storing them in MinIO.

Synchronization is UNIDIRECTIONAL: Cosium -> OptiFlow (read-only).
Documents are downloaded via GET only — no writes to Cosium.

Rate limiting is enforced to avoid overloading the Cosium server:
- 1 second delay between document downloads (configurable)
- 2 seconds delay between customers (configurable)
"""

import re
import time
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.integrations.storage import StorageAdapter
from app.models.client import Customer
from app.models.cosium_data import CosiumDocument

logger = get_logger("cosium_document_sync")

BUCKET = "optiflow-docs"
KEY_PREFIX = "cosium-docs"


def _sanitize_filename(name: str) -> str:
    """Remove special characters from filename for safe MinIO key."""
    if not name:
        return "document"
    # Keep alphanumeric, dots, hyphens, underscores
    sanitized = re.sub(r"[^\w.\-]", "_", name)
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:200] if sanitized else "document"


def sync_customer_documents(
    db: Session,
    tenant_id: int,
    customer_cosium_id: int,
    connector: CosiumConnector,
    storage: StorageAdapter,
    delay_between_docs: float = 1.0,
) -> dict:
    """Download all documents for ONE customer from Cosium to MinIO.

    Returns: {"downloaded": N, "skipped": N, "errors": N}
    """
    downloaded = 0
    skipped = 0
    errors = 0

    # 1. List documents from Cosium API
    try:
        docs = connector.get_customer_documents(customer_cosium_id)
    except (ConnectionError, TimeoutError, OSError) as e:
        logger.error(
            "cosium_docs_list_failed",
            tenant_id=tenant_id,
            customer_cosium_id=customer_cosium_id,
            error=str(e),
        )
        return {"downloaded": 0, "skipped": 0, "errors": 1}

    if not docs:
        return {"downloaded": 0, "skipped": 0, "errors": 0}

    # 2. Load existing local docs for this customer to skip duplicates
    existing_doc_ids: set[int] = set(
        db.scalars(
            select(CosiumDocument.cosium_document_id).where(
                CosiumDocument.tenant_id == tenant_id,
                CosiumDocument.customer_cosium_id == customer_cosium_id,
            )
        ).all()
    )

    # Find matching local customer_id (if linked)
    customer_id: int | None = db.scalar(
        select(Customer.id).where(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id == str(customer_cosium_id),
        )
    )

    for doc in docs:
        doc_id = doc.get("document_id", 0)
        if not doc_id:
            continue

        # 2a. Skip if already downloaded
        if doc_id in existing_doc_ids:
            skipped += 1
            continue

        label = doc.get("label", "") or f"doc_{doc_id}"

        try:
            # 2b. Download content from Cosium (GET only)
            content = connector.get_document_content(customer_cosium_id, doc_id)
            if not content:
                logger.warning(
                    "cosium_doc_empty",
                    tenant_id=tenant_id,
                    customer_cosium_id=customer_cosium_id,
                    document_id=doc_id,
                )
                errors += 1
                continue

            # 2c. Upload to MinIO
            safe_name = _sanitize_filename(label)
            minio_key = f"{KEY_PREFIX}/{tenant_id}/{customer_cosium_id}/{doc_id}_{safe_name}"

            # Guess content type
            content_type = "application/pdf"
            lower_name = label.lower()
            if lower_name.endswith(".jpg") or lower_name.endswith(".jpeg"):
                content_type = "image/jpeg"
            elif lower_name.endswith(".png"):
                content_type = "image/png"
            elif lower_name.endswith(".tiff") or lower_name.endswith(".tif"):
                content_type = "image/tiff"

            storage.ensure_bucket(BUCKET)
            storage.upload_file(BUCKET, minio_key, content, content_type=content_type)

            # 2d. Create DB record
            record = CosiumDocument(
                tenant_id=tenant_id,
                customer_cosium_id=customer_cosium_id,
                customer_id=customer_id,
                cosium_document_id=doc_id,
                name=label[:500],
                content_type=content_type,
                size_bytes=len(content),
                minio_key=minio_key,
                synced_at=datetime.now(UTC),
            )
            db.add(record)
            db.flush()
            downloaded += 1

            # Batch commit every 50 documents
            if downloaded % 50 == 0:
                db.commit()

            logger.info(
                "cosium_doc_downloaded",
                tenant_id=tenant_id,
                customer_cosium_id=customer_cosium_id,
                document_id=doc_id,
                size_bytes=len(content),
            )

        except Exception as e:  # noqa: BLE001 — une erreur par doc ne doit pas aborter la sync
            db.rollback()
            logger.error(
                "cosium_doc_download_failed",
                tenant_id=tenant_id,
                customer_cosium_id=customer_cosium_id,
                document_id=doc_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            errors += 1

        # 2e. Rate limit between downloads
        if delay_between_docs > 0:
            time.sleep(delay_between_docs)

    # Final commit for remaining records
    if downloaded % 50 != 0:
        db.commit()

    return {"downloaded": downloaded, "skipped": skipped, "errors": errors}


def sync_all_documents(
    db: Session,
    tenant_id: int,
    user_id: int = 0,
    delay_between_customers: float = 2.0,
    delay_between_docs: float = 1.0,
    max_customers: int | None = None,
) -> dict:
    """Bulk download ALL customer documents from Cosium to MinIO.

    IMPORTANT: Designed to be SLOW to avoid overloading Cosium:
    - 1 second delay between document downloads
    - 2 seconds delay between customers
    - Progress logged every 10 customers

    Returns: {
        "customers_processed": N,
        "documents_downloaded": N,
        "documents_skipped": N,
        "errors": N,
    }
    """
    from app.integrations.storage import storage
    from app.services.erp_sync_service import _authenticate_connector, _get_connector_for_tenant

    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    if not isinstance(connector, CosiumConnector):
        logger.error("cosium_docs_sync_wrong_connector", tenant_id=tenant_id)
        return {
            "customers_processed": 0,
            "documents_downloaded": 0,
            "documents_skipped": 0,
            "errors": 1,
        }

    # Get all customers with cosium_id
    customers = db.scalars(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id.isnot(None),
            Customer.cosium_id != "",
        )
    ).all()

    total_customers = len(customers)
    if max_customers:
        customers = customers[:max_customers]

    logger.info(
        "cosium_docs_sync_start",
        tenant_id=tenant_id,
        total_customers=total_customers,
        processing=len(customers),
        max_customers=max_customers,
    )

    total_downloaded = 0
    total_skipped = 0
    total_errors = 0
    customers_processed = 0

    storage_adapter = storage  # module-level singleton

    # Pre-load already-processed customer IDs to skip them quickly (no API call)
    already_processed: set[int] = set(
        db.scalars(
            select(func.distinct(CosiumDocument.customer_cosium_id)).where(
                CosiumDocument.tenant_id == tenant_id,
            )
        ).all()
    )
    logger.info("cosium_docs_skip_already_processed", count=len(already_processed))

    for i, customer in enumerate(customers):
        cosium_id = int(customer.cosium_id)

        # Skip customers already fully processed (have at least 1 doc in DB)
        if cosium_id in already_processed:
            customers_processed += 1
            continue

        result = sync_customer_documents(
            db=db,
            tenant_id=tenant_id,
            customer_cosium_id=cosium_id,
            connector=connector,
            storage=storage_adapter,
            delay_between_docs=delay_between_docs,
        )

        total_downloaded += result["downloaded"]
        total_skipped += result["skipped"]
        total_errors += result["errors"]
        customers_processed += 1

        # Log progress every 10 customers
        if (i + 1) % 10 == 0 or (i + 1) == len(customers):
            logger.info(
                "cosium_docs_sync_progress",
                tenant_id=tenant_id,
                progress=f"{i + 1}/{len(customers)}",
                downloaded=total_downloaded,
                skipped=total_skipped,
                errors=total_errors,
            )

        # Rate limit between customers
        if delay_between_customers > 0 and (i + 1) < len(customers):
            time.sleep(delay_between_customers)

    logger.info(
        "cosium_docs_sync_complete",
        tenant_id=tenant_id,
        customers_processed=customers_processed,
        downloaded=total_downloaded,
        skipped=total_skipped,
        errors=total_errors,
    )

    return {
        "customers_processed": customers_processed,
        "documents_downloaded": total_downloaded,
        "documents_skipped": total_skipped,
        "errors": total_errors,
    }


def get_local_documents(
    db: Session, tenant_id: int, customer_cosium_id: int
) -> list[CosiumDocument]:
    """Get locally cached documents for a customer."""
    return list(
        db.scalars(
            select(CosiumDocument)
            .where(
                CosiumDocument.tenant_id == tenant_id,
                CosiumDocument.customer_cosium_id == customer_cosium_id,
            )
            .order_by(CosiumDocument.synced_at.desc())
        ).all()
    )


def get_sync_status(db: Session, tenant_id: int) -> dict:
    """Return progress info for document sync."""
    from sqlalchemy import func

    total_docs = db.scalar(
        select(func.count(CosiumDocument.id)).where(CosiumDocument.tenant_id == tenant_id)
    ) or 0

    total_customers_with_docs = db.scalar(
        select(func.count(func.distinct(CosiumDocument.customer_cosium_id))).where(
            CosiumDocument.tenant_id == tenant_id
        )
    ) or 0

    total_customers = db.scalar(
        select(func.count(Customer.id)).where(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id.isnot(None),
            Customer.cosium_id != "",
        )
    ) or 0

    total_size = db.scalar(
        select(func.sum(CosiumDocument.size_bytes)).where(CosiumDocument.tenant_id == tenant_id)
    ) or 0

    last_sync = db.scalar(
        select(func.max(CosiumDocument.synced_at)).where(CosiumDocument.tenant_id == tenant_id)
    )

    return {
        "total_documents": total_docs,
        "customers_with_docs": total_customers_with_docs,
        "total_customers": total_customers,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 1) if total_size else 0,
        "last_sync_at": last_sync.isoformat() if last_sync else None,
    }
