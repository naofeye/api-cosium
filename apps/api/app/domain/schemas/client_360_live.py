"""Schemas pour la vue client 360 LIVE Cosium (non-cachee)."""
from pydantic import BaseModel

from app.domain.schemas.fidelity import FidelityCardResponse, SponsorshipResponse
from app.domain.schemas.notes import CosiumNoteResponse


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
    errors: list[str] = []
