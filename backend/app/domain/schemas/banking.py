from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PaymentCreate(BaseModel):
    case_id: int
    facture_id: int | None = None
    payer_type: str = Field(..., min_length=1, max_length=50)
    mode_paiement: str | None = None
    reference_externe: str | None = None
    date_paiement: datetime | None = None
    amount_due: float = Field(0, ge=0)
    amount_paid: float = Field(..., gt=0, description="Montant paye, doit etre strictement positif")

    @model_validator(mode="after")
    def validate_amounts(self) -> "PaymentCreate":
        """Validate that amount_paid does not exceed amount_due when amount_due is set."""
        if self.amount_due > 0 and self.amount_paid > self.amount_due:
            msg = (
                f"Le montant paye ({self.amount_paid}) ne peut pas depasser "
                f"le montant du ({self.amount_due})"
            )
            raise ValueError(msg)
        return self


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
    skipped: int = 0
