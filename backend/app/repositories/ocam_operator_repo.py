"""Repository for OCAM operators."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ocam_operator import OcamOperator


def list_all(
    db: Session,
    tenant_id: int,
    active_only: bool = True,
) -> list[OcamOperator]:
    """List all OCAM operators for a tenant."""
    stmt = select(OcamOperator).where(OcamOperator.tenant_id == tenant_id)
    if active_only:
        stmt = stmt.where(OcamOperator.active.is_(True))
    stmt = stmt.order_by(OcamOperator.name)
    return list(db.scalars(stmt).all())


def get_by_id(
    db: Session,
    operator_id: int,
    tenant_id: int,
) -> OcamOperator | None:
    """Get an OCAM operator by ID."""
    return db.scalars(
        select(OcamOperator).where(
            OcamOperator.id == operator_id,
            OcamOperator.tenant_id == tenant_id,
        )
    ).first()


def create(
    db: Session,
    tenant_id: int,
    name: str,
    code: str | None = None,
    portal_url: str | None = None,
    required_fields: str | None = None,
    required_documents: str | None = None,
    specific_rules: str | None = None,
    active: bool = True,
) -> OcamOperator:
    """Create a new OCAM operator."""
    operator = OcamOperator(
        tenant_id=tenant_id,
        name=name,
        code=code,
        portal_url=portal_url,
        required_fields=required_fields,
        required_documents=required_documents,
        specific_rules=specific_rules,
        active=active,
    )
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator
