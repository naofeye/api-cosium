from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

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
