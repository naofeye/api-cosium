"""Admin user management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.admin_users import (
    AdminUserCreate,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
)
from app.services import admin_user_service

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin"])


@router.get(
    "",
    response_model=AdminUserListResponse,
    summary="Lister les utilisateurs",
    description="Retourne tous les utilisateurs du tenant courant (admin uniquement).",
)
def list_users(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> AdminUserListResponse:
    users = admin_user_service.list_users(db, tenant_ctx.tenant_id)
    return AdminUserListResponse(users=users, total=len(users))


@router.post(
    "",
    response_model=AdminUserResponse,
    status_code=201,
    summary="Creer un utilisateur",
    description="Cree un nouvel utilisateur et l'associe au tenant courant (admin uniquement).",
)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> AdminUserResponse:
    return admin_user_service.create_user(
        db, tenant_ctx.tenant_id, payload, tenant_ctx.user_id
    )


@router.patch(
    "/{user_id}",
    response_model=AdminUserResponse,
    summary="Modifier un utilisateur",
    description="Modifie le role ou le statut d'un utilisateur du tenant (admin uniquement).",
)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> AdminUserResponse:
    return admin_user_service.update_user(
        db, tenant_ctx.tenant_id, user_id, payload, tenant_ctx.user_id
    )


@router.delete(
    "/{user_id}",
    response_model=AdminUserResponse,
    summary="Desactiver un utilisateur",
    description="Desactive un utilisateur du tenant (suppression logique, admin uniquement).",
)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> AdminUserResponse:
    return admin_user_service.deactivate_user(
        db, tenant_ctx.tenant_id, user_id, tenant_ctx.user_id
    )
