"""Parsing/transform helpers for Cosium document sync.

Extracted from cosium_document_sync.py to keep files under 300 lines.
Contains: filename sanitization, content type detection, sync status query.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.client import Customer
from app.models.cosium_data import CosiumDocument


def sanitize_filename(name: str) -> str:
    """Remove special characters from filename for safe MinIO key."""
    if not name:
        return "document"
    # Keep alphanumeric, dots, hyphens, underscores
    sanitized = re.sub(r"[^\w.\-]", "_", name)
    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized[:200] if sanitized else "document"


def guess_content_type(label: str) -> str:
    """Guess MIME content type from document label/filename."""
    content_type = "application/pdf"
    lower_name = label.lower()
    if lower_name.endswith(".jpg") or lower_name.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif lower_name.endswith(".png"):
        content_type = "image/png"
    elif lower_name.endswith(".tiff") or lower_name.endswith(".tif"):
        content_type = "image/tiff"
    return content_type


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
