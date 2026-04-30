"""Schemas for admin user management endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.schemas.auth import PasswordMixin

VALID_ROLES = ("admin", "manager", "operator", "viewer")


class AdminUserCreate(BaseModel, PasswordMixin):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=10, max_length=128)
    role: str = Field(default="operator", max_length=30)
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Role invalide. Valeurs autorisees : {', '.join(VALID_ROLES)}")
        return v

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        # Reutilise le validateur central (10+ chars, majuscule, minuscule,
        # chiffre, special) pour aligner la politique avec reset/signup
        # (auth.PasswordMixin). Avant : 8 chars + maj + chiffre seulement,
        # plus faible que les autres flux.
        return cls.validate_password_strength(v)


class AdminUserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"Role invalide. Valeurs autorisees : {', '.join(VALID_ROLES)}")
        return v


class AdminUserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    users: list[AdminUserResponse]
    total: int
