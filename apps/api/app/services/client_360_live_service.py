"""Vue client 360 LIVE — agrege les appels Cosium en temps reel.

Pas de cache : chaque appel touche Cosium. Utiliser pour la fiche client
quand on veut la donnee la plus fraiche (vs le cache local).
"""
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.client_360_live import Client360CosiumLive, CosiumConsents
from app.domain.schemas.fidelity import FidelityCardResponse, SponsorshipResponse
from app.domain.schemas.notes import CosiumNoteResponse
from app.integrations.cosium.adapter import (
    cosium_fidelity_card_to_optiflow,
    cosium_note_to_optiflow,
    cosium_sponsorship_to_optiflow,
)
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.repositories import client_repo
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("client_360_live_service")


def get_client_cosium_live(db: Session, tenant_id: int, client_id: int) -> Client360CosiumLive:
    """Agrege fidelity + sponsorships + notes en LIVE depuis Cosium."""
    customer = client_repo.get_by_id(db, client_id, tenant_id)
    if not customer:
        raise NotFoundError("Client", client_id)

    cosium_id_raw = getattr(customer, "cosium_id", None)
    if not cosium_id_raw:
        return Client360CosiumLive(customer_id=client_id, cosium_id=None)

    try:
        cosium_id = int(cosium_id_raw)
    except (ValueError, TypeError):
        return Client360CosiumLive(
            customer_id=client_id, cosium_id=None,
            errors=[f"cosium_id non numerique: {cosium_id_raw}"],
        )

    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    if not isinstance(connector, CosiumConnector):
        return Client360CosiumLive(
            customer_id=client_id, cosium_id=cosium_id,
            errors=["Tenant n'utilise pas Cosium"],
        )

    try:
        _authenticate_connector(connector, tenant)
    except Exception as e:
        logger.warning("client_360_live_auth_failed", error=str(e))
        return Client360CosiumLive(
            customer_id=client_id, cosium_id=cosium_id,
            errors=[f"Authentification Cosium echouee: {str(e)[:100]}"],
        )

    errors: list[str] = []
    fidelity: list[FidelityCardResponse] = []
    sponsorships: list[SponsorshipResponse] = []
    notes: list[CosiumNoteResponse] = []

    try:
        raw = connector.list_customer_fidelity_cards(cosium_id)
        fidelity = [FidelityCardResponse(**cosium_fidelity_card_to_optiflow(c)) for c in raw]
    except Exception as e:
        errors.append(f"fidelity-cards: {str(e)[:100]}")
        logger.warning("client_360_live_fidelity_failed", cosium_id=cosium_id, error=str(e))

    try:
        raw = connector.list_customer_sponsorships(cosium_id)
        sponsorships = [SponsorshipResponse(**cosium_sponsorship_to_optiflow(s)) for s in raw]
    except Exception as e:
        errors.append(f"sponsorships: {str(e)[:100]}")
        logger.warning("client_360_live_sponsorships_failed", cosium_id=cosium_id, error=str(e))

    try:
        raw = connector.list_notes_for_customer(cosium_id)
        notes = [CosiumNoteResponse(**cosium_note_to_optiflow(n)) for n in raw]
    except Exception as e:
        errors.append(f"notes: {str(e)[:100]}")
        logger.warning("client_360_live_notes_failed", cosium_id=cosium_id, error=str(e))

    consents: CosiumConsents | None = None
    try:
        raw_c = connector.get_customer_consents(cosium_id)
        consents = CosiumConsents(
            email_consent=raw_c.get("emailConsent"),
            sms_consent=raw_c.get("smsConsent"),
            whatsapp_consent=raw_c.get("whatsappConsent"),
            exclude_all_consent=raw_c.get("excludeAllConsent"),
        )
    except Exception as e:
        errors.append(f"consents: {str(e)[:100]}")
        logger.warning("client_360_live_consents_failed", cosium_id=cosium_id, error=str(e))

    logger.info(
        "client_360_live_fetched",
        client_id=client_id, cosium_id=cosium_id,
        fidelity=len(fidelity), sponsorships=len(sponsorships), notes=len(notes),
        errors=len(errors),
    )
    return Client360CosiumLive(
        customer_id=client_id,
        cosium_id=cosium_id,
        fidelity_cards=fidelity,
        sponsorships=sponsorships,
        notes=notes,
        consents=consents,
        errors=errors,
    )
