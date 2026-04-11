from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    birth_date: date | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    social_security_number: str | None = None
    notes: str | None = None


class ClientUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=120)
    last_name: str | None = Field(None, min_length=1, max_length=120)
    birth_date: date | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    social_security_number: str | None = None
    notes: str | None = None


class ClientCompletenessScore(BaseModel):
    score: float = 0.0
    fields: dict[str, bool] = {}


class ClientResponse(BaseModel):
    id: int
    cosium_id: str | None = None
    customer_number: str | None = None
    first_name: str
    last_name: str
    birth_date: date | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    street_number: str | None = None
    street_name: str | None = None
    city: str | None = None
    postal_code: str | None = None
    social_security_number: str | None = None
    optician_name: str | None = None
    ophthalmologist_id: str | None = None
    mobile_phone_country: str | None = None
    site_id: int | None = None
    notes: str | None = None
    avatar_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completeness: ClientCompletenessScore | None = None

    model_config = ConfigDict(from_attributes=True)


class ClientSearch(BaseModel):
    query: str = ""
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    total: int
    page: int
    page_size: int
    total_pages: int = 0


class ClientImportError(BaseModel):
    line: int
    reason: str


class ClientImportResult(BaseModel):
    imported: int
    updated: int = 0
    skipped: int
    errors: list[ClientImportError]


class DuplicateGroup(BaseModel):
    name: str
    count: int
    clients: list[ClientResponse]


class ClientMergeRequest(BaseModel):
    keep_id: int = Field(..., description="ID du client a conserver")
    merge_id: int = Field(..., description="ID du client a fusionner (sera supprime)")


class ClientMergeResult(BaseModel):
    kept_client: ClientResponse
    cases_transferred: int = 0
    interactions_transferred: int = 0
    pec_transferred: int = 0
    marketing_transferred: int = 0
    cosium_data_transferred: int = 0
    fields_filled: list[str] = []
    merged_client_deleted: bool = True
