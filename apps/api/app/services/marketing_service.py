import json

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.marketing import (
    CampaignCreate,
    CampaignResponse,
    CampaignStats,
    SegmentCreate,
    SegmentResponse,
)
from app.models import Customer
from app.repositories import marketing_repo
from app.services import audit_service, event_service

logger = get_logger("marketing_service")


# --- Segments ---


def list_segments(db: Session, tenant_id: int) -> list[SegmentResponse]:
    rows = marketing_repo.list_segments(db, tenant_id)
    return [SegmentResponse(**r) for r in rows]


def create_segment(db: Session, tenant_id: int, payload: SegmentCreate, user_id: int) -> SegmentResponse:
    segment = marketing_repo.create_segment(
        db,
        tenant_id,
        payload.name,
        payload.description,
        json.dumps(payload.rules_json),
    )
    # Evaluate rules and populate members
    client_ids = marketing_repo.evaluate_segment_rules(db, tenant_id, payload.rules_json)
    marketing_repo.refresh_segment_members(db, segment_id=segment.id, tenant_id=tenant_id, client_ids=client_ids)

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "create",
            "segment",
            segment.id,
            new_value={"name": payload.name, "members": len(client_ids)},
        )
    logger.info("segment_created", tenant_id=tenant_id, segment_id=segment.id, members=len(client_ids))
    return SegmentResponse(
        id=segment.id,
        name=segment.name,
        description=segment.description,
        rules_json=segment.rules_json,
        member_count=len(client_ids),
        created_at=segment.created_at,
    )


def refresh_segment(db: Session, tenant_id: int, segment_id: int) -> SegmentResponse:
    segment = marketing_repo.get_segment(db, segment_id=segment_id, tenant_id=tenant_id)
    if not segment:
        raise NotFoundError("segment", segment_id)
    rules = json.loads(segment.rules_json)
    client_ids = marketing_repo.evaluate_segment_rules(db, tenant_id, rules)
    marketing_repo.refresh_segment_members(db, segment_id=segment_id, tenant_id=tenant_id, client_ids=client_ids)
    return SegmentResponse(
        id=segment.id,
        name=segment.name,
        description=segment.description,
        rules_json=segment.rules_json,
        member_count=len(client_ids),
        created_at=segment.created_at,
    )


# --- Campaigns ---


def list_campaigns(db: Session, tenant_id: int) -> list[CampaignResponse]:
    rows = marketing_repo.list_campaigns(db, tenant_id)
    return [CampaignResponse(**r) for r in rows]


def create_campaign(db: Session, tenant_id: int, payload: CampaignCreate, user_id: int) -> CampaignResponse:
    segment = marketing_repo.get_segment(db, segment_id=payload.segment_id, tenant_id=tenant_id)
    if not segment:
        raise NotFoundError("segment", payload.segment_id)

    campaign = marketing_repo.create_campaign(
        db,
        tenant_id,
        payload.name,
        payload.segment_id,
        payload.channel,
        payload.subject,
        payload.template,
    )
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "campaign", campaign.id)
    logger.info("campaign_created", tenant_id=tenant_id, campaign_id=campaign.id)
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        segment_id=campaign.segment_id,
        channel=campaign.channel,
        subject=campaign.subject,
        template=campaign.template,
        status=campaign.status,
        scheduled_at=campaign.scheduled_at,
        sent_at=campaign.sent_at,
        created_at=campaign.created_at,
        segment_name=segment.name,
    )


def send_campaign(db: Session, tenant_id: int, campaign_id: int, user_id: int) -> CampaignStats:
    campaign = marketing_repo.get_campaign(db, campaign_id=campaign_id, tenant_id=tenant_id)
    if not campaign:
        raise NotFoundError("campaign", campaign_id)
    if campaign.status == "sent":
        raise BusinessError("Cette campagne a deja ete envoyee", code="CAMPAIGN_ALREADY_SENT")

    member_ids = marketing_repo.get_segment_members(db, segment_id=campaign.segment_id, tenant_id=tenant_id)
    consented_ids = marketing_repo.get_consented_client_ids(db, channel=campaign.channel, tenant_id=tenant_id)
    eligible_ids = [cid for cid in member_ids if cid in consented_ids]

    sent_count = 0
    failed_count = 0

    if campaign.channel == "email":
        from app.integrations.email_sender import email_sender

        for client_id in eligible_ids:
            customer = db.get(Customer, client_id)
            if not customer or not customer.email:
                marketing_repo.add_message_log(db, tenant_id, campaign_id, client_id, campaign.channel, "failed")
                failed_count += 1
                continue

            body = campaign.template
            body = body.replace("{{client_name}}", f"{customer.first_name} {customer.last_name}")
            body = body.replace("{{prenom}}", customer.first_name)

            success = email_sender.send_email(
                to=customer.email,
                subject=campaign.subject or campaign.name,
                body_html=f"<div>{body}</div>",
            )
            status = "sent" if success else "failed"
            marketing_repo.add_message_log(db, tenant_id, campaign_id, client_id, campaign.channel, status)
            if success:
                sent_count += 1
            else:
                failed_count += 1
    else:
        for client_id in eligible_ids:
            marketing_repo.add_message_log(db, tenant_id, campaign_id, client_id, campaign.channel, "sent")
            sent_count += 1

    db.commit()
    marketing_repo.update_campaign_status(db, campaign, "sent")

    if user_id:
        event_service.emit_event(db, tenant_id, "CampagneLancee", "campaign", campaign_id, user_id)
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "update",
            "campaign",
            campaign_id,
            new_value={"sent": sent_count, "failed": failed_count},
        )

    logger.info("campaign_sent", tenant_id=tenant_id, campaign_id=campaign_id, sent=sent_count, failed=failed_count)
    return CampaignStats(
        campaign_id=campaign_id,
        total_sent=sent_count,
        total_delivered=0,
        total_failed=failed_count,
        total_opened=0,
        total_clicked=0,
    )


def get_campaign_stats(db: Session, tenant_id: int, campaign_id: int) -> CampaignStats:
    campaign = marketing_repo.get_campaign(db, campaign_id=campaign_id, tenant_id=tenant_id)
    if not campaign:
        raise NotFoundError("campaign", campaign_id)
    stats = marketing_repo.get_campaign_stats(db, campaign_id=campaign_id, tenant_id=tenant_id)
    return CampaignStats(campaign_id=campaign_id, **stats)


def get_campaign_roi(db: Session, tenant_id: int, campaign_id: int) -> dict:
    """ROI basique : CA genere par les clients cibles dans les 30j suivant l'envoi."""
    from datetime import timedelta
    from sqlalchemy import func, select
    from app.models.marketing import Campaign, MessageLog
    from app.models.cosium_data import CosiumInvoice

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
    from sqlalchemy import func, select
    from app.models.marketing import MessageLog

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
