from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.notifications import (
    NotificationListResponse,
    UnreadCountResponse,
)
from app.services import notification_service

router = APIRouter(prefix="/api/v1", tags=["notifications"])


@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    summary="Lister les notifications",
    description="Retourne la liste des notifications de l'utilisateur.",
)
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> NotificationListResponse:
    return notification_service.list_notifications(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/notifications/unread-count",
    response_model=UnreadCountResponse,
    summary="Nombre de notifications non lues",
    description="Retourne le compteur de notifications non lues.",
)
def unread_count(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> UnreadCountResponse:
    return notification_service.get_unread_count(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )


@router.patch(
    "/notifications/{notification_id}/read",
    status_code=204,
    summary="Marquer comme lue",
    description="Marque une notification comme lue.",
)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> None:
    notification_service.mark_read(db, tenant_id=tenant_ctx.tenant_id, notification_id=notification_id)


@router.patch(
    "/notifications/read-all",
    status_code=204,
    summary="Tout marquer comme lu",
    description="Marque toutes les notifications de l'utilisateur comme lues.",
)
def mark_all_read(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> None:
    notification_service.mark_all_read(
        db,
        tenant_id=tenant_ctx.tenant_id,
        user_id=tenant_ctx.user_id,
    )
