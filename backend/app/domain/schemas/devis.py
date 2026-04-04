from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DevisLineCreate(BaseModel):
    designation: str = Field(..., min_length=1, max_length=255)
    quantite: int = Field(1, ge=1)
    prix_unitaire_ht: float = Field(..., ge=0)
    taux_tva: float = Field(20.0, ge=0, le=100)


class DevisLineResponse(BaseModel):
    id: int
    designation: str
    quantite: int
    prix_unitaire_ht: float
    taux_tva: float
    montant_ht: float
    montant_ttc: float

    model_config = ConfigDict(from_attributes=True)


class DevisCreate(BaseModel):
    case_id: int
    part_secu: float = Field(0, ge=0)
    part_mutuelle: float = Field(0, ge=0)
    lignes: list[DevisLineCreate] = Field(..., min_length=1)


class DevisUpdate(BaseModel):
    part_secu: float | None = Field(None, ge=0)
    part_mutuelle: float | None = Field(None, ge=0)
    lignes: list[DevisLineCreate] | None = None


class DevisStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(brouillon|envoye|signe|facture|annule)$")


class DevisResponse(BaseModel):
    id: int
    case_id: int
    numero: str
    status: str
    montant_ht: float
    tva: float
    montant_ttc: float
    part_secu: float
    part_mutuelle: float
    reste_a_charge: float
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DevisDetail(DevisResponse):
    lignes: list[DevisLineResponse] = []
    customer_name: str | None = None
