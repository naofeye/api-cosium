from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.idempotency import IdempotencyContext, idempotency
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.pec import (
    PayerOrgCreate,
    PayerOrgResponse,
    PecCreate,
    PecDetail,
    PecResponse,
    PecStatusHistoryResponse,
    PecStatusUpdate,
    RelanceCreate,
    RelanceResponse,
)
from app.services import pec_service

router = APIRouter(prefix="/api/v1", tags=["pec"])


# --- Organizations ---


@router.get(
    "/payer-organizations",
    response_model=list[PayerOrgResponse],
    summary="Lister les organismes payeurs",
    description="Retourne la liste des mutuelles et organismes de tiers payant.",
)
def list_organizations(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[PayerOrgResponse]:
    return pec_service.list_organizations(db, tenant_id=tenant_ctx.tenant_id)


@router.post(
    "/payer-organizations",
    response_model=PayerOrgResponse,
    status_code=201,
    summary="Creer un organisme payeur",
    description="Ajoute un nouvel organisme payeur (mutuelle, secu).",
)
def create_organization(
    payload: PayerOrgCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PayerOrgResponse:
    return pec_service.create_organization(
        db, tenant_id=tenant_ctx.tenant_id, payload=payload, user_id=tenant_ctx.user_id
    )


# --- PEC Requests ---


@router.post(
    "/pec",
    response_model=PecResponse,
    status_code=201,
    summary="Creer une demande de PEC",
    description="Soumet une nouvelle demande de prise en charge.",
)
def create_pec(
    payload: PecCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    idem: IdempotencyContext = Depends(idempotency("pec:create")),
) -> PecResponse:
    if idem.cached:
        return PecResponse(**idem.cached)
    result = pec_service.create_pec(db, tenant_id=tenant_ctx.tenant_id, payload=payload, user_id=tenant_ctx.user_id)
    idem.store(result.model_dump(mode="json"))
    return result


@router.get(
    "/pec",
    response_model=list[PecResponse],
    summary="Lister les demandes de PEC",
    description="Retourne la liste filtrable des demandes de prise en charge.",
)
def list_pec(
    status: str | None = Query(None),
    organization_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[PecResponse]:
    offset = (page - 1) * page_size
    return pec_service.list_pec(
        db, tenant_id=tenant_ctx.tenant_id, status=status, organization_id=organization_id, limit=page_size, offset=offset
    )


@router.get(
    "/pec/{pec_id}",
    response_model=PecDetail,
    summary="Detail d'une PEC",
    description="Retourne le detail complet d'une demande de prise en charge.",
)
def get_pec(
    pec_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PecDetail:
    return pec_service.get_pec_detail(db, tenant_id=tenant_ctx.tenant_id, pec_id=pec_id)


@router.patch(
    "/pec/{pec_id}/status",
    response_model=PecResponse,
    summary="Changer le statut d'une PEC",
    description="Met a jour le statut d'une demande de prise en charge.",
)
def change_status(
    pec_id: int,
    payload: PecStatusUpdate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PecResponse:
    return pec_service.change_status(
        db, tenant_id=tenant_ctx.tenant_id, pec_id=pec_id, payload=payload, user_id=tenant_ctx.user_id
    )


@router.get(
    "/pec/{pec_id}/history",
    response_model=list[PecStatusHistoryResponse],
    summary="Historique d'une PEC",
    description="Retourne l'historique des changements de statut d'une PEC.",
)
def get_history(
    pec_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[PecStatusHistoryResponse]:
    return pec_service.get_history(db, tenant_id=tenant_ctx.tenant_id, pec_id=pec_id)


# --- Relances ---


@router.post(
    "/pec/{pec_id}/relances",
    response_model=RelanceResponse,
    status_code=201,
    summary="Creer une relance PEC",
    description="Cree une relance pour une demande de prise en charge en attente.",
)
def create_relance(
    pec_id: int,
    payload: RelanceCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> RelanceResponse:
    return pec_service.create_relance(
        db, tenant_id=tenant_ctx.tenant_id, pec_id=pec_id, payload=payload, user_id=tenant_ctx.user_id
    )


@router.get(
    "/pec/{pec_id}/relances",
    response_model=list[RelanceResponse],
    summary="Lister les relances d'une PEC",
    description="Retourne les relances envoyees pour une demande de prise en charge.",
)
def get_relances(
    pec_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[RelanceResponse]:
    return pec_service.get_relances(db, tenant_id=tenant_ctx.tenant_id, pec_id=pec_id)
