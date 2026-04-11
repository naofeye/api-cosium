"""Schemas for Cosium financial and medical data sync."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

# --- Payments ---


class CosiumPaymentResponse(BaseModel):
    id: int
    tenant_id: int
    cosium_id: int
    payment_type_id: int | None = None
    amount: float = 0
    original_amount: float | None = None
    type: str = ""
    due_date: datetime | None = None
    issuer_name: str = ""
    bank: str = ""
    site_name: str = ""
    comment: str | None = None
    payment_number: str = ""
    invoice_cosium_id: int | None = None
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CosiumPaymentList(BaseModel):
    items: list[CosiumPaymentResponse]
    total: int


# --- Third-Party Payments ---


class CosiumThirdPartyPaymentResponse(BaseModel):
    id: int
    tenant_id: int
    cosium_id: int
    social_security_amount: float = 0
    social_security_tpp: bool = False
    additional_health_care_amount: float = 0
    additional_health_care_tpp: bool = False
    invoice_cosium_id: int | None = None
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CosiumThirdPartyPaymentList(BaseModel):
    items: list[CosiumThirdPartyPaymentResponse]
    total: int


# --- Prescriptions ---


class CosiumPrescriptionResponse(BaseModel):
    id: int
    tenant_id: int
    cosium_id: int
    prescription_date: str | None = None
    file_date: datetime | None = None
    customer_cosium_id: int | None = None
    customer_id: int | None = None
    sphere_right: float | None = None
    cylinder_right: float | None = None
    axis_right: float | None = None
    addition_right: float | None = None
    sphere_left: float | None = None
    cylinder_left: float | None = None
    axis_left: float | None = None
    addition_left: float | None = None
    spectacles_json: str | None = None
    prescriber_name: str | None = None
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CosiumPrescriptionList(BaseModel):
    items: list[CosiumPrescriptionResponse]
    total: int


# --- Documents (proxied from Cosium, not stored locally) ---


class CosiumDocumentResponse(BaseModel):
    document_id: int
    label: str = ""
    type: str = ""
    date: str | None = None
    size: int | None = None


class CosiumDocumentList(BaseModel):
    items: list[CosiumDocumentResponse]
    total: int


# --- Local documents (downloaded from Cosium, stored in MinIO) ---


class LocalCosiumDocumentResponse(BaseModel):
    id: int
    customer_cosium_id: int
    cosium_document_id: int
    name: str | None = None
    content_type: str = "application/pdf"
    size_bytes: int = 0
    synced_at: datetime
    source: str = "local"  # always "local" for MinIO-stored docs

    model_config = ConfigDict(from_attributes=True)


class LocalCosiumDocumentList(BaseModel):
    items: list[LocalCosiumDocumentResponse]
    total: int


class DocumentSyncStatusResponse(BaseModel):
    total_documents: int = 0
    customers_with_docs: int = 0
    total_customers: int = 0
    total_size_bytes: int = 0
    total_size_mb: float = 0
    last_sync_at: str | None = None


class BulkSyncRequest(BaseModel):
    max_customers: int | None = None
    delay_docs: float = 1.0
    delay_customers: float = 2.0


# --- Reusable sync result ---


class SyncResultResponse(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    total: int = 0
    fetched: int = 0
    note: str = ""
