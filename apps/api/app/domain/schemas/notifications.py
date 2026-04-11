from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    entity_type: str | None = None
    entity_id: int | None = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    page: int = 1
    page_size: int = 25
    total_pages: int = 0
    unread_count: int


class UnreadCountResponse(BaseModel):
    count: int


class ActionItemResponse(BaseModel):
    id: int
    type: str
    title: str
    description: str | None = None
    entity_type: str
    entity_id: int
    priority: str
    status: str
    due_date: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActionItemUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|done|dismissed)$")


class ActionItemListResponse(BaseModel):
    items: list[ActionItemResponse]
    total: int
    counts: dict[str, int]
