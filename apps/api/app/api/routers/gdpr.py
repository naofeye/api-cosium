from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.gdpr import AnonymizeResponse, ClientDataResponse
from app.services import gdpr_service

router = APIRouter(prefix="/api/v1/gdpr", tags=["gdpr"])


@router.get(
    "/clients/{client_id}/data",
    response_model=ClientDataResponse,
    summary="Donnees personnelles d'un client",
    description="Retourne toutes les donnees personnelles d'un client (droit d'acces RGPD).",
)
def get_client_data(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> ClientDataResponse:
    return gdpr_service.get_client_data(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/clients/{client_id}/export",
    summary="Exporter les donnees RGPD",
    description="Exporte les donnees personnelles d'un client au format JSON (portabilite).",
)
def export_client_data(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> Response:
    data = gdpr_service.export_client_data(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
        user_id=tenant_ctx.user_id,
    )
    return Response(
        content=data,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=client_{client_id}_data.json"},
    )


@router.post(
    "/clients/{client_id}/anonymize",
    response_model=AnonymizeResponse,
    summary="Anonymiser un client",
    description="Anonymise irreversiblement les donnees personnelles d'un client (droit a l'oubli).",
)
def anonymize_client(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> AnonymizeResponse:
    return gdpr_service.anonymize_client(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
        user_id=tenant_ctx.user_id,
    )
