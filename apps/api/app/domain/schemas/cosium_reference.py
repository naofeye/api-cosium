"""Pydantic schemas for Cosium reference data endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.schemas.cosium_sync import CosiumPaymentResponse, CosiumPrescriptionResponse

# --- Calendar Events ---

class CalendarEventResponse(BaseModel):
    id: int
    tenant_id: int
    cosium_id: int
    start_date: datetime | None = None
    end_date: datetime | None = None
    subject: str = ""
    customer_fullname: str = ""
    customer_number: str = ""
    category_name: str = ""
    category_color: str = ""
    category_family: str = ""
    status: str = ""
    canceled: bool = False
    missed: bool = False
    customer_arrived: bool = False
    observation: str | None = None
    site_name: str | None = None
    modification_date: datetime | None = None
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Mutuelles ---

class MutuelleResponse(BaseModel):
    id: int
    tenant_id: int
    cosium_id: int
    name: str = ""
    code: str = ""
    label: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    hidden: bool = False
    opto_amc: bool = False
    coverage_request_phone: str = ""
    coverage_request_email: str = ""
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Doctors ---

class DoctorResponse(BaseModel):
    id: int
    tenant_id: int
    cosium_id: str
    firstname: str = ""
    lastname: str = ""
    civility: str = ""
    email: str | None = None
    phone: str | None = None
    rpps_number: str | None = None
    specialty: str = ""
    optic_prescriber: bool = False
    audio_prescriber: bool = False
    hidden: bool = False
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Brands ---

class BrandResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Suppliers ---

class SupplierResponse(BaseModel):
    id: int
    tenant_id: int
    name: str
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Tags ---

class TagResponse(BaseModel):
    id: int
    tenant_id: int
    cosium_id: int
    code: str = ""
    description: str = ""
    hidden: bool = False
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Sites ---

class SiteResponse(BaseModel):
    id: int
    tenant_id: int
    cosium_id: int
    name: str = ""
    code: str = ""
    long_label: str = ""
    address: str = ""
    postcode: str = ""
    city: str = ""
    country: str = ""
    phone: str = ""
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Paginated response ---

class PaginatedCalendarEvents(BaseModel):
    items: list[CalendarEventResponse]
    total: int
    page: int
    page_size: int


class PaginatedMutuelles(BaseModel):
    items: list[MutuelleResponse]
    total: int
    page: int
    page_size: int


class PaginatedDoctors(BaseModel):
    items: list[DoctorResponse]
    total: int
    page: int
    page_size: int


# --- Prescriptions / Payments / Products paginated ---

class PaginatedPrescriptions(BaseModel):
    items: list[CosiumPrescriptionResponse]
    total: int
    page: int
    page_size: int


class PaginatedPayments(BaseModel):
    items: list[CosiumPaymentResponse]
    total: int
    page: int
    page_size: int


class CosiumProductResponse(BaseModel):
    id: int
    cosium_id: str
    label: str = ""
    code: str = ""
    ean_code: str = ""
    price: float = 0
    family_type: str = ""

    model_config = ConfigDict(from_attributes=True)


class PaginatedProducts(BaseModel):
    items: list[CosiumProductResponse]
    total: int
    page: int
    page_size: int


# --- Sync result ---

class ReferenceSyncResult(BaseModel):
    entity: str
    created: int = 0
    updated: int = 0
    total_fetched: int = 0


class ReferenceSyncAllResult(BaseModel):
    results: list[ReferenceSyncResult]
    total_created: int = 0
    total_updated: int = 0
