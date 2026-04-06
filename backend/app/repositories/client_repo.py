from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Customer


def search(
    db: Session,
    tenant_id: int,
    query: str,
    page: int,
    size: int,
    include_deleted: bool = False,
) -> tuple[list[Customer], int]:
    stmt = select(Customer).where(Customer.tenant_id == tenant_id)
    if not include_deleted:
        stmt = stmt.where(Customer.deleted_at.is_(None))
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                Customer.first_name.ilike(pattern),
                Customer.last_name.ilike(pattern),
                Customer.email.ilike(pattern),
                Customer.phone.ilike(pattern),
                Customer.city.ilike(pattern),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(Customer.last_name, Customer.first_name).offset((page - 1) * size).limit(size)
    ).all()
    return list(rows), total or 0


def get_by_id(db: Session, client_id: int, tenant_id: int) -> Customer | None:
    return db.scalars(select(Customer).where(Customer.id == client_id, Customer.tenant_id == tenant_id)).first()


def get_by_id_active(db: Session, client_id: int, tenant_id: int) -> Customer | None:
    return db.scalars(
        select(Customer).where(
            Customer.id == client_id,
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
        )
    ).first()


def create(db: Session, tenant_id: int, **kwargs: object) -> Customer:
    customer = Customer(tenant_id=tenant_id, **kwargs)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update(db: Session, customer: Customer, **kwargs: object) -> Customer:
    for key, value in kwargs.items():
        if value is not None:
            setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer


def delete(db: Session, customer: Customer) -> None:
    customer.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(customer)


def restore(db: Session, customer: Customer) -> Customer:
    customer.deleted_at = None
    db.commit()
    db.refresh(customer)
    return customer
