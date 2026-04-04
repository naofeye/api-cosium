from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.clients import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.repositories import client_repo
from app.services import audit_service

logger = get_logger("client_service")


def search_clients(db: Session, tenant_id: int, query: str, page: int, page_size: int) -> ClientListResponse:
    items, total = client_repo.search(db, tenant_id, query, page, page_size)
    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_client(db: Session, tenant_id: int, client_id: int) -> ClientResponse:
    customer = client_repo.get_by_id(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    return ClientResponse.model_validate(customer)


def create_client(db: Session, tenant_id: int, payload: ClientCreate, user_id: int) -> ClientResponse:
    customer = client_repo.create(db, tenant_id=tenant_id, **payload.model_dump(exclude_none=True))
    audit_service.log_action(
        db,
        tenant_id,
        user_id,
        "create",
        "client",
        customer.id,
        new_value=payload.model_dump(exclude_none=True),
    )
    logger.info("client_created", tenant_id=tenant_id, client_id=customer.id, user_id=user_id)
    return ClientResponse.model_validate(customer)


def update_client(db: Session, tenant_id: int, client_id: int, payload: ClientUpdate, user_id: int) -> ClientResponse:
    customer = client_repo.get_by_id(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    updated = client_repo.update(db, customer, **payload.model_dump(exclude_unset=True))
    audit_service.log_action(
        db,
        tenant_id,
        user_id,
        "update",
        "client",
        client_id,
        new_value=payload.model_dump(exclude_unset=True),
    )
    logger.info("client_updated", tenant_id=tenant_id, client_id=client_id, user_id=user_id)
    return ClientResponse.model_validate(updated)


def delete_client(db: Session, tenant_id: int, client_id: int, user_id: int) -> None:
    customer = client_repo.get_by_id(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    client_repo.delete(db, customer)
    audit_service.log_action(db, tenant_id, user_id, "delete", "client", client_id)
    logger.info("client_deleted", tenant_id=tenant_id, client_id=client_id, user_id=user_id)
