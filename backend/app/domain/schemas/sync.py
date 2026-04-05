"""Schemas for ERP sync endpoints."""

from pydantic import BaseModel


class SyncStatusResponse(BaseModel):
    configured: bool
    authenticated: bool = False
    erp_type: str = "cosium"
    tenant_name: str | None = None
    last_sync_at: str | None = None
    first_sync_done: bool = False


class SyncResultResponse(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    total: int = 0
    fetched: int = 0
    note: str = ""


class ERPTypeItem(BaseModel):
    type: str
    status: str
    label: str


class SyncAllResult(BaseModel):
    """Result of a full sync across all ERP domains."""

    customers: SyncResultResponse | dict | None = None
    invoices: SyncResultResponse | dict | None = None
    payments: SyncResultResponse | dict | None = None
    prescriptions: SyncResultResponse | dict | None = None
    reference: dict | None = None
    has_errors: bool = False


class SeedDemoResponse(BaseModel):
    status: str = ""
    reason: str = ""
    clients: int = 0
    cases: int = 0
    devis: int = 0
    factures: int = 0
    payments: int = 0
    pec: int = 0
    bank_transactions: int = 0
    campaigns: int = 0
    interactions: int = 0
