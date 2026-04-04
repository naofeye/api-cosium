import json

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.repositories import audit_repo

logger = get_logger("audit_service")


def log_action(
    db: Session,
    tenant_id: int,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> None:
    audit_repo.create(
        db,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=json.dumps(old_value) if old_value else None,
        new_value=json.dumps(new_value) if new_value else None,
        tenant_id=tenant_id,
    )
    logger.info(
        "audit_logged",
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
    )


def search_logs(
    db: Session,
    tenant_id: int,
    entity_type: str | None,
    entity_id: int | None,
    user_id: int | None,
    date_from: str | None,
    date_to: str | None,
    page: int,
    page_size: int,
) -> AuditLogListResponse:
    from datetime import datetime

    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None
    items, total = audit_repo.search(db, tenant_id, entity_type, entity_id, user_id, df, dt, page, page_size)
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )
