from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Payment


def list_by_case(db: Session, case_id: int, tenant_id: int, limit: int = 200) -> list[Payment]:
    return (
        db.execute(select(Payment).where(Payment.case_id == case_id, Payment.tenant_id == tenant_id).limit(limit))
        .scalars()
        .all()
    )


def get_summary(db: Session, case_id: int, tenant_id: int) -> dict:
    rows = list_by_case(db, case_id, tenant_id)
    total_due = round(sum(float(r.amount_due) for r in rows), 2)
    total_paid = round(sum(float(r.amount_paid) for r in rows), 2)
    return {
        "case_id": case_id,
        "total_due": total_due,
        "total_paid": total_paid,
        "remaining": round(total_due - total_paid, 2),
        "items": rows,
    }
