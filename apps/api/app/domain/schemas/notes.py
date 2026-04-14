"""Schemas Pydantic pour les notes CRM Cosium (lecture seule)."""
from pydantic import BaseModel


class CosiumNoteResponse(BaseModel):
    """Note CRM Cosium."""
    cosium_id: int | None = None
    message: str = ""
    creation_date: str | None = None
    modification_date: str | None = None
    customer_id: int | None = None
    customer_number: str | None = None
    author: str | None = None
    appearance_value: str | None = None
    appearance_label: str | None = None
    status_value: str | None = None
    status_label: str | None = None
