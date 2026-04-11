import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class PasswordMixin:
    """Validation de mot de passe : 10+ chars, 1 majuscule, 1 minuscule, 1 chiffre, 1 special."""

    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Le mot de passe doit contenir au moins 10 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not re.search(r"[a-z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not re.search(r"\d", v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("Le mot de passe doit contenir au moins un caractere special")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255)


class ResetPasswordRequest(BaseModel, PasswordMixin):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return cls.validate_password_strength(v)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel, PasswordMixin):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=10, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return cls.validate_password_strength(v)


class TenantInfo(BaseModel):
    id: int
    name: str
    slug: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    tenant_id: int | None = None
    tenant_name: str | None = None
    available_tenants: list[TenantInfo] = []


class LoginResponse(BaseModel):
    """Response body for login/switch-tenant — tokens are in httpOnly cookies only."""

    role: str
    tenant_id: int | None = None
    tenant_name: str | None = None
    available_tenants: list[TenantInfo] = []


class SwitchTenantRequest(BaseModel):
    tenant_id: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class UserMeResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool


class SyncResult(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    total: int = 0
    fetched: int = 0
    note: str = ""
