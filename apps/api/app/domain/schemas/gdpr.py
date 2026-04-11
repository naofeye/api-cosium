"""Schemas for GDPR endpoints."""

from pydantic import BaseModel


class GDPRPersonalInfo(BaseModel):
    id: int
    prenom: str | None = None
    nom: str | None = None
    email: str | None = None
    telephone: str | None = None
    date_naissance: str | None = None
    adresse: str | None = None
    ville: str | None = None
    code_postal: str | None = None
    numero_secu: str | None = None


class GDPRCaseItem(BaseModel):
    id: int
    statut: str | None = None
    source: str | None = None


class GDPRDocumentItem(BaseModel):
    id: int
    type: str | None = None
    filename: str | None = None


class GDPRDevisItem(BaseModel):
    id: int
    numero: str | None = None
    montant_ttc: float = 0.0


class GDPRFactureItem(BaseModel):
    id: int
    numero: str | None = None
    montant_ttc: float = 0.0


class GDPRPaymentItem(BaseModel):
    id: int
    montant_paye: float = 0.0
    statut: str | None = None


class GDPRConsentItem(BaseModel):
    canal: str
    consenti: bool
    date: str | None = None


class GDPRInteractionItem(BaseModel):
    id: int
    type: str
    sujet: str


class ClientDataResponse(BaseModel):
    informations_personnelles: GDPRPersonalInfo
    dossiers: list[GDPRCaseItem] = []
    documents: list[GDPRDocumentItem] = []
    devis: list[GDPRDevisItem] = []
    factures: list[GDPRFactureItem] = []
    paiements: list[GDPRPaymentItem] = []
    consentements_marketing: list[GDPRConsentItem] = []
    interactions: list[GDPRInteractionItem] = []


class AnonymizeResponse(BaseModel):
    client_id: int
    status: str
