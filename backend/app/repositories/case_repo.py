from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Case, Customer


def count_cases(db: Session, tenant_id: int) -> int:
    return (
        db.scalar(select(func.count()).select_from(Case).where(Case.tenant_id == tenant_id, Case.deleted_at.is_(None)))
        or 0
    )


def list_cases(db: Session, tenant_id: int, limit: int = 25, offset: int = 0) -> list[dict]:
    rows = db.execute(
        select(
            Case.id,
            Case.status,
            Case.source,
            Case.created_at,
            Customer.first_name,
            Customer.last_name,
        )
        .join(Customer, Customer.id == Case.customer_id)
        .where(Case.tenant_id == tenant_id, Case.deleted_at.is_(None))
        .order_by(Case.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        {
            "id": r.id,
            "customer_name": f"{r.first_name} {r.last_name}",
            "status": r.status,
            "source": r.source,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def get_case(db: Session, case_id: int, tenant_id: int) -> dict | None:
    row = db.execute(
        select(
            Case.id,
            Case.status,
            Case.source,
            Customer.first_name,
            Customer.last_name,
            Customer.phone,
            Customer.email,
        )
        .join(Customer, Customer.id == Case.customer_id)
        .where(Case.id == case_id, Case.tenant_id == tenant_id, Case.deleted_at.is_(None))
    ).first()
    if not row:
        return None
    return {
        "id": row.id,
        "customer_name": f"{row.first_name} {row.last_name}",
        "status": row.status,
        "source": row.source,
        "phone": row.phone,
        "email": row.email,
    }


def create_case(
    db: Session, tenant_id: int, first_name: str, last_name: str, phone: str | None, email: str | None, source: str
) -> Case:
    customer = Customer(tenant_id=tenant_id, first_name=first_name, last_name=last_name, phone=phone, email=email)
    db.add(customer)
    db.flush()
    case = Case(tenant_id=tenant_id, customer_id=customer.id, status="draft", source=source)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case
