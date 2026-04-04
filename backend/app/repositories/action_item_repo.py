from sqlalchemy import and_, func, select, update
from sqlalchemy import case as sa_case
from sqlalchemy.orm import Session

from app.models import ActionItem

PRIORITY_ORDER = sa_case(
    (ActionItem.priority == "critical", 0),
    (ActionItem.priority == "high", 1),
    (ActionItem.priority == "medium", 2),
    (ActionItem.priority == "low", 3),
    else_=4,
)


def list_by_user(
    db: Session,
    user_id: int,
    tenant_id: int,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ActionItem], int]:
    q = select(ActionItem).where(
        ActionItem.user_id == user_id,
        ActionItem.tenant_id == tenant_id,
    )
    if status:
        q = q.where(ActionItem.status == status)
    if priority:
        q = q.where(ActionItem.priority == priority)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(PRIORITY_ORDER, ActionItem.created_at.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def get_counts_by_type(db: Session, user_id: int, tenant_id: int) -> dict[str, int]:
    rows = db.execute(
        select(ActionItem.type, func.count())
        .where(
            ActionItem.user_id == user_id,
            ActionItem.tenant_id == tenant_id,
            ActionItem.status == "pending",
        )
        .group_by(ActionItem.type)
    ).all()
    return {row[0]: row[1] for row in rows}


def update_status(db: Session, item_id: int, tenant_id: int, status: str) -> None:
    db.execute(
        update(ActionItem)
        .where(
            ActionItem.id == item_id,
            ActionItem.tenant_id == tenant_id,
        )
        .values(status=status)
    )
    db.commit()


def create(
    db: Session,
    tenant_id: int,
    user_id: int,
    type: str,
    title: str,
    description: str | None,
    entity_type: str,
    entity_id: int,
    priority: str = "medium",
    due_date=None,
) -> ActionItem:
    item = ActionItem(
        tenant_id=tenant_id,
        user_id=user_id,
        type=type,
        title=title,
        description=description,
        entity_type=entity_type,
        entity_id=entity_id,
        priority=priority,
        due_date=due_date,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def find_existing(
    db: Session, user_id: int, tenant_id: int, type: str, entity_type: str, entity_id: int
) -> ActionItem | None:
    return db.scalars(
        select(ActionItem).where(
            and_(
                ActionItem.user_id == user_id,
                ActionItem.tenant_id == tenant_id,
                ActionItem.type == type,
                ActionItem.entity_type == entity_type,
                ActionItem.entity_id == entity_id,
                ActionItem.status == "pending",
            )
        )
    ).first()


def delete_resolved(db: Session, user_id: int, tenant_id: int, type: str, entity_type: str, entity_id: int) -> None:
    db.execute(
        update(ActionItem)
        .where(
            and_(
                ActionItem.user_id == user_id,
                ActionItem.tenant_id == tenant_id,
                ActionItem.type == type,
                ActionItem.entity_type == entity_type,
                ActionItem.entity_id == entity_id,
                ActionItem.status == "pending",
            )
        )
        .values(status="done")
    )
    db.commit()
