import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.models.user import User
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
    action: str | None = None,
) -> AuditLogListResponse:
    from datetime import datetime

    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None
    items, total = audit_repo.search(
        db, tenant_id, entity_type, entity_id, user_id, df, dt, page, page_size, action=action,
    )
    # Enrich with user emails
    user_ids = list({i.user_id for i in items})
    email_map: dict[int, str] = {}
    if user_ids:
        rows = db.execute(select(User.id, User.email).where(User.id.in_(user_ids))).all()
        email_map = {r.id: r.email for r in rows}

    enriched = []
    for i in items:
        resp = AuditLogResponse.model_validate(i)
        resp.user_email = email_map.get(i.user_id)
        enriched.append(resp)

    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return AuditLogListResponse(
        items=enriched,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
