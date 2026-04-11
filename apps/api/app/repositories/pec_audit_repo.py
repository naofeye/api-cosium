"""Repository for PEC audit trail entries."""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pec_audit import PecAuditEntry


def create(
    db: Session,
    tenant_id: int,
    preparation_id: int,
    action: str,
    user_id: int,
    field_name: str | None = None,
    old_value: object = None,
    new_value: object = None,
    source: str | None = None,
) -> PecAuditEntry:
    """Create a new PEC audit entry."""
    entry = PecAuditEntry(
        tenant_id=tenant_id,
        preparation_id=preparation_id,
        action=action,
        user_id=user_id,
        field_name=field_name,
        old_value=json.dumps(old_value) if old_value is not None else None,
        new_value=json.dumps(new_value) if new_value is not None else None,
        source=source,
    )
    db.add(entry)
    db.flush()
    return entry


def list_by_preparation(
    db: Session,
    preparation_id: int,
    tenant_id: int,
    limit: int = 100,
    offset: int = 0,
) -> list[PecAuditEntry]:
    """List audit entries for a given preparation, newest first."""
    stmt = (
        select(PecAuditEntry)
        .where(
            PecAuditEntry.preparation_id == preparation_id,
            PecAuditEntry.tenant_id == tenant_id,
        )
        .order_by(PecAuditEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt).all())
