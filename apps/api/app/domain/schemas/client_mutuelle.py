"""Pydantic schemas for client-mutuelle associations."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ClientMutuelleCreate(BaseModel):
    """Schema for manually adding a mutuelle to a client."""

    mutuelle_name: str = Field(..., min_length=1, max_length=255)
    mutuelle_id: int | None = None
    numero_adherent: str | None = Field(None, max_length=100)
    type_beneficiaire: str = Field("assure", pattern=r"^(assure|conjoint|enfant)$")
    date_debut: date | None = None
    date_fin: date | None = None
    source: str = "manual"
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class ClientMutuelleResponse(BaseModel):
    """Schema for mutuelle response."""

    id: int
    tenant_id: int
    customer_id: int
    mutuelle_id: int | None = None
    mutuelle_name: str
    numero_adherent: str | None = None
    type_beneficiaire: str = "assure"
    date_debut: date | None = None
    date_fin: date | None = None
    source: str = "cosium_tpp"
    confidence: float = 0.7
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MutuelleDetectionResult(BaseModel):
    """Result of batch mutuelle detection."""

    total_clients_scanned: int = 0
    clients_with_mutuelle: int = 0
    new_mutuelles_created: int = 0
    existing_mutuelles_skipped: int = 0
    errors: int = 0
