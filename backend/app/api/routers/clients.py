from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.clients import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.services import client_service

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
def list_clients(
    query: str = Query("", alias="q"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ClientListResponse:
    # Only admin can see deleted clients
    effective_include_deleted = include_deleted and tenant_ctx.role == "admin"
    return client_service.search_clients(
        db,
        tenant_id=tenant_ctx.tenant_id,
        query=query,
        page=page,
        page_size=page_size,
        include_deleted=effective_include_deleted,
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ClientResponse:
    return client_service.get_client(db, tenant_id=tenant_ctx.tenant_id, client_id=client_id)


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ClientResponse:
    return client_service.create_client(db, tenant_id=tenant_ctx.tenant_id, payload=payload, user_id=tenant_ctx.user_id)


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ClientResponse:
    return client_service.update_client(
        db, tenant_id=tenant_ctx.tenant_id, client_id=client_id, payload=payload, user_id=tenant_ctx.user_id
    )


@router.delete("/{client_id}", status_code=204)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> None:
    client_service.delete_client(db, tenant_id=tenant_ctx.tenant_id, client_id=client_id, user_id=tenant_ctx.user_id)


@router.post("/{client_id}/restore", response_model=ClientResponse)
def restore_client(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> ClientResponse:
    return client_service.restore_client(
        db, tenant_id=tenant_ctx.tenant_id, client_id=client_id, user_id=tenant_ctx.user_id
    )
