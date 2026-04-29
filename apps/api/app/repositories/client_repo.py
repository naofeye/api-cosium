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
    return db.scalars(
        select(Customer).where(
            Customer.id == client_id,
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
        )
    ).first()


def get_by_id_including_deleted(db: Session, client_id: int, tenant_id: int) -> Customer | None:
    return db.scalars(select(Customer).where(Customer.id == client_id, Customer.tenant_id == tenant_id)).first()


# Keep old alias for backwards compatibility
get_by_id_active = get_by_id


# Whitelist des champs modifiables sur Customer (protection mass-assignment).
# Exclut deliberement : id, tenant_id (set explicitement), created_at, updated_at,
# deleted_at, avatar_url (gere par service dedie), cosium_id, customer_number,
# site_id, ophthalmologist_id (geres par sync Cosium).
# Champs derives de la doc Cosium gardes (mobile_phone_country, etc.) ou metier
# OptiFlow (notes, optician_name).
_CUSTOMER_WRITABLE_FIELDS = frozenset({
    "first_name", "last_name", "email", "phone", "mobile_phone_country",
    "birth_date", "address", "street_name", "street_number", "postal_code", "city",
    "social_security_number", "optician_name", "notes",
})


def _filter_writable(kwargs: dict) -> dict:
    return {k: v for k, v in kwargs.items() if k in _CUSTOMER_WRITABLE_FIELDS}


def create(db: Session, tenant_id: int, **kwargs: object) -> Customer:
    safe = _filter_writable(kwargs)
    customer = Customer(tenant_id=tenant_id, **safe)
    db.add(customer)
    db.flush()
    db.refresh(customer)
    return customer


def update(db: Session, customer: Customer, **kwargs: object) -> Customer:
    """PATCH d'un Customer. Le filtre `_filter_writable` empeche le mass-assignment.
    On accepte les valeurs None (qui vident les colonnes nullable) : si l'appelant
    veut conserver l'existant, il doit utiliser `exclude_unset=True` cote schema
    Pydantic et ne pas passer le champ.
    """
    safe = _filter_writable(kwargs)
    for key, value in safe.items():
        setattr(customer, key, value)
    db.flush()
    db.refresh(customer)
    return customer


def delete(db: Session, customer: Customer) -> None:
    customer.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db.flush()


def restore(db: Session, customer: Customer) -> Customer:
    customer.deleted_at = None
    db.flush()
    return customer
