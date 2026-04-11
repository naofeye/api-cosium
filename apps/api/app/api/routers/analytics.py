from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.analytics import (
    AgingBalance,
    CommercialKPIs,
    DashboardFull,
    FinancialKPIs,
    MarketingKPIs,
    OperationalKPIs,
    PayerPerformance,
)
from app.services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get(
    "/financial",
    response_model=FinancialKPIs,
    summary="KPIs financiers",
    description="Retourne les indicateurs financiers cles sur une periode.",
)
def get_financial(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> FinancialKPIs:
    return analytics_service.get_financial_kpis(
        db,
        tenant_id=tenant_ctx.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get(
    "/aging",
    response_model=AgingBalance,
    summary="Balance agee",
    description="Retourne la balance agee des creances par tranche de retard.",
)
def get_aging(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> AgingBalance:
    return analytics_service.get_aging_balance(db, tenant_id=tenant_ctx.tenant_id)


@router.get(
    "/payers",
    response_model=PayerPerformance,
    summary="Performance des payeurs",
    description="Retourne les statistiques de performance par organisme payeur.",
)
def get_payers(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PayerPerformance:
    return analytics_service.get_payer_performance(db, tenant_id=tenant_ctx.tenant_id)


@router.get(
    "/operational",
    response_model=OperationalKPIs,
    summary="KPIs operationnels",
    description="Retourne les indicateurs operationnels du magasin.",
)
def get_operational(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> OperationalKPIs:
    return analytics_service.get_operational_kpis(db, tenant_id=tenant_ctx.tenant_id)


@router.get(
    "/commercial",
    response_model=CommercialKPIs,
    summary="KPIs commerciaux",
    description="Retourne les indicateurs commerciaux (devis, conversion).",
)
def get_commercial(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CommercialKPIs:
    return analytics_service.get_commercial_kpis(db, tenant_id=tenant_ctx.tenant_id)


@router.get(
    "/marketing",
    response_model=MarketingKPIs,
    summary="KPIs marketing",
    description="Retourne les indicateurs marketing (campagnes, segments).",
)
def get_marketing(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> MarketingKPIs:
    return analytics_service.get_marketing_kpis(db, tenant_id=tenant_ctx.tenant_id)


@router.get(
    "/dashboard",
    response_model=DashboardFull,
    summary="Dashboard analytique complet",
    description="Retourne l'ensemble des KPIs pour le tableau de bord analytique.",
)
def get_dashboard(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DashboardFull:
    return analytics_service.get_dashboard_full(
        db,
        tenant_id=tenant_ctx.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )
