from datetime import datetime

from pydantic import BaseModel

from app.domain.schemas.interactions import InteractionResponse


class FinancialSummary(BaseModel):
    total_facture: float = 0
    total_paye: float = 0
    reste_du: float = 0
    taux_recouvrement: float = 0


class DossierSummary(BaseModel):
    id: int
    statut: str
    source: str | None = None
    created_at: str | None = None


class DocumentSummary(BaseModel):
    id: int
    type: str
    filename: str
    uploaded_at: str | None = None


class DevisSummary(BaseModel):
    id: int
    numero: str
    statut: str
    montant_ttc: float = 0
    reste_a_charge: float = 0


class FactureSummary(BaseModel):
    id: int
    numero: str
    statut: str
    montant_ttc: float = 0
    date_emission: str | None = None


class PaiementSummary(BaseModel):
    id: int
    payeur: str
    mode: str | None = None
    montant_du: float = 0
    montant_paye: float = 0
    statut: str


class PecSummary(BaseModel):
    id: int
    statut: str
    montant_demande: float = 0
    montant_accorde: float | None = None


class ConsentementSummary(BaseModel):
    canal: str
    consenti: bool


class Client360Response(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    birth_date: str | None = None
    address: str | None = None
    city: str | None = None
    postal_code: str | None = None
    social_security_number: str | None = None
    avatar_url: str | None = None
    created_at: datetime | None = None
    dossiers: list[DossierSummary] = []
    devis: list[DevisSummary] = []
    factures: list[FactureSummary] = []
    paiements: list[PaiementSummary] = []
    documents: list[DocumentSummary] = []
    pec: list[PecSummary] = []
    consentements: list[ConsentementSummary] = []
    interactions: list[InteractionResponse] = []
    resume_financier: FinancialSummary = FinancialSummary()
