from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.notifications import (
    ActionItemListResponse,
    ActionItemUpdate,
)
from app.services import action_item_service

router = APIRouter(prefix="/api/v1", tags=["action-items"])


@router.get(
    "/action-items",
    response_model=ActionItemListResponse,
    summary="Lister les actions a faire",
    description="Retourne la liste des actions a faire filtrable par statut et priorite.",
)
def list_action_items(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ActionItemListResponse:
    return action_item_service.list_action_items(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        status=status,
        priority=priority,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/action-items/{item_id}",
    status_code=204,
    summary="Mettre a jour une action",
    description="Met a jour le statut d'une action a faire.",
)
def update_action_item(
    item_id: int,
    payload: ActionItemUpdate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> None:
    action_item_service.update_status(
        db,
        tenant_id=tenant_ctx.tenant_id,
        item_id=item_id,
        status=payload.status,
    )


@router.post(
    "/action-items/refresh",
    response_model=ActionItemListResponse,
    summary="Rafraichir les actions",
    description="Regenere la liste des actions a faire basee sur l'etat des dossiers.",
)
def refresh_action_items(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ActionItemListResponse:
    return action_item_service.generate_action_items(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )
