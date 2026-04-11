"""Pydantic schemas for the reconciliation module."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnomalyItem(BaseModel):
    """A single anomaly detected during reconciliation."""

    type: str = Field(..., description="Type d'anomalie: surpaiement, ecart, doublon, sans_facture, etc.")
    severity: str = Field("warning", description="Severite: info, warning, error")
    message: str = Field(..., description="Description humaine de l'anomalie")
    invoice_number: str | None = None
    amount: float | None = None


class PaymentMatch(BaseModel):
    """A payment matched to an invoice."""

    payment_id: int
    cosium_id: int
    amount: float
    type: str  # CB, CHQ, ESP, TPSV, TPMV, ALMA, AV, VIR
    category: str  # secu, mutuelle, client, avoir
    issuer_name: str = ""
    due_date: datetime | None = None
    payment_number: str = ""


class InvoiceReconciliation(BaseModel):
    """Per-invoice reconciliation detail."""

    invoice_id: int
    cosium_id: int
    invoice_number: str
    invoice_date: datetime | None = None
    total_ti: float
    outstanding_balance: float
    share_social_security: float = 0
    share_private_insurance: float = 0
    settled: bool
    payments: list[PaymentMatch] = Field(default_factory=list)
    total_paid: float = 0
    paid_secu: float = 0
    paid_mutuelle: float = 0
    paid_client: float = 0
    paid_avoir: float = 0
    status: str = "en_attente"  # solde, partiellement_paye, en_attente, incoherent
    anomalies: list[AnomalyItem] = Field(default_factory=list)


class DossierReconciliationResponse(BaseModel):
    """Full reconciliation result for a customer."""

    id: int
    tenant_id: int
    customer_id: int
    customer_name: str = ""
    status: str
    confidence: str
    total_facture: float
    total_outstanding: float
    total_paid: float
    total_secu: float
    total_mutuelle: float
    total_client: float
    total_avoir: float
    invoice_count: int
    payment_count: int
    quote_count: int
    credit_note_count: int
    has_pec: bool
    pec_status: str | None = None
    invoices: list[InvoiceReconciliation] = Field(default_factory=list)
    anomalies: list[AnomalyItem] = Field(default_factory=list)
    explanation: str = ""
    reconciled_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReconciliationSummary(BaseModel):
    """Batch overview of reconciliation results."""

    total_customers: int
    solde: int = 0
    solde_non_rapproche: int = 0
    partiellement_paye: int = 0
    en_attente: int = 0
    incoherent: int = 0
    info_insuffisante: int = 0
    total_facture: float = 0
    total_outstanding: float = 0
    total_paid: float = 0


class ReconciliationListItem(BaseModel):
    """Single item in the reconciliation list."""

    customer_id: int
    customer_name: str
    status: str
    confidence: str
    total_facture: float
    total_outstanding: float
    total_paid: float
    total_secu: float
    total_mutuelle: float
    total_client: float
    total_avoir: float
    invoice_count: int
    has_pec: bool
    explanation: str = ""
    reconciled_at: datetime


class ReconciliationListResponse(BaseModel):
    """Paginated list of reconciliations."""

    items: list[ReconciliationListItem]
    total: int
    page: int
    page_size: int


class LinkPaymentsResult(BaseModel):
    """Result of the payment-to-customer linking process."""

    total_payments: int
    already_linked: int
    newly_linked: int
    unmatched: int


class BatchReconciliationResult(BaseModel):
    """Result of batch reconciliation."""

    total_processed: int
    summary: ReconciliationSummary
    anomaly_count: int
