from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InteractionCreate(BaseModel):
    client_id: int
    case_id: int | None = None
    type: str = Field(..., pattern="^(appel|email|sms|visite|note|tache)$")
    direction: str = Field("interne", pattern="^(entrant|sortant|interne)$")
    subject: str = Field(..., min_length=1, max_length=200)
    content: str | None = None


class InteractionResponse(BaseModel):
    id: int
    client_id: int
    case_id: int | None = None
    type: str
    direction: str
    subject: str
    content: str | None = None
    created_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InteractionListResponse(BaseModel):
    items: list[InteractionResponse]
    total: int
