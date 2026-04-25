from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    Campaign,
    Customer,
    MarketingConsent,
    MessageLog,
    Segment,
    SegmentMembership,
)

# --- Consents ---


def get_consents(db: Session, client_id: int, tenant_id: int) -> list[MarketingConsent]:
    return list(
        db.scalars(
            select(MarketingConsent).where(
                MarketingConsent.client_id == client_id,
                MarketingConsent.tenant_id == tenant_id,
            )
        ).all()
    )


def get_consent(db: Session, client_id: int, channel: str, tenant_id: int) -> MarketingConsent | None:
    return db.scalars(
        select(MarketingConsent).where(
            MarketingConsent.client_id == client_id,
            MarketingConsent.channel == channel,
            MarketingConsent.tenant_id == tenant_id,
        )
    ).first()


def upsert_consent(
    db: Session, tenant_id: int, client_id: int, channel: str, consented: bool, source: str | None
) -> MarketingConsent:
    existing = get_consent(db, client_id, channel, tenant_id)
    now = datetime.now(UTC).replace(tzinfo=None)
    if existing:
        existing.consented = consented
        existing.source = source
        if consented:
            existing.consented_at = now
            existing.revoked_at = None
        else:
            existing.revoked_at = now
        db.flush()
        db.refresh(existing)
        return existing
    consent = MarketingConsent(
        tenant_id=tenant_id,
        client_id=client_id,
        channel=channel,
        consented=consented,
        consented_at=now if consented else None,
        revoked_at=now if not consented else None,
        source=source,
    )
    db.add(consent)
    db.flush()
    db.refresh(consent)
    return consent


def check_consent(db: Session, client_id: int, channel: str, tenant_id: int) -> bool:
    c = get_consent(db, client_id, channel, tenant_id)
    return c.consented if c else False


def get_consented_client_ids(db: Session, channel: str, tenant_id: int) -> set[int]:
    rows = db.execute(
        select(MarketingConsent.client_id).where(
            MarketingConsent.channel == channel,
            MarketingConsent.consented.is_(True),
            MarketingConsent.tenant_id == tenant_id,
        )
    ).all()
    return {r[0] for r in rows}


# --- Segments ---


def list_segments(db: Session, tenant_id: int) -> list[dict]:
    segments = db.scalars(select(Segment).where(Segment.tenant_id == tenant_id).order_by(Segment.id.desc())).all()
    results = []
    for s in segments:
        count = (
            db.scalar(select(func.count()).select_from(SegmentMembership).where(SegmentMembership.segment_id == s.id))
            or 0
        )
        results.append(
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "rules_json": s.rules_json,
                "member_count": count,
                "created_at": s.created_at,
            }
        )
    return results


def get_segment(db: Session, segment_id: int, tenant_id: int) -> Segment | None:
    return db.scalars(
        select(Segment).where(
            Segment.id == segment_id,
            Segment.tenant_id == tenant_id,
        )
    ).first()


def create_segment(db: Session, tenant_id: int, name: str, description: str | None, rules_json: str) -> Segment:
    s = Segment(tenant_id=tenant_id, name=name, description=description, rules_json=rules_json)
    db.add(s)
    db.flush()
    db.refresh(s)
    return s


def get_segment_members(db: Session, segment_id: int, tenant_id: int) -> list[int]:
    rows = db.execute(
        select(SegmentMembership.client_id)
        .join(Segment, Segment.id == SegmentMembership.segment_id)
        .where(
            SegmentMembership.segment_id == segment_id,
            Segment.tenant_id == tenant_id,
        )
    ).all()
    return [r[0] for r in rows]


def refresh_segment_members(db: Session, segment_id: int, tenant_id: int, client_ids: list[int]) -> None:
    # Verify segment belongs to tenant before refreshing
    segment = get_segment(db, segment_id, tenant_id)
    if not segment:
        return
    db.execute(delete(SegmentMembership).where(SegmentMembership.segment_id == segment_id))
    for cid in client_ids:
        db.add(SegmentMembership(tenant_id=tenant_id, segment_id=segment_id, client_id=cid))
    db.flush()


def evaluate_segment_rules(db: Session, tenant_id: int, rules: dict) -> list[int]:
    q = select(Customer.id).where(Customer.tenant_id == tenant_id)
    if "city" in rules and rules["city"]:
        q = q.where(Customer.city == rules["city"])
    if "postal_code" in rules and rules["postal_code"]:
        q = q.where(Customer.postal_code == rules["postal_code"])
    if "has_email" in rules and rules["has_email"]:
        q = q.where(Customer.email.isnot(None))
    if "has_phone" in rules and rules["has_phone"]:
        q = q.where(Customer.phone.isnot(None))
    rows = db.execute(q).all()
    return [r[0] for r in rows]


# --- Campaigns ---


def list_campaigns(db: Session, tenant_id: int) -> list[dict]:
    rows = db.execute(
        select(
            Campaign.id,
            Campaign.name,
            Campaign.segment_id,
            Campaign.channel,
            Campaign.subject,
            Campaign.template,
            Campaign.status,
            Campaign.scheduled_at,
            Campaign.sent_at,
            Campaign.created_at,
            Segment.name.label("segment_name"),
        )
        .join(Segment, Segment.id == Campaign.segment_id)
        .where(Campaign.tenant_id == tenant_id)
        .order_by(Campaign.id.desc())
    ).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "segment_id": r.segment_id,
            "channel": r.channel,
            "subject": r.subject,
            "template": r.template,
            "status": r.status,
            "scheduled_at": r.scheduled_at,
            "sent_at": r.sent_at,
            "created_at": r.created_at,
            "segment_name": r.segment_name,
        }
        for r in rows
    ]


def create_campaign(
    db: Session, tenant_id: int, name: str, segment_id: int, channel: str, subject: str | None, template: str
) -> Campaign:
    c = Campaign(
        tenant_id=tenant_id,
        name=name,
        segment_id=segment_id,
        channel=channel,
        subject=subject,
        template=template,
    )
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def get_campaign(db: Session, campaign_id: int, tenant_id: int) -> Campaign | None:
    return db.scalars(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
        )
    ).first()


def update_campaign_status(db: Session, campaign: Campaign, status: str) -> None:
    campaign.status = status
    if status == "sent":
        campaign.sent_at = datetime.now(UTC).replace(tzinfo=None)
    db.flush()


def add_message_log(
    db: Session, tenant_id: int, campaign_id: int, client_id: int, channel: str, status: str
) -> MessageLog:
    m = MessageLog(
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        client_id=client_id,
        channel=channel,
        status=status,
    )
    db.add(m)
    return m


def get_campaign_stats(db: Session, campaign_id: int, tenant_id: int) -> dict[str, int]:
    rows = db.execute(
        select(MessageLog.status, func.count())
        .where(
            MessageLog.campaign_id == campaign_id,
            MessageLog.tenant_id == tenant_id,
        )
        .group_by(MessageLog.status)
    ).all()
    stats = {r[0]: r[1] for r in rows}
    return {
        "total_sent": stats.get("sent", 0),
        "total_delivered": stats.get("delivered", 0),
        "total_failed": stats.get("failed", 0),
        "total_opened": stats.get("opened", 0),
        "total_clicked": stats.get("clicked", 0),
    }
