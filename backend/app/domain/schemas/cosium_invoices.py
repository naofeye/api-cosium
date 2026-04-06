"""Schemas for Cosium invoice listing endpoint."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CosiumInvoiceItem(BaseModel):
    """Single Cosium invoice in the list."""

    id: int
    cosium_id: int
    invoice_number: str
    invoice_date: datetime | None = None
    customer_name: str
    customer_id: int | None = None
    type: str
    total_ti: float
    outstanding_balance: float
    share_social_security: float = 0
    share_private_insurance: float = 0
    settled: bool
    archived: bool = False
    site_id: int | None = None
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CosiumInvoiceListResponse(BaseModel):
    """Paginated list of Cosium invoices."""

    items: list[CosiumInvoiceItem]
    total: int
    page: int
    page_size: int
    total_pages: int = 0


class CosiumInvoiceTotals(BaseModel):
    """Aggregate totals for filtered Cosium invoices (across all pages)."""

    total_ttc: float
    total_impaye: float
    count: int
