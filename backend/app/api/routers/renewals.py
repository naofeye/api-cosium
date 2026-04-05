"""Routes API pour le copilote de renouvellement proactif."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.renewals import (
    RenewalAnalysisResult,
    RenewalCampaignCreate,
    RenewalCampaignResponse,
    RenewalConfig,
    RenewalDashboardResponse,
    RenewalMessageResult,
    RenewalOpportunity,
)
from app.services import ai_renewal_copilot, renewal_campaign_service, renewal_engine

router = APIRouter(prefix="/api/v1/renewals", tags=["renewals"])


@router.get(
    "/opportunities",
    response_model=list[RenewalOpportunity],
    summary="Opportunites de renouvellement",
    description="Liste les opportunites de renouvellement detectees.",
)
def list_opportunities(
    age_minimum_months: int = Query(24, ge=6, le=60),
    min_invoice_amount: float = Query(0.0, ge=0),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[RenewalOpportunity]:
    """Liste les opportunites de renouvellement detectees."""
    config = RenewalConfig(
        age_minimum_months=age_minimum_months,
        min_invoice_amount=min_invoice_amount,
    )
    return renewal_engine.detect_renewals(db, tenant_ctx.tenant_id, config)


@router.get(
    "/dashboard",
    response_model=RenewalDashboardResponse,
    summary="Dashboard renouvellements",
    description="Tableau de bord des renouvellements avec KPIs.",
)
def get_dashboard(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> RenewalDashboardResponse:
    """Tableau de bord des renouvellements avec KPIs."""
    return renewal_engine.get_renewal_dashboard(db, tenant_ctx.tenant_id)


@router.post(
    "/campaign",
    response_model=RenewalCampaignResponse,
    status_code=201,
    summary="Creer une campagne de renouvellement",
    description="Cree une campagne de renouvellement avec message IA optionnel.",
)
def create_campaign(
    payload: RenewalCampaignCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> RenewalCampaignResponse:
    """Cree une campagne de renouvellement (avec message IA optionnel)."""
    return renewal_campaign_service.create_renewal_campaign(
        db,
        tenant_ctx.tenant_id,
        payload,
        tenant_ctx.user_id,
    )


@router.get(
    "/ai-analysis",
    response_model=RenewalAnalysisResult,
    summary="Analyse IA des renouvellements",
    description="Analyse IA du potentiel de renouvellement du magasin.",
)
def get_ai_analysis(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> RenewalAnalysisResult:
    """Analyse IA du potentiel de renouvellement."""
    dashboard = renewal_engine.get_renewal_dashboard(db, tenant_ctx.tenant_id)
    analysis = ai_renewal_copilot.analyze_renewal_potential(
        db,
        tenant_ctx.tenant_id,
        total_opportunities=dashboard.total_opportunities,
        high_score_count=dashboard.high_score_count,
        avg_months=dashboard.avg_months_since_purchase,
        estimated_revenue=dashboard.estimated_revenue,
    )
    return RenewalAnalysisResult(analysis=analysis)


@router.post(
    "/generate-message",
    response_model=RenewalMessageResult,
    summary="Generer un message de renouvellement",
    description="Genere un message personnalise de renouvellement via IA.",
)
def generate_message(
    customer_id: int = Query(...),
    channel: str = Query("email", pattern="^(email|sms)$"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> RenewalMessageResult:
    """Genere un message de renouvellement personnalise via IA."""
    message = ai_renewal_copilot.generate_renewal_message(
        db,
        tenant_ctx.tenant_id,
        customer_id,
        channel,
    )
    return RenewalMessageResult(message=message, channel=channel, customer_id=customer_id)
