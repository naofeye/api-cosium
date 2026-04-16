"""Agrege une timeline unifiee par client : interactions + messages marketing + notes Cosium.

Retourne une liste triee desc par date avec des event typees.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer
from app.models.interaction import Interaction
from app.models.marketing import Campaign, MessageLog

TimelineEvent = dict[str, object]


def _as_iso(d: datetime | None) -> str | None:
    return d.isoformat() if d else None


def _interactions_as_events(db: Session, tenant_id: int, customer_id: int) -> list[TimelineEvent]:
    rows = db.scalars(
        select(Interaction)
        .where(Interaction.tenant_id == tenant_id, Interaction.client_id == customer_id)
        .order_by(Interaction.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "id": f"interaction:{r.id}",
            "kind": "interaction",
            "channel": r.type,
            "direction": r.direction,
            "subject": r.subject,
            "content": r.content or "",
            "date": _as_iso(r.created_at),
        }
        for r in rows
    ]


def _messages_as_events(db: Session, tenant_id: int, customer_id: int) -> list[TimelineEvent]:
    rows = db.execute(
        select(
            MessageLog.id,
            MessageLog.channel,
            MessageLog.status,
            MessageLog.variant_key,
            MessageLog.sent_at,
            MessageLog.opened_at,
            MessageLog.clicked_at,
            MessageLog.replied_at,
            Campaign.name,
        )
        .join(Campaign, Campaign.id == MessageLog.campaign_id)
        .where(MessageLog.tenant_id == tenant_id, MessageLog.client_id == customer_id)
        .order_by(MessageLog.sent_at.desc())
        .limit(100)
    ).all()
    events: list[TimelineEvent] = []
    for r in rows:
        events.append({
            "id": f"message:{r.id}",
            "kind": "campaign_message",
            "channel": r.channel,
            "direction": "sortant",
            "subject": f"Campagne : {r.name}",
            "content": f"Envoyee (variant {r.variant_key or 'default'})",
            "date": _as_iso(r.sent_at),
            "status": r.status,
            "opened_at": _as_iso(r.opened_at),
            "clicked_at": _as_iso(r.clicked_at),
            "replied_at": _as_iso(r.replied_at),
        })
    return events


def build_client_timeline(
    db: Session,
    tenant_id: int,
    customer_id: int,
    kinds: list[Literal["interaction", "campaign_message"]] | None = None,
) -> list[TimelineEvent]:
    """Retourne la timeline client triee desc par date."""
    customer = db.scalars(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    ).first()
    if not customer:
        return []

    selected = set(kinds or ["interaction", "campaign_message"])
    events: list[TimelineEvent] = []
    if "interaction" in selected:
        events.extend(_interactions_as_events(db, tenant_id, customer_id))
    if "campaign_message" in selected:
        events.extend(_messages_as_events(db, tenant_id, customer_id))

    # Tri desc date (None en fin)
    events.sort(key=lambda e: e.get("date") or "", reverse=True)
    return events
