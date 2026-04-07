from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.notifications import (
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.repositories import notification_repo

logger = get_logger("notification_service")


def notify(
    db: Session,
    tenant_id: int,
    user_id: int,
    type: str,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> NotificationResponse:
    notif = notification_repo.create(db, tenant_id, user_id, type, title, message, entity_type, entity_id)
    logger.info("notification_created", tenant_id=tenant_id, user_id=user_id, type=type, title=title)
    return NotificationResponse.model_validate(notif)


def list_notifications(
    db: Session, tenant_id: int, user_id: int, unread_only: bool = False, limit: int = 50, offset: int = 0
) -> NotificationListResponse:
    items, total = notification_repo.list_by_user(
        db, user_id=user_id, tenant_id=tenant_id, unread_only=unread_only, limit=limit, offset=offset
    )
    unread = notification_repo.get_unread_count(db, user_id=user_id, tenant_id=tenant_id)
    page = (offset // limit + 1) if limit else 1
    total_pages = (total + limit - 1) // limit if limit else 0
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
        unread_count=unread,
    )


def get_unread_count(db: Session, tenant_id: int, user_id: int) -> UnreadCountResponse:
    count = notification_repo.get_unread_count(db, user_id=user_id, tenant_id=tenant_id)
    return UnreadCountResponse(count=count)


def mark_read(db: Session, tenant_id: int, notification_id: int, user_id: int) -> None:
    notification_repo.mark_read(db, notification_id=notification_id, tenant_id=tenant_id, user_id=user_id)
    db.commit()
    logger.info("notification_read", tenant_id=tenant_id, notification_id=notification_id, user_id=user_id)


def mark_all_read(db: Session, tenant_id: int, user_id: int) -> None:
    notification_repo.mark_all_read(db, user_id=user_id, tenant_id=tenant_id)
    db.commit()
    logger.info("notifications_all_read", tenant_id=tenant_id, user_id=user_id)


def delete_notification(db: Session, tenant_id: int, notification_id: int, user_id: int) -> None:
    notification_repo.delete_notification(db, notification_id=notification_id, tenant_id=tenant_id, user_id=user_id)
    db.commit()
    logger.info("notification_deleted", tenant_id=tenant_id, notification_id=notification_id, user_id=user_id)


def delete_read_notifications(db: Session, tenant_id: int, user_id: int) -> int:
    count = notification_repo.delete_read_notifications(db, tenant_id=tenant_id, user_id=user_id)
    db.commit()
    logger.info("notifications_read_deleted", tenant_id=tenant_id, user_id=user_id, count=count)
    return count
