from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> DashboardSummary:
    return dashboard_service.get_summary(db, tenant_id=tenant_ctx.tenant_id)
