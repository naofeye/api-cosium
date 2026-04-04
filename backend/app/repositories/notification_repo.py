from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import Notification


def list_by_user(
    db: Session, user_id: int, tenant_id: int, unread_only: bool = False, limit: int = 50, offset: int = 0
) -> tuple[list[Notification], int]:
    q = select(Notification).where(
        Notification.user_id == user_id,
        Notification.tenant_id == tenant_id,
    )
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Notification.created_at.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def get_unread_count(db: Session, user_id: int, tenant_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.tenant_id == tenant_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )


def mark_read(db: Session, notification_id: int, tenant_id: int) -> None:
    db.execute(
        update(Notification)
        .where(
            Notification.id == notification_id,
            Notification.tenant_id == tenant_id,
        )
        .values(is_read=True)
    )
    db.commit()


def mark_all_read(db: Session, user_id: int, tenant_id: int) -> None:
    db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    db.commit()


def create(
    db: Session,
    tenant_id: int,
    user_id: int,
    type: str,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Notification:
    notif = Notification(
        tenant_id=tenant_id,
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif
