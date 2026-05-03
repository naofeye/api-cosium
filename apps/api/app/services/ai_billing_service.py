"""Service de facturation IA — suivi de la consommation et quotas."""

from datetime import UTC, datetime

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import AiUsageLog
from app.repositories import onboarding_repo

logger = get_logger("ai_billing_service")

QUOTAS = {
    "solo": 500,
    "trial": 500,
    "reseau": 2000,
    "ia_pro": 5000,
}


def get_usage_summary(db: Session, tenant_id: int, year: int | None = None, month: int | None = None) -> dict:
    now = datetime.now(UTC)
    y = year or now.year
    m = month or now.month

    base = select(
        func.count().label("total_requests"),
        func.coalesce(func.sum(AiUsageLog.tokens_in), 0).label("total_tokens_in"),
        func.coalesce(func.sum(AiUsageLog.tokens_out), 0).label("total_tokens_out"),
        func.coalesce(func.sum(AiUsageLog.cost_usd), 0).label("total_cost"),
    ).where(
        AiUsageLog.tenant_id == tenant_id,
        extract("year", AiUsageLog.created_at) == y,
        extract("month", AiUsageLog.created_at) == m,
    )
    row = db.execute(base).first()

    # Get plan quota
    tenant = onboarding_repo.get_tenant_by_id(db, tenant_id)
    org = onboarding_repo.get_org_by_id(db, tenant.organization_id) if tenant else None
    plan = org.plan if org else "solo"
    quota = QUOTAS.get(plan, 500)

    total_requests = row.total_requests if row else 0

    return {
        "year": y,
        "month": m,
        "total_requests": total_requests,
        "total_tokens_in": int(row.total_tokens_in) if row else 0,
        "total_tokens_out": int(row.total_tokens_out) if row else 0,
        "total_cost_usd": float(row.total_cost) if row else 0.0,
        "quota": quota,
        "quota_remaining": max(0, quota - total_requests),
        "quota_percent": round((total_requests / quota) * 100, 1) if quota > 0 else 0,
        "plan": plan,
    }



def get_daily_breakdown(db: Session, tenant_id: int, year: int | None = None, month: int | None = None) -> list[dict]:
    now = datetime.now(UTC)
    y = year or now.year
    m = month or now.month

    rows = db.execute(
        select(
            extract("day", AiUsageLog.created_at).label("day"),
            func.count().label("requests"),
            func.coalesce(func.sum(AiUsageLog.tokens_in + AiUsageLog.tokens_out), 0).label("tokens"),
        )
        .where(
            AiUsageLog.tenant_id == tenant_id,
            extract("year", AiUsageLog.created_at) == y,
            extract("month", AiUsageLog.created_at) == m,
        )
        .group_by(extract("day", AiUsageLog.created_at))
        .order_by(extract("day", AiUsageLog.created_at))
    ).all()

    return [{"day": int(r.day), "requests": r.requests, "tokens": int(r.tokens)} for r in rows]
