"""Schemas Pydantic pour les dossiers SAV Cosium (lecture seule)."""
from pydantic import BaseModel


class AfterSalesServiceResponse(BaseModel):
    """Dossier SAV (apres-vente) Cosium."""
    cosium_id: int | None = None
    status: str | None = None
    resolution_status: str | None = None
    creation_date: str | None = None
    processing_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    type: str | None = None
    customer_number: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    item_serial_number: str | None = None
    product_code: str | None = None
    product_ean: str | None = None
    product_model: str | None = None
    product_color: str | None = None
    repairer_name: str | None = None
    site_name: str | None = None
