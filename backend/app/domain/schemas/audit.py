from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    entity_type: str
    entity_id: int
    old_value: str | None = None
    new_value: str | None = None
    created_at: datetime
    user_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogSearch(BaseModel):
    entity_type: str | None = None
    entity_id: int | None = None
    user_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


class CompletenessItem(BaseModel):
    code: str
    label: str
    category: str
    is_required: bool
    present: bool


class CompletenessResponse(BaseModel):
    case_id: int
    total_required: int
    total_present: int
    total_missing: int
    items: list[CompletenessItem]
