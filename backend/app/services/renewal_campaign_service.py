"""Service de creation de campagnes de renouvellement.

Reutilise le module marketing existant (segments, campaigns) avec le tag 'renouvellement'.
"""

import json

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.renewals import (
    RenewalCampaignCreate,
    RenewalCampaignResponse,
)
from app.repositories import marketing_repo
from app.services import audit_service

logger = get_logger("renewal_campaign_service")

RENEWAL_DEFAULT_TEMPLATE = (
    "Bonjour {{client_name}},\n\n"
    "Cela fait un moment que vous n'avez pas renouvele votre equipement optique. "
    "Votre sante visuelle est importante ! Prenez rendez-vous pour un bilan.\n\n"
    "Cordialement,\nVotre opticien"
)


def create_renewal_campaign(
    db: Session,
    tenant_id: int,
    payload: RenewalCampaignCreate,
    user_id: int,
) -> RenewalCampaignResponse:
    """Cree une campagne de renouvellement via le module marketing."""

    # 1. Creer un segment ad-hoc avec les clients selectionnes
    segment = marketing_repo.create_segment(
        db,
        tenant_id,
        name=f"[Renouvellement] {payload.name}",
        description="Segment genere automatiquement pour campagne de renouvellement",
        rules_json=json.dumps({"type": "renewal", "customer_ids": payload.customer_ids}),
    )
    marketing_repo.refresh_segment_members(
        db,
        segment_id=segment.id,
        tenant_id=tenant_id,
        client_ids=payload.customer_ids,
    )

    # 2. Determiner le template
    template = payload.custom_template or RENEWAL_DEFAULT_TEMPLATE

    # 3. Si IA demandee, generer un message personnalise
    if payload.use_ai_message:
        try:
            from app.services.ai_renewal_copilot import generate_renewal_template

            ai_template = generate_renewal_template(
                db,
                tenant_id,
                channel=payload.channel,
            )
            if ai_template:
                template = ai_template
        except Exception as e:
            logger.warning("ai_renewal_template_fallback", error=str(e))

    # 4. Creer la campagne marketing
    campaign = marketing_repo.create_campaign(
        db,
        tenant_id,
        name=f"[Renouvellement] {payload.name}",
        segment_id=segment.id,
        channel=payload.channel,
        subject=f"Renouvellement - {payload.name}" if payload.channel == "email" else None,
        template=template,
    )

    if user_id:
        audit_service.log_action(
            db,
            tenant_id,
            user_id,
            "create",
            "renewal_campaign",
            campaign.id,
            new_value={"name": payload.name, "customers": len(payload.customer_ids)},
        )
    logger.info(
        "renewal_campaign_created",
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        customer_count=len(payload.customer_ids),
        ai_generated=payload.use_ai_message,
    )

    return RenewalCampaignResponse(
        id=campaign.id,
        name=campaign.name,
        channel=campaign.channel,
        customer_count=len(payload.customer_ids),
        status=campaign.status,
        created_at=campaign.created_at,
    )
