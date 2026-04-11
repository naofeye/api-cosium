"""Service for querying Cosium documents — DB queries and Cosium proxy logic.

Extracted from the cosium_documents router to keep business logic out of routers.
"""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

from app.core.exceptions import ExternalServiceError, NotFoundError
from app.core.logging import get_logger
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.models.client import Customer
from app.models.cosium_data import CosiumDocument
from app.models.document_extraction import DocumentExtraction
from app.services.erp_sync_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("cosium_document_query_service")


# ---------------------------------------------------------------------------
# Data containers (plain dicts returned to the router for serialisation)
# ---------------------------------------------------------------------------


def list_all_documents_paginated(
    db: Session,
    tenant_id: int,
    *,
    page: int = 1,
    page_size: int = 25,
    search: str | None = None,
    doc_type: str | None = None,
) -> dict:
    """Return a paginated list of all locally-synced Cosium documents.

    Returns a dict with keys: items (list[dict]), total, page, page_size,
    total_size_bytes, type_counts.
    """
    # Base query: left join with customer and extraction
    query = (
        sa_select(
            CosiumDocument,
            Customer.first_name,
            Customer.last_name,
            DocumentExtraction.document_type,
            DocumentExtraction.classification_confidence,
        )
        .outerjoin(
            Customer,
            (Customer.id == CosiumDocument.customer_id) & (Customer.tenant_id == tenant_id),
        )
        .outerjoin(
            DocumentExtraction,
            (DocumentExtraction.cosium_document_id == CosiumDocument.cosium_document_id)
            & (DocumentExtraction.tenant_id == tenant_id),
        )
        .where(CosiumDocument.tenant_id == tenant_id)
    )

    count_base = sa_select(func.count(CosiumDocument.id)).where(
        CosiumDocument.tenant_id == tenant_id,
    )

    if search:
        pattern = f"%{search}%"
        search_filter = or_(
            CosiumDocument.name.ilike(pattern),
            (Customer.first_name + " " + Customer.last_name).ilike(pattern),
            (Customer.last_name + " " + Customer.first_name).ilike(pattern),
        )
        query = query.where(search_filter)
        count_base = (
            sa_select(func.count(CosiumDocument.id))
            .outerjoin(
                Customer,
                (Customer.id == CosiumDocument.customer_id) & (Customer.tenant_id == tenant_id),
            )
            .where(CosiumDocument.tenant_id == tenant_id)
            .where(search_filter)
        )

    if doc_type:
        query = query.where(DocumentExtraction.document_type == doc_type)
        count_base = (
            sa_select(func.count(CosiumDocument.id))
            .outerjoin(
                DocumentExtraction,
                (DocumentExtraction.cosium_document_id == CosiumDocument.cosium_document_id)
                & (DocumentExtraction.tenant_id == tenant_id),
            )
            .where(CosiumDocument.tenant_id == tenant_id)
            .where(DocumentExtraction.document_type == doc_type)
        )

    total = db.scalar(count_base) or 0

    # Total size
    size_q = sa_select(func.coalesce(func.sum(CosiumDocument.size_bytes), 0)).where(
        CosiumDocument.tenant_id == tenant_id,
    )
    total_size = db.scalar(size_q) or 0

    # Type counts
    type_count_q = (
        sa_select(DocumentExtraction.document_type, func.count(DocumentExtraction.id))
        .join(
            CosiumDocument,
            (DocumentExtraction.cosium_document_id == CosiumDocument.cosium_document_id)
            & (DocumentExtraction.tenant_id == CosiumDocument.tenant_id),
        )
        .where(DocumentExtraction.tenant_id == tenant_id)
        .where(DocumentExtraction.document_type.isnot(None))
        .group_by(DocumentExtraction.document_type)
    )
    type_counts_raw = db.execute(type_count_q).all()
    type_counts = {str(row[0]): int(row[1]) for row in type_counts_raw if row[0]}

    # Paginate
    query = query.order_by(CosiumDocument.synced_at.desc())
    offset = (page - 1) * page_size
    rows = db.execute(query.offset(offset).limit(page_size)).all()

    items: list[dict] = []
    for row in rows:
        doc = row[0]
        first_name = row[1] or ""
        last_name = row[2] or ""
        d_type = row[3]
        d_confidence = row[4]
        customer_name = f"{first_name} {last_name}".strip() or None
        items.append(
            {
                "id": doc.id,
                "customer_cosium_id": doc.customer_cosium_id,
                "customer_id": doc.customer_id,
                "customer_name": customer_name,
                "cosium_document_id": doc.cosium_document_id,
                "name": doc.name,
                "content_type": doc.content_type,
                "size_bytes": doc.size_bytes,
                "document_type": d_type,
                "classification_confidence": d_confidence,
                "synced_at": doc.synced_at.isoformat() if doc.synced_at else None,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_size_bytes": int(total_size),
        "type_counts": type_counts,
    }


# ---------------------------------------------------------------------------
# Single-document download (local / MinIO)
# ---------------------------------------------------------------------------


def get_local_document_content(
    db: Session,
    tenant_id: int,
    document_id: int,
) -> tuple[bytes, str, str]:
    """Download a document from MinIO storage.

    Returns (content_bytes, content_type, filename).
    Raises NotFoundError if the document doesn't exist locally.
    Raises ExternalServiceError if the download from storage fails.
    """
    doc = (
        db.query(CosiumDocument)
        .filter(CosiumDocument.id == document_id, CosiumDocument.tenant_id == tenant_id)
        .first()
    )
    if not doc or not doc.minio_key:
        raise NotFoundError("Document", document_id)

    try:
        from app.integrations.storage import storage
        from app.services.cosium_document_sync import BUCKET

        content = storage.download_file(BUCKET, doc.minio_key)
    except Exception as e:
        logger.error("local_doc_download_failed", document_id=document_id, error=str(e))
        raise ExternalServiceError(
            message="Erreur lors du telechargement du document.",
            service="minio",
        ) from e

    safe_name = doc.name or f"document_{doc.cosium_document_id}"
    content_type = doc.content_type or "application/octet-stream"
    return content, content_type, safe_name


# ---------------------------------------------------------------------------
# Customer document extractions
# ---------------------------------------------------------------------------


def get_customer_extraction_ids(
    db: Session,
    tenant_id: int,
    customer_cosium_id: int,
) -> list[int]:
    """Return cosium_document_ids for a given customer."""
    return [
        row[0]
        for row in db.execute(
            sa_select(CosiumDocument.cosium_document_id).where(
                CosiumDocument.tenant_id == tenant_id,
                CosiumDocument.customer_cosium_id == customer_cosium_id,
            )
        ).all()
    ]


# ---------------------------------------------------------------------------
# Cosium proxy helpers
# ---------------------------------------------------------------------------


def _get_cosium_connector(db: Session, tenant_id: int) -> tuple[CosiumConnector, object]:
    """Obtain an authenticated CosiumConnector for the tenant.

    Raises ExternalServiceError if the connector type is wrong.
    """
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    if not isinstance(connector, CosiumConnector):
        raise ExternalServiceError(
            message="Le connecteur ERP ne supporte pas les documents Cosium.",
            service="cosium",
        )
    return connector, tenant


def list_customer_documents_from_cosium(
    db: Session,
    tenant_id: int,
    customer_cosium_id: int,
) -> list[dict]:
    """Fetch document list for a customer from Cosium API.

    Raises ExternalServiceError on failure.
    """
    connector, _tenant = _get_cosium_connector(db, tenant_id)

    try:
        return connector.get_customer_documents(customer_cosium_id)
    except Exception as e:
        logger.error(
            "cosium_documents_fetch_failed",
            customer_id=customer_cosium_id,
            error=str(e),
        )
        raise ExternalServiceError(
            message="Impossible de recuperer les documents depuis Cosium.",
            service="cosium",
        ) from e


def download_document_with_fallback(
    db: Session,
    tenant_id: int,
    customer_cosium_id: int,
    document_id: int,
) -> tuple[bytes, str, str]:
    """Download a document, trying local MinIO first then Cosium proxy.

    Returns (content_bytes, content_type, filename).
    Raises ExternalServiceError if both local and Cosium downloads fail.
    """
    # Check local cache first
    local_doc = (
        db.query(CosiumDocument)
        .filter(
            CosiumDocument.tenant_id == tenant_id,
            CosiumDocument.customer_cosium_id == customer_cosium_id,
            CosiumDocument.cosium_document_id == document_id,
        )
        .first()
    )

    if local_doc and local_doc.minio_key:
        try:
            from app.integrations.storage import storage
            from app.services.cosium_document_sync import BUCKET

            content = storage.download_file(BUCKET, local_doc.minio_key)
            safe_name = local_doc.name or f"cosium_doc_{document_id}.pdf"
            content_type = local_doc.content_type or "application/octet-stream"
            return content, content_type, safe_name
        except Exception:
            logger.warning("local_doc_fallback_to_cosium", document_id=document_id)
            # Fall through to Cosium proxy

    # Proxy from Cosium
    connector, _tenant = _get_cosium_connector(db, tenant_id)

    try:
        content = connector.get_document_content(customer_cosium_id, document_id)
    except Exception as e:
        logger.error(
            "cosium_document_download_failed",
            customer_id=customer_cosium_id,
            document_id=document_id,
            error=str(e),
        )
        raise ExternalServiceError(
            message="Impossible de telecharger le document depuis Cosium.",
            service="cosium",
        ) from e

    return content, "application/octet-stream", f"cosium_doc_{document_id}.pdf"
