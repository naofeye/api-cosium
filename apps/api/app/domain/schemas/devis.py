from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class DevisLineCreate(BaseModel):
    designation: str = Field(..., min_length=1, max_length=255)
    quantite: int = Field(1, ge=1)
    prix_unitaire_ht: float = Field(..., ge=0)
    taux_tva: float = Field(20.0, ge=0, le=30)


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
    reste_a_charge: float | None = Field(None, ge=0)
    lignes: list[DevisLineCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_financial_consistency(self) -> "DevisCreate":
        # If all three financial parts are provided, check they sum to montant_ttc
        if self.reste_a_charge is not None:
            montant_ttc = sum(
                l.prix_unitaire_ht * l.quantite * (1 + l.taux_tva / 100)
                for l in self.lignes
            )
            parts_sum = self.part_secu + self.part_mutuelle + self.reste_a_charge
            if abs(parts_sum - montant_ttc) > 0.01:
                raise ValueError(
                    f"La somme part_secu + part_mutuelle + reste_a_charge ({parts_sum:.2f}) "
                    f"doit être égale au montant TTC ({montant_ttc:.2f})"
                )
        return self


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
    valid_until: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DevisDetail(DevisResponse):
    lignes: list[DevisLineResponse] = []
    customer_name: str | None = None
    customer_email: str | None = None


class DevisSendEmailRequest(BaseModel):
    to: EmailStr
    subject: str | None = Field(None, max_length=200)
    message: str | None = Field(None, max_length=2000)


class DevisSendEmailResponse(BaseModel):
    sent: bool
    to: EmailStr
    devis_id: int
