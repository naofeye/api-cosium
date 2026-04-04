from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    case_id: int
    facture_id: int | None = None
    payer_type: str = Field(..., min_length=1, max_length=50)
    mode_paiement: str | None = None
    reference_externe: str | None = None
    date_paiement: datetime | None = None
    amount_due: float = Field(0, ge=0)
    amount_paid: float = Field(..., ge=0)


class PaymentResponse(BaseModel):
    id: int
    case_id: int
    facture_id: int | None = None
    payer_type: str
    mode_paiement: str | None = None
    reference_externe: str | None = None
    date_paiement: datetime | None = None
    amount_due: float
    amount_paid: float
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BankTransactionResponse(BaseModel):
    id: int
    date: datetime
    libelle: str
    montant: float
    reference: str | None = None
    source_file: str | None = None
    reconciled: bool
    reconciled_payment_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BankTransactionListResponse(BaseModel):
    items: list[BankTransactionResponse]
    total: int


class ReconcileRequest(BaseModel):
    transaction_id: int
    payment_id: int


class ReconcileResult(BaseModel):
    matched: int
    unmatched: int


class ImportStatementResult(BaseModel):
    imported: int
