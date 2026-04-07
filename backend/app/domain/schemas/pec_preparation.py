"""Pydantic schemas for PEC preparation (assistance PEC)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PecPreparationCreate(BaseModel):
    """Request to start a PEC preparation for a client."""

    devis_id: int | None = None
    ocam_operator_id: int | None = None


class FieldValidation(BaseModel):
    """Request to validate a field in a PEC preparation."""

    field_name: str = Field(..., min_length=1)


class FieldCorrection(BaseModel):
    """Request to correct a field in a PEC preparation."""

    field_name: str = Field(..., min_length=1)
    new_value: Any
    reason: str | None = Field(None, max_length=500, description="Raison de la correction")


class DocumentAttach(BaseModel):
    """Request to attach a document to a PEC preparation."""

    document_id: int | None = None
    cosium_document_id: int | None = None
    document_role: str = Field(
        "autre",
        pattern=r"^(ordonnance|devis|attestation_mutuelle|facture|autre)$",
    )
    extraction_id: int | None = None


class PecPreparationDocumentResponse(BaseModel):
    """Response schema for a PEC preparation document."""

    id: int
    preparation_id: int
    document_id: int | None = None
    cosium_document_id: int | None = None
    document_role: str
    extraction_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class UserValidationEntry(BaseModel):
    """A single user validation record."""

    validated: bool = True
    validated_by: int
    at: datetime


class UserCorrectionEntry(BaseModel):
    """A single user correction record."""

    original: Any
    corrected: Any
    by: int
    at: datetime


class PecPreparationResponse(BaseModel):
    """Full PEC preparation response."""

    id: int
    tenant_id: int
    customer_id: int
    devis_id: int | None = None
    pec_request_id: int | None = None
    ocam_operator_id: int | None = None
    consolidated_data: dict | None = None
    status: str
    completude_score: float = 0.0
    errors_count: int = 0
    warnings_count: int = 0
    user_validations: dict | None = None
    user_corrections: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    created_by: int | None = None

    model_config = ConfigDict(from_attributes=True)


class PecPreparationSummary(BaseModel):
    """Short summary for listing PEC preparations."""

    id: int
    customer_id: int
    devis_id: int | None = None
    status: str
    completude_score: float = 0.0
    errors_count: int = 0
    warnings_count: int = 0
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
