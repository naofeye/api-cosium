from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.dashboard import DashboardSummary
from app.models import Case, Document, Payment

logger = get_logger("dashboard_service")


def get_summary(db: Session, tenant_id: int) -> DashboardSummary:
    cases_count = db.query(Case).filter(Case.tenant_id == tenant_id).count()
    documents_count = db.query(Document).filter(Document.tenant_id == tenant_id).count()
    payments = db.query(Payment).filter(Payment.tenant_id == tenant_id).all()
    total_due = round(sum(float(p.amount_due or 0) for p in payments), 2)
    total_paid = round(sum(float(p.amount_paid or 0) for p in payments), 2)
    logger.info("dashboard_loaded", tenant_id=tenant_id, cases=cases_count, documents=documents_count)
    return DashboardSummary(
        cases_count=cases_count,
        documents_count=documents_count,
        alerts_count=max(cases_count - documents_count, 0),
        total_due=total_due,
        total_paid=total_paid,
        remaining=round(total_due - total_paid, 2),
    )
