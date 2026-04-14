from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.analytics import CosiumCockpitKPIs
from app.domain.schemas.dashboard import DashboardSummary
from app.services import analytics_cosium_service, dashboard_service

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummary,
    summary="Resume du tableau de bord",
    description="Retourne les KPIs principaux pour le tableau de bord d'accueil.",
)
def dashboard_summary(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DashboardSummary:
    return dashboard_service.get_summary(db, tenant_id=tenant_ctx.tenant_id)


@router.get(
    "/dashboard/top-clients",
    summary="Top clients par CA",
    description="Retourne les N clients avec le CA le plus eleve sur les derniers mois (factures Cosium).",
)
def dashboard_top_clients(
    limit: int = 10,
    months: int = 12,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    return analytics_cosium_service.get_top_clients_by_ca(db, tenant_ctx.tenant_id, limit=limit, months=months)


@router.get(
    "/dashboard/cosium-cockpit",
    response_model=CosiumCockpitKPIs,
    summary="Cockpit opticien — KPIs Cosium live",
    description="CA jour/semaine/mois, panier moyen, taux transformation devis->facture, balance agee.",
)
def dashboard_cosium_cockpit(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumCockpitKPIs:
    return analytics_cosium_service.get_cosium_cockpit_kpis(db, tenant_ctx.tenant_id)
