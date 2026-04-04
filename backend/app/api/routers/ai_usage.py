from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.ai_usage import AIUsageDaily, AIUsageSummary
from app.services import ai_billing_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai-usage"])


@router.get("/usage", response_model=AIUsageSummary)
def get_usage(
    year: int | None = Query(None),
    month: int | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> AIUsageSummary:
    return ai_billing_service.get_usage_summary(db, tenant_id=tenant_ctx.tenant_id, year=year, month=month)


@router.get("/usage/daily", response_model=list[AIUsageDaily])
def get_daily(
    year: int | None = Query(None),
    month: int | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[AIUsageDaily]:
    return ai_billing_service.get_daily_breakdown(db, tenant_id=tenant_ctx.tenant_id, year=year, month=month)
