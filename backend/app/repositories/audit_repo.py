from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog


def create(
    db: Session,
    tenant_id: int,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    old_value: str | None = None,
    new_value: str | None = None,
) -> AuditLog:
    log = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def search(
    db: Session,
    tenant_id: int,
    entity_type: str | None,
    entity_id: int | None,
    user_id: int | None,
    date_from: datetime | None,
    date_to: datetime | None,
    page: int,
    size: int,
) -> tuple[list[AuditLog], int]:
    stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    return list(rows), total or 0
