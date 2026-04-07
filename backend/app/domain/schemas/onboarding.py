import re

from pydantic import BaseModel, Field, field_validator


class SignupRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    owner_email: str = Field(..., min_length=5, max_length=255)
    owner_password: str = Field(..., min_length=10, max_length=128)
    owner_first_name: str = Field(..., min_length=1, max_length=100)
    owner_last_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(None, max_length=50)

    @field_validator("owner_password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not re.search(r"[a-z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not re.search(r"\d", v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        if not re.search(r"[^A-Za-z0-9]", v):
            raise ValueError("Le mot de passe doit contenir au moins un caractere special")
        return v


class ConnectCosiumRequest(BaseModel):
    cosium_tenant: str = Field(..., min_length=1, max_length=100)
    cosium_login: str = Field(..., min_length=1, max_length=255)
    cosium_password: str = Field(..., min_length=1, max_length=255)


class OnboardingStep(BaseModel):
    key: str
    label: str
    completed: bool


class OnboardingStatusResponse(BaseModel):
    steps: list[OnboardingStep]
    current_step: str
    cosium_connected: bool
    first_sync_done: bool
    trial_days_remaining: int | None = None


class ConnectCosiumResult(BaseModel):
    status: str


class FirstSyncResult(BaseModel):
    status: str
    details: dict[str, str | int] = {}
