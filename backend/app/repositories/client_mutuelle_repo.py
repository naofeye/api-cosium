"""Repository for client-mutuelle associations."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client_mutuelle import ClientMutuelle


def get_by_customer(
    db: Session, customer_id: int, tenant_id: int
) -> list[ClientMutuelle]:
    """Return all mutuelles for a given customer."""
    stmt = (
        select(ClientMutuelle)
        .where(
            ClientMutuelle.customer_id == customer_id,
            ClientMutuelle.tenant_id == tenant_id,
        )
        .order_by(ClientMutuelle.active.desc(), ClientMutuelle.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_by_id(
    db: Session, mutuelle_id: int, tenant_id: int
) -> ClientMutuelle | None:
    """Return a single client_mutuelle by id."""
    return db.scalars(
        select(ClientMutuelle).where(
            ClientMutuelle.id == mutuelle_id,
            ClientMutuelle.tenant_id == tenant_id,
        )
    ).first()


def find_existing(
    db: Session,
    customer_id: int,
    tenant_id: int,
    mutuelle_name: str,
    source: str,
) -> ClientMutuelle | None:
    """Check if a mutuelle with the same name+source already exists for this client."""
    return db.scalars(
        select(ClientMutuelle).where(
            ClientMutuelle.customer_id == customer_id,
            ClientMutuelle.tenant_id == tenant_id,
            ClientMutuelle.mutuelle_name == mutuelle_name,
            ClientMutuelle.source == source,
        )
    ).first()


def create(db: Session, data: dict) -> ClientMutuelle:
    """Create a new client-mutuelle association."""
    record = ClientMutuelle(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update(
    db: Session, record_id: int, tenant_id: int, data: dict
) -> ClientMutuelle | None:
    """Update an existing client-mutuelle record."""
    record = get_by_id(db, record_id, tenant_id)
    if not record:
        return None
    for key, value in data.items():
        setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    return record


def delete(db: Session, record_id: int, tenant_id: int) -> bool:
    """Delete a client-mutuelle record. Returns True if deleted."""
    record = get_by_id(db, record_id, tenant_id)
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True
