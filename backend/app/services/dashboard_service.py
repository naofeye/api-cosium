from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.dashboard import DashboardSummary
from app.models import Case, Document, Payment

logger = get_logger("dashboard_service")


def get_summary(db: Session, tenant_id: int) -> DashboardSummary:
    from app.core.redis_cache import cache_get, cache_set

    cache_key = f"dashboard:summary:{tenant_id}"
    cached = cache_get(cache_key)
    if cached:
        logger.debug("dashboard_summary_cache_hit", tenant_id=tenant_id)
        return DashboardSummary(**cached)

    cases_count = db.query(func.count(Case.id)).filter(Case.tenant_id == tenant_id).scalar() or 0
    documents_count = db.query(func.count(Document.id)).filter(Document.tenant_id == tenant_id).scalar() or 0

    # Use SQL aggregates instead of loading all payments into memory
    payment_totals = (
        db.query(
            func.coalesce(func.sum(Payment.amount_due), 0),
            func.coalesce(func.sum(Payment.amount_paid), 0),
        )
        .filter(Payment.tenant_id == tenant_id)
        .one()
    )
    total_due = round(float(payment_totals[0]), 2)
    total_paid = round(float(payment_totals[1]), 2)

    logger.info("dashboard_loaded", tenant_id=tenant_id, cases=cases_count, documents=documents_count)
    result = DashboardSummary(
        cases_count=cases_count,
        documents_count=documents_count,
        alerts_count=max(cases_count - documents_count, 0),
        total_due=total_due,
        total_paid=total_paid,
        remaining=round(total_due - total_paid, 2),
    )
    cache_set(cache_key, result.model_dump(), ttl=30)
    return result
