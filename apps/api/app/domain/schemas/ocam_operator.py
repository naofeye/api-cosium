"""Pydantic schemas for OCAM operators."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OcamSpecificRule(BaseModel):
    """Une regle specifique d'un operateur OCAM."""

    field: str
    rule_type: str  # "required", "format", "max_length", etc.
    value: str | int | bool | None = None
    message: str | None = None


class OcamOperatorCreate(BaseModel):
    """Request to create an OCAM operator."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str | None = Field(None, max_length=50)
    portal_url: str | None = Field(None, max_length=500)
    required_fields: list[str] | None = None
    required_documents: list[str] | None = None
    specific_rules: list[OcamSpecificRule] | None = None
    active: bool = True


class OcamOperatorResponse(BaseModel):
    """Response for an OCAM operator."""

    id: int
    tenant_id: int
    name: str
    code: str | None = None
    portal_url: str | None = None
    required_fields: list[str] | None = None
    required_documents: list[str] | None = None
    specific_rules: list[OcamSpecificRule] | None = None
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
