"""Pydantic schemas for batch PEC operations."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class BatchCreateRequest(BaseModel):
    """Request to create a batch operation from a marketing code."""

    marketing_code: str = Field(..., min_length=1, max_length=255, description="Code marketing (tag Cosium)")
    label: str | None = Field(None, max_length=255, description="Label descriptif de l'operation")
    date_from: date | None = Field(
        None, description="Date debut pour filtrer les clients (derniere facture ou creation)"
    )
    date_to: date | None = Field(
        None, description="Date fin pour filtrer les clients (derniere facture ou creation)"
    )


class BatchItemResponse(BaseModel):
    """Response for a single item within a batch operation."""

    id: int
    batch_id: int
    customer_id: int
    customer_name: str | None = None
    status: str
    pec_preparation_id: int | None = None
    completude_score: float = 0
    errors_count: int = 0
    warnings_count: int = 0
    error_message: str | None = None
    processed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BatchOperationResponse(BaseModel):
    """Response for a batch operation."""

    id: int
    tenant_id: int
    type: str
    marketing_code: str
    label: str | None = None
    status: str
    total_clients: int = 0
    clients_prets: int = 0
    clients_incomplets: int = 0
    clients_en_conflit: int = 0
    clients_erreur: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: int

    model_config = ConfigDict(from_attributes=True)


class BatchSummaryResponse(BaseModel):
    """Response for batch detail including all items."""

    batch: BatchOperationResponse
    items: list[BatchItemResponse] = []


class MarketingCodeResponse(BaseModel):
    """A marketing code (Cosium tag) with its associated client count."""

    code: str
    description: str = ""
    client_count: int = 0


class BatchPecResult(BaseModel):
    """Result of batch PEC preparation."""

    prepared: int = 0
    skipped: int = 0
    errors: int = 0
