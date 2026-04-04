from pydantic import BaseModel, ConfigDict


class PaymentResponse(BaseModel):
    id: int
    payer_type: str
    amount_due: float
    amount_paid: float
    status: str

    model_config = ConfigDict(from_attributes=True)


class PaymentSummary(BaseModel):
    case_id: int
    total_due: float
    total_paid: float
    remaining: float
    items: list[PaymentResponse]
