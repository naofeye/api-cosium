"""Pydantic schemas for PEC audit trail."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

# Type pour les valeurs de champs heterogenes (noms, montants, dates, etc.)
FieldValue = str | int | float | bool | None


class PecAuditEntryResponse(BaseModel):
    """Response schema for a single PEC audit entry."""

    id: int
    tenant_id: int
    preparation_id: int
    action: str
    field_name: str | None = None
    old_value: FieldValue = None
    new_value: FieldValue = None
    source: str | None = None
    user_id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
