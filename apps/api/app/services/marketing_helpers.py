"""Helper functions for marketing_service (ROI and A/B stats)."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.cosium_data import CosiumInvoice
from app.models.marketing import MessageLog
from app.repositories import marketing_repo


def get_campaign_roi(db: Session, tenant_id: int, campaign_id: int) -> dict:
    """ROI basique : CA genere par les clients cibles dans les 30j suivant l'envoi."""
    campaign = marketing_repo.get_campaign(db, campaign_id=campaign_id, tenant_id=tenant_id)
    if not campaign:
        raise NotFoundError("campaign", campaign_id)

    sent_at = campaign.sent_at
    if not sent_at:
        return {
            "campaign_id": campaign_id,
            "sent": False,
            "ca_generated": 0.0,
            "conversions": 0,
            "messages_sent": 0,
            "conversion_rate": 0.0,
        }

    window_end = sent_at + timedelta(days=30)

    # Liste des client_id cibles par la campagne
    target_ids = db.scalars(
        select(MessageLog.client_id)
        .where(MessageLog.campaign_id == campaign_id, MessageLog.tenant_id == tenant_id)
        .distinct()
    ).all()

    messages_sent = len(target_ids)
    if not target_ids:
        return {
            "campaign_id": campaign_id,
            "sent": True,
            "ca_generated": 0.0,
            "conversions": 0,
            "messages_sent": 0,
            "conversion_rate": 0.0,
        }

    # CA post-envoi sur les 30j par les clients cibles
    row = db.execute(
        select(
            func.coalesce(func.sum(CosiumInvoice.total_ti), 0),
            func.count(func.distinct(CosiumInvoice.customer_id)),
        ).where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "INVOICE",
            CosiumInvoice.customer_id.in_(target_ids),
            CosiumInvoice.invoice_date >= sent_at,
            CosiumInvoice.invoice_date <= window_end,
        )
    ).one()

    ca = float(row[0] or 0)
    conversions = int(row[1] or 0)
    conversion_rate = round(conversions / messages_sent * 100, 1) if messages_sent else 0.0

    return {
        "campaign_id": campaign_id,
        "sent": True,
        "sent_at": sent_at.isoformat(),
        "window_days": 30,
        "ca_generated": round(ca, 2),
        "conversions": conversions,
        "messages_sent": messages_sent,
        "conversion_rate": conversion_rate,
    }


def get_campaign_ab_stats(db: Session, tenant_id: int, campaign_id: int) -> dict:
    """Compare les variantes A/B d'une campagne : taux d'ouverture/clic/reponse par variant_key."""
    campaign = marketing_repo.get_campaign(db, campaign_id=campaign_id, tenant_id=tenant_id)
    if not campaign:
        raise NotFoundError("campaign", campaign_id)

    rows = db.execute(
        select(
            MessageLog.variant_key,
            func.count().label("sent"),
            func.count(MessageLog.opened_at).label("opened"),
            func.count(MessageLog.clicked_at).label("clicked"),
            func.count(MessageLog.replied_at).label("replied"),
        )
        .where(MessageLog.campaign_id == campaign_id, MessageLog.tenant_id == tenant_id)
        .group_by(MessageLog.variant_key)
    ).all()

    variants = []
    for r in rows:
        sent = int(r.sent or 0)
        variants.append({
            "variant_key": r.variant_key or "default",
            "sent": sent,
            "opened": int(r.opened or 0),
            "clicked": int(r.clicked or 0),
            "replied": int(r.replied or 0),
            "open_rate": round(int(r.opened or 0) / sent * 100, 1) if sent else 0.0,
            "click_rate": round(int(r.clicked or 0) / sent * 100, 1) if sent else 0.0,
            "reply_rate": round(int(r.replied or 0) / sent * 100, 1) if sent else 0.0,
        })

    return {"campaign_id": campaign_id, "variants": variants}
