"""Pydantic schemas for PEC audit trail."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PecAuditEntryResponse(BaseModel):
    """Response schema for a single PEC audit entry."""

    id: int
    tenant_id: int
    preparation_id: int
    action: str
    field_name: str | None = None
    old_value: Any | None = None
    new_value: Any | None = None
    source: str | None = None
    user_id: int
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
