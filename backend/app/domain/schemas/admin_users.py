"""Schemas for admin user management endpoints."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_ROLES = ("admin", "manager", "operator", "viewer")


class AdminUserCreate(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
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
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not re.search(r"\d", v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v


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
