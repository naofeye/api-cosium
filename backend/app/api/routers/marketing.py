from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.marketing import (
    CampaignCreate,
    CampaignResponse,
    CampaignStats,
    SegmentCreate,
    SegmentResponse,
)
from app.services import marketing_service

router = APIRouter(prefix="/api/v1/marketing", tags=["marketing"])


# --- Segments ---


@router.get(
    "/segments",
    response_model=list[SegmentResponse],
    summary="Lister les segments",
    description="Retourne la liste des segments marketing.",
)
def list_segments(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SegmentResponse]:
    return marketing_service.list_segments(db, tenant_id=tenant_ctx.tenant_id)


@router.post(
    "/segments",
    response_model=SegmentResponse,
    status_code=201,
    summary="Creer un segment",
    description="Cree un nouveau segment marketing base sur des criteres.",
)
def create_segment(
    payload: SegmentCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> SegmentResponse:
    return marketing_service.create_segment(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/segments/{segment_id}/refresh",
    response_model=SegmentResponse,
    summary="Rafraichir un segment",
    description="Recalcule les membres d'un segment marketing.",
)
def refresh_segment(
    segment_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> SegmentResponse:
    return marketing_service.refresh_segment(
        db,
        tenant_id=tenant_ctx.tenant_id,
        segment_id=segment_id,
    )


# --- Campaigns ---


@router.get(
    "/campaigns",
    response_model=list[CampaignResponse],
    summary="Lister les campagnes",
    description="Retourne la liste des campagnes marketing.",
)
def list_campaigns(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[CampaignResponse]:
    return marketing_service.list_campaigns(db, tenant_id=tenant_ctx.tenant_id)


@router.post(
    "/campaigns",
    response_model=CampaignResponse,
    status_code=201,
    summary="Creer une campagne",
    description="Cree une nouvelle campagne marketing.",
)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> CampaignResponse:
    return marketing_service.create_campaign(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/campaigns/{campaign_id}/send",
    response_model=CampaignStats,
    summary="Envoyer une campagne",
    description="Declenche l'envoi d'une campagne marketing aux destinataires.",
)
def send_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> CampaignStats:
    return marketing_service.send_campaign(
        db,
        tenant_id=tenant_ctx.tenant_id,
        campaign_id=campaign_id,
        user_id=tenant_ctx.user_id,
    )


@router.get(
    "/campaigns/{campaign_id}/stats",
    response_model=CampaignStats,
    summary="Statistiques d'une campagne",
    description="Retourne les statistiques d'envoi d'une campagne.",
)
def get_campaign_stats(
    campaign_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CampaignStats:
    return marketing_service.get_campaign_stats(
        db,
        tenant_id=tenant_ctx.tenant_id,
        campaign_id=campaign_id,
    )
