from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.marketing import ConsentResponse, ConsentUpdate
from app.services import consent_service

router = APIRouter(prefix="/api/v1", tags=["consents"])


@router.get(
    "/clients/{client_id}/consents",
    response_model=list[ConsentResponse],
    summary="Consentements d'un client",
    description="Retourne les consentements marketing d'un client par canal.",
)
def get_consents(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[ConsentResponse]:
    return consent_service.get_consents(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
    )


@router.put(
    "/clients/{client_id}/consents/{channel}",
    response_model=ConsentResponse,
    summary="Modifier un consentement",
    description="Met a jour le consentement d'un client pour un canal donne.",
)
def update_consent(
    client_id: int,
    channel: str,
    payload: ConsentUpdate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("edit", "client")),
) -> ConsentResponse:
    return consent_service.update_consent(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
        channel=channel,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )
