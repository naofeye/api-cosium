from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReminderPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    payer_type: str = Field(..., pattern="^(client|mutuelle|secu)$")
    rules_json: dict = Field(default_factory=lambda: {"min_days_overdue": 7, "min_amount": 0, "max_reminders": 3})
    channel_sequence: list[str] = Field(default_factory=lambda: ["email"])
    interval_days: int = Field(7, ge=1)
    is_active: bool = True


class ReminderPlanResponse(BaseModel):
    id: int
    name: str
    payer_type: str
    rules_json: str
    channel_sequence: str
    interval_days: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReminderCreate(BaseModel):
    target_type: str = Field(..., pattern="^(client|payer_organization)$")
    target_id: int
    facture_id: int | None = None
    pec_request_id: int | None = None
    channel: str = Field("email", pattern="^(email|sms|courrier|telephone)$")
    content: str | None = None


class ReminderResponse(BaseModel):
    id: int
    plan_id: int | None = None
    target_type: str
    target_id: int
    facture_id: int | None = None
    pec_request_id: int | None = None
    channel: str
    status: str
    template_used: str | None = None
    content: str | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    response_notes: str | None = None
    created_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReminderTemplateResponse(BaseModel):
    id: int
    name: str
    channel: str
    payer_type: str
    subject: str | None = None
    body: str
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReminderTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1)
    channel: str = Field("email")
    payer_type: str = Field("client")
    subject: str | None = None
    body: str = Field(..., min_length=1)
    is_default: bool = False


class OverdueItem(BaseModel):
    entity_type: str
    entity_id: int
    customer_name: str
    payer_type: str
    amount: float
    days_overdue: int
    score: float
    action: str


class ReminderStats(BaseModel):
    total_overdue_amount: float
    total_reminders_sent: int
    total_responded: int
    recovery_rate: float
    overdue_by_age: dict[str, float]


class ReminderListResponse(BaseModel):
    items: list[ReminderResponse]
    total: int


class AutoGenerateResponse(BaseModel):
    status: str
    plans: dict[str, int] = {}
