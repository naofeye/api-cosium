"""Schemas Pydantic pour les cartes de fidelite et parrainages Cosium (lecture seule)."""
from pydantic import BaseModel


class FidelityCardResponse(BaseModel):
    """Carte de fidelite Cosium."""
    cosium_id: int | None = None
    card_number: str | None = None
    amount: float | None = None
    remaining_amount: float | None = None
    remaining_consumable_amount: float | None = None
    creation_date: str | None = None
    expiration_date: str | None = None


class SponsorshipResponse(BaseModel):
    """Parrainage Cosium."""
    cosium_id: int | None = None
    sponsored_first_name: str | None = None
    sponsored_last_name: str | None = None
    amount: float | None = None
    remaining_amount: float | None = None
    creation_date: str | None = None
    consumed: bool = False
