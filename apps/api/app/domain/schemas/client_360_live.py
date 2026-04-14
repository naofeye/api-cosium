"""Schemas pour la vue client 360 LIVE Cosium (non-cachee)."""
from pydantic import BaseModel

from app.domain.schemas.fidelity import FidelityCardResponse, SponsorshipResponse
from app.domain.schemas.notes import CosiumNoteResponse


class CosiumConsents(BaseModel):
    """Consentements marketing du client cote Cosium (lecture seule)."""
    email_consent: bool | None = None
    sms_consent: bool | None = None
    whatsapp_consent: bool | None = None
    exclude_all_consent: bool | None = None


class Client360CosiumLive(BaseModel):
    """Donnees client recuperees en LIVE depuis Cosium (non cachees).

    Si le client n'a pas de cosium_id, retourne des listes vides.
    Si Cosium est inaccessible, les sections en erreur sont vides + flag errors.
    """
    customer_id: int
    cosium_id: int | None = None
    fidelity_cards: list[FidelityCardResponse] = []
    sponsorships: list[SponsorshipResponse] = []
    notes: list[CosiumNoteResponse] = []
    consents: CosiumConsents | None = None
    errors: list[str] = []
