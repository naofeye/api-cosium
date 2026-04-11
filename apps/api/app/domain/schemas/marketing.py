from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# --- Consents ---


class ConsentResponse(BaseModel):
    id: int
    client_id: int
    channel: str
    consented: bool
    consented_at: datetime | None = None
    revoked_at: datetime | None = None
    source: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConsentUpdate(BaseModel):
    consented: bool
    source: str | None = None


# --- Segments ---


class SegmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    rules_json: dict = Field(default_factory=dict)


class SegmentResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    rules_json: str
    member_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Campaigns ---


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    segment_id: int
    channel: str = Field("email", pattern="^(email|sms)$")
    subject: str | None = None
    template: str = Field(..., min_length=1)


class CampaignResponse(BaseModel):
    id: int
    name: str
    segment_id: int
    channel: str
    subject: str | None = None
    template: str
    status: str
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    created_at: datetime
    segment_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CampaignStats(BaseModel):
    campaign_id: int
    total_sent: int
    total_delivered: int
    total_failed: int
    total_opened: int
    total_clicked: int
