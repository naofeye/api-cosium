"""Cosium proxy helpers for cosium_document_query_service.

Handles authenticated connector retrieval and document download via the
Cosium API (with local MinIO fallback).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services.erp_sync_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("cosium_document_query_helpers")


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
    from app.models.cosium_data import CosiumDocument

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
        except Exception as exc:
            logger.warning("local_doc_fallback_to_cosium", document_id=document_id, error=str(exc), error_type=type(exc).__name__)
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
