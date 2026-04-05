"""Router for proxying Cosium document access (read-only).

All document content is proxied through the backend — the frontend
NEVER calls Cosium directly (CORS disabled on Cosium side).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.logging import get_logger
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.cosium_sync import CosiumDocumentList, CosiumDocumentResponse
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services.erp_sync_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("cosium_documents_router")

router = APIRouter(prefix="/api/v1/cosium-documents", tags=["cosium-documents"])


@router.get(
    "/{customer_cosium_id}",
    response_model=CosiumDocumentList,
    summary="Liste des documents d'un client Cosium",
    description="Retourne la liste des documents disponibles pour un client dans Cosium.",
)
def list_customer_documents(
    customer_cosium_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> CosiumDocumentList:
    connector, tenant = _get_connector_for_tenant(db, tenant_ctx.tenant_id)
    _authenticate_connector(connector, tenant)

    if not isinstance(connector, CosiumConnector):
        raise HTTPException(status_code=400, detail="Le connecteur ERP ne supporte pas les documents Cosium.")

    try:
        docs = connector.get_customer_documents(customer_cosium_id)
    except Exception as e:
        logger.error("cosium_documents_fetch_failed", customer_id=customer_cosium_id, error=str(e))
        raise HTTPException(status_code=502, detail="Impossible de recuperer les documents depuis Cosium.") from e

    items = [CosiumDocumentResponse(**d) for d in docs]
    return CosiumDocumentList(items=items, total=len(items))


@router.get(
    "/{customer_cosium_id}/{document_id}/download",
    summary="Telecharger un document Cosium",
    description="Proxy le telechargement du contenu d'un document depuis Cosium.",
)
def download_document(
    customer_cosium_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> Response:
    connector, tenant = _get_connector_for_tenant(db, tenant_ctx.tenant_id)
    _authenticate_connector(connector, tenant)

    if not isinstance(connector, CosiumConnector):
        raise HTTPException(status_code=400, detail="Le connecteur ERP ne supporte pas les documents Cosium.")

    try:
        content = connector.get_document_content(customer_cosium_id, document_id)
    except Exception as e:
        logger.error(
            "cosium_document_download_failed",
            customer_id=customer_cosium_id,
            document_id=document_id,
            error=str(e),
        )
        raise HTTPException(status_code=502, detail="Impossible de telecharger le document depuis Cosium.") from e

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=cosium_doc_{document_id}.pdf"},
    )
