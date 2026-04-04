from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.interactions import InteractionCreate, InteractionResponse
from app.repositories import interaction_repo
from app.services import audit_service

logger = get_logger("interaction_service")


def add_interaction(db: Session, tenant_id: int, payload: InteractionCreate, user_id: int) -> InteractionResponse:
    item = interaction_repo.create(
        db,
        tenant_id,
        payload.client_id,
        payload.case_id,
        payload.type,
        payload.direction,
        payload.subject,
        payload.content,
        user_id,
    )
    audit_service.log_action(db, tenant_id, user_id, "create", "interaction", item.id)
    logger.info("interaction_created", tenant_id=tenant_id, id=item.id, client_id=payload.client_id, type=payload.type)
    return InteractionResponse.model_validate(item)


def get_client_timeline(
    db: Session,
    tenant_id: int,
    client_id: int,
    type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[InteractionResponse], int]:
    items, total = interaction_repo.list_by_client(
        db, client_id=client_id, tenant_id=tenant_id, type=type, limit=limit, offset=offset
    )
    return [InteractionResponse.model_validate(i) for i in items], total


def delete_interaction(db: Session, tenant_id: int, interaction_id: int, user_id: int) -> None:
    item = interaction_repo.get_by_id(db, interaction_id=interaction_id, tenant_id=tenant_id)
    if not item:
        raise NotFoundError("interaction", interaction_id)
    interaction_repo.delete(db, item)
    audit_service.log_action(db, tenant_id, user_id, "delete", "interaction", interaction_id)
    logger.info("interaction_deleted", tenant_id=tenant_id, id=interaction_id)
