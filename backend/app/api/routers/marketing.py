from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

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


@router.get("/segments", response_model=list[SegmentResponse])
def list_segments(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SegmentResponse]:
    return marketing_service.list_segments(db, tenant_id=tenant_ctx.tenant_id)


@router.post("/segments", response_model=SegmentResponse, status_code=201)
def create_segment(
    payload: SegmentCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> SegmentResponse:
    return marketing_service.create_segment(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.post("/segments/{segment_id}/refresh", response_model=SegmentResponse)
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


@router.get("/campaigns", response_model=list[CampaignResponse])
def list_campaigns(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[CampaignResponse]:
    return marketing_service.list_campaigns(db, tenant_id=tenant_ctx.tenant_id)


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CampaignResponse:
    return marketing_service.create_campaign(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.post("/campaigns/{campaign_id}/send", response_model=CampaignStats)
def send_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CampaignStats:
    return marketing_service.send_campaign(
        db,
        tenant_id=tenant_ctx.tenant_id,
        campaign_id=campaign_id,
        user_id=tenant_ctx.user_id,
    )


@router.get("/campaigns/{campaign_id}/stats", response_model=CampaignStats)
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
