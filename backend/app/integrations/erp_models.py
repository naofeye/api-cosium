"""Modeles generiques ERP — structures de donnees communes a tous les connecteurs."""

from datetime import date, datetime

from pydantic import BaseModel


class ERPCustomer(BaseModel):
    """Client tel que retourne par un ERP optique."""

    erp_id: str
    first_name: str
    last_name: str
    birth_date: date | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    social_security_number: str | None = None


class ERPInvoice(BaseModel):
    """Facture/devis tel que retourne par un ERP optique."""

    erp_id: str
    type: str = "INVOICE"
    number: str = ""
    date: datetime | None = None
    total_ttc: float = 0.0
    total_ht: float = 0.0
    total_tax: float = 0.0
    settled: bool = False
    customer_erp_id: str = ""
    customer_name: str = ""
    outstanding_balance: float = 0.0
    share_social_security: float = 0.0
    share_private_insurance: float = 0.0
    archived: bool = False
    site_id: int | None = None


class ERPProduct(BaseModel):
    """Produit du catalogue ERP."""

    erp_id: str
    code: str = ""
    ean: str = ""
    gtin: str = ""
    label: str = ""
    family: str = ""
    price: float = 0.0


class ERPStock(BaseModel):
    """Stock d'un produit par site."""

    product_erp_id: str
    site: str = ""
    quantity: int = 0


class ERPPaymentType(BaseModel):
    """Moyen de paiement accepte par l'ERP."""

    erp_id: str
    label: str
    code: str = ""
