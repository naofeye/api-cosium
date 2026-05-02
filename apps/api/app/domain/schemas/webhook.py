"""Pydantic schemas pour les endpoints webhook."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

# Liste blanche d'evenements emis. Toute future addition doit etre documentee
# dans docs/WEBHOOKS.md.
ALLOWED_EVENT_TYPES = frozenset(
    {
        "client.created",
        "client.updated",
        "client.merged",
        "client.deleted",
        "facture.created",
        "facture.avoir_created",
        "facture.deleted",
        "devis.created",
        "devis.signed",
        "devis.refused",
        "pec.submitted",
        "pec.accepted",
        "pec.refused",
        "payment.received",
        "campaign.sent",
    }
)


class SubscriptionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    url: HttpUrl
    event_types: list[str] = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=500)

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, v: list[str]) -> list[str]:
        invalid = [e for e in v if e not in ALLOWED_EVENT_TYPES]
        if invalid:
            raise ValueError(
                f"Event types non supportes : {', '.join(invalid)}. "
                f"Voir documentation pour la liste complete."
            )
        # deduplique en preservant l'ordre
        seen: set[str] = set()
        out: list[str] = []
        for e in v:
            if e not in seen:
                seen.add(e)
                out.append(e)
        return out


class SubscriptionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    url: HttpUrl | None = None
    event_types: list[str] | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=500)
    is_active: bool | None = None

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        invalid = [e for e in v if e not in ALLOWED_EVENT_TYPES]
        if invalid:
            raise ValueError(
                f"Event types non supportes : {', '.join(invalid)}."
            )
        seen: set[str] = set()
        out: list[str] = []
        for e in v:
            if e not in seen:
                seen.add(e)
                out.append(e)
        return out


class SubscriptionResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    url: str
    event_types: list[str]
    is_active: bool
    description: str | None
    created_at: datetime
    updated_at: datetime
    # Le secret n'est expose qu'a la creation (champ secret_full_once-shown).
    # Apres ca, on retourne uniquement un masque.
    secret_masked: str

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreatedResponse(SubscriptionResponse):
    """Reponse a la creation : inclut le secret en clair une seule fois."""

    secret: str


class DeliveryResponse(BaseModel):
    id: int
    subscription_id: int
    tenant_id: int
    event_type: str
    event_id: str
    status: str
    attempts: int
    last_status_code: int | None
    last_error: str | None
    next_retry_at: datetime | None
    delivered_at: datetime | None
    duration_ms: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryListResponse(BaseModel):
    items: list[DeliveryResponse]
    total: int


class AllowedEventsResponse(BaseModel):
    events: list[str]
