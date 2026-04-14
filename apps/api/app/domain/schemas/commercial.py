"""Schemas Pydantic pour les operations commerciales Cosium (lecture seule)."""
from pydantic import BaseModel


class AdvantageResponse(BaseModel):
    """Avantage d'une operation commerciale Cosium."""
    cosium_id: int | None = None
    name: str | None = None
    description: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
