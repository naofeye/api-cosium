"""Repository webhooks : queries SQL pures."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.webhook import WebhookDelivery, WebhookSubscription

# --- Subscriptions ---


def list_subscriptions(db: Session, tenant_id: int) -> list[WebhookSubscription]:
    return list(
        db.scalars(
            select(WebhookSubscription)
            .where(WebhookSubscription.tenant_id == tenant_id)
            .order_by(WebhookSubscription.created_at.desc())
        ).all()
    )


def get_subscription(
    db: Session, tenant_id: int, subscription_id: int
) -> WebhookSubscription | None:
    return db.scalars(
        select(WebhookSubscription).where(
            WebhookSubscription.id == subscription_id,
            WebhookSubscription.tenant_id == tenant_id,
        )
    ).first()


def get_active_subscriptions_for_event(
    db: Session, tenant_id: int, event_type: str
) -> list[WebhookSubscription]:
    """Retourne les subs actives du tenant qui ecoutent cet event_type.

    Filtrage event_types fait en Python (JSON column, portabilite SQLite).
    OK car on en a peu (5-10 par tenant max en pratique).
    """
    rows = db.scalars(
        select(WebhookSubscription).where(
            WebhookSubscription.tenant_id == tenant_id,
            WebhookSubscription.is_active.is_(True),
        )
    ).all()
    return [s for s in rows if event_type in (s.event_types or [])]


_SUB_WRITABLE = frozenset(
    {"name", "url", "event_types", "description", "is_active"}
)


def create_subscription(
    db: Session,
    *,
    tenant_id: int,
    secret: str,
    created_by_user_id: int | None,
    fields: dict[str, Any],
) -> WebhookSubscription:
    safe_fields = {k: v for k, v in fields.items() if k in _SUB_WRITABLE}
    sub = WebhookSubscription(
        tenant_id=tenant_id,
        secret=secret,
        created_by_user_id=created_by_user_id,
        **safe_fields,
    )
    db.add(sub)
    db.flush()
    db.refresh(sub)
    return sub


def update_subscription(
    db: Session, subscription: WebhookSubscription, fields: dict[str, Any]
) -> WebhookSubscription:
    for key, value in fields.items():
        if key in _SUB_WRITABLE and value is not None:
            setattr(subscription, key, value)
    db.flush()
    db.refresh(subscription)
    return subscription


def delete_subscription(db: Session, subscription: WebhookSubscription) -> None:
    db.delete(subscription)
    db.flush()


# --- Deliveries ---


def create_delivery(
    db: Session,
    *,
    subscription_id: int,
    tenant_id: int,
    event_type: str,
    event_id: str,
    payload: dict,
) -> WebhookDelivery:
    delivery = WebhookDelivery(
        subscription_id=subscription_id,
        tenant_id=tenant_id,
        event_type=event_type,
        event_id=event_id,
        payload=payload,
    )
    db.add(delivery)
    db.flush()
    db.refresh(delivery)
    return delivery


def get_delivery(
    db: Session, tenant_id: int, delivery_id: int
) -> WebhookDelivery | None:
    return db.scalars(
        select(WebhookDelivery).where(
            WebhookDelivery.id == delivery_id,
            WebhookDelivery.tenant_id == tenant_id,
        )
    ).first()


def get_delivery_for_worker(db: Session, delivery_id: int) -> WebhookDelivery | None:
    """Worker-side fetch (cross-tenant, par id seul)."""
    return db.get(WebhookDelivery, delivery_id)


def list_deliveries(
    db: Session,
    tenant_id: int,
    *,
    subscription_id: int | None = None,
    status: str | None = None,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[WebhookDelivery], int]:
    base = select(WebhookDelivery).where(WebhookDelivery.tenant_id == tenant_id)
    count_base = select(func.count(WebhookDelivery.id)).where(
        WebhookDelivery.tenant_id == tenant_id
    )

    filters = []
    if subscription_id is not None:
        filters.append(WebhookDelivery.subscription_id == subscription_id)
    if status is not None:
        filters.append(WebhookDelivery.status == status)
    if event_type is not None:
        filters.append(WebhookDelivery.event_type == event_type)

    if filters:
        base = base.where(and_(*filters))
        count_base = count_base.where(and_(*filters))

    total = db.scalar(count_base) or 0
    rows = list(
        db.scalars(
            base.order_by(WebhookDelivery.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return rows, int(total)


def update_delivery_status(
    db: Session,
    delivery: WebhookDelivery,
    *,
    status: str,
    attempts: int,
    last_status_code: int | None = None,
    last_error: str | None = None,
    next_retry_at: datetime | None = None,
    delivered_at: datetime | None = None,
    duration_ms: int | None = None,
) -> WebhookDelivery:
    delivery.status = status
    delivery.attempts = attempts
    delivery.last_status_code = last_status_code
    delivery.last_error = last_error
    delivery.next_retry_at = next_retry_at
    delivery.delivered_at = delivered_at
    delivery.duration_ms = duration_ms
    db.flush()
    db.refresh(delivery)
    return delivery
