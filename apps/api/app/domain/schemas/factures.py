from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class FactureCreate(BaseModel):
    devis_id: int


class FactureLigneResponse(BaseModel):
    id: int
    designation: str
    quantite: int
    prix_unitaire_ht: float
    taux_tva: float
    montant_ht: float
    montant_ttc: float

    model_config = ConfigDict(from_attributes=True)


class FactureResponse(BaseModel):
    id: int
    case_id: int
    devis_id: int
    numero: str
    date_emission: datetime
    montant_ht: float
    tva: float
    montant_ttc: float
    status: str
    created_at: datetime
    customer_name: str | None = None
    customer_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FactureDetail(FactureResponse):
    lignes: list[FactureLigneResponse] = []
    devis_numero: str | None = None


class FactureSendEmailRequest(BaseModel):
    to: EmailStr
    subject: str | None = Field(None, max_length=200)
    message: str | None = Field(None, max_length=2000)


class FactureSendEmailResponse(BaseModel):
    sent: bool
    to: EmailStr
    facture_id: int
