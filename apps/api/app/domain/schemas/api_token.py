"""Pydantic schemas pour API tokens (admin CRUD)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Liste blanche des scopes supportes en V1 (read-only).
ALLOWED_SCOPES = frozenset(
    {
        "read:clients",
        "read:devis",
        "read:factures",
        "read:pec",
        "read:payments",
        "read:analytics",
    }
)


class ApiTokenCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    scopes: list[str] = Field(..., min_length=1, max_length=20)
    description: str | None = Field(None, max_length=500)
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: list[str]) -> list[str]:
        invalid = [s for s in v if s not in ALLOWED_SCOPES]
        if invalid:
            raise ValueError(
                f"Scopes non supportes : {', '.join(invalid)}. "
                f"V1 supporte uniquement les scopes read:*."
            )
        # Deduplication preservant l'ordre
        seen: set[str] = set()
        out: list[str] = []
        for s in v:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out


class ApiTokenUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=500)
    revoked: bool | None = None
    scopes: list[str] | None = Field(None, min_length=1, max_length=20)

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        invalid = [s for s in v if s not in ALLOWED_SCOPES]
        if invalid:
            raise ValueError(f"Scopes non supportes : {', '.join(invalid)}")
        seen: set[str] = set()
        out: list[str] = []
        for s in v:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out


class ApiTokenResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    prefix: str
    scopes: list[str]
    description: str | None
    expires_at: datetime | None
    revoked: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiTokenCreatedResponse(ApiTokenResponse):
    """Reponse a la creation : inclut le token brut une seule fois."""

    token: str


class AllowedScopesResponse(BaseModel):
    scopes: list[str]
