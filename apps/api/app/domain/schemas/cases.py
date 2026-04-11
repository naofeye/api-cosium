from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.schemas.documents import DocumentResponse
from app.domain.schemas.payments import PaymentResponse


class CaseCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    phone: str | None = None
    email: EmailStr | None = None
    source: str = "manual"


class CaseResponse(BaseModel):
    id: int
    customer_id: int | None = None
    customer_name: str
    status: str
    source: str | None
    created_at: datetime | None = None
    missing_docs: int | None = None

    model_config = ConfigDict(from_attributes=True)


class CaseDetail(BaseModel):
    id: int
    customer_name: str
    status: str
    source: str | None
    phone: str | None
    email: str | None
    documents: list[DocumentResponse] = []
    payments: list[PaymentResponse] = []

    model_config = ConfigDict(from_attributes=True)
