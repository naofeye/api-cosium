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


class ClientResponse(BaseModel):
    id: int
    cosium_id: str | None = None
    first_name: str
    last_name: str
    birth_date: date | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    social_security_number: str | None = None
    notes: str | None = None
    avatar_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None

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


class ClientImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


class DuplicateGroup(BaseModel):
    name: str
    count: int
    clients: list[ClientResponse]
