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


class CosiumInvoiceSummary(BaseModel):
    cosium_id: int
    invoice_number: str
    invoice_date: str | None = None
    type: str = "INVOICE"
    total_ti: float = 0
    outstanding_balance: float = 0
    share_social_security: float = 0
    share_private_insurance: float = 0
    settled: bool = False


class CosiumPrescriptionSummary(BaseModel):
    id: int
    cosium_id: int
    prescription_date: str | None = None
    prescriber_name: str | None = None
    sphere_right: float | None = None
    cylinder_right: float | None = None
    axis_right: float | None = None
    addition_right: float | None = None
    sphere_left: float | None = None
    cylinder_left: float | None = None
    axis_left: float | None = None
    addition_left: float | None = None
    spectacles_json: str | None = None


class CosiumPaymentSummary(BaseModel):
    id: int
    cosium_id: int
    amount: float = 0
    type: str = ""
    due_date: str | None = None
    issuer_name: str = ""
    bank: str = ""
    site_name: str = ""
    payment_number: str = ""
    invoice_cosium_id: int | None = None


class CosiumCalendarSummary(BaseModel):
    id: int
    cosium_id: int
    start_date: str | None = None
    end_date: str | None = None
    subject: str = ""
    category_name: str = ""
    category_color: str = ""
    status: str = ""
    canceled: bool = False
    missed: bool = False
    observation: str | None = None
    site_name: str | None = None


class EquipmentItem(BaseModel):
    prescription_id: int
    prescription_date: str | None = None
    label: str = ""
    brand: str = ""
    type: str = ""


class CorrectionActuelle(BaseModel):
    """Derniere correction optique connue (OD/OG)."""

    prescription_date: str | None = None
    prescriber_name: str | None = None
    sphere_right: float | None = None
    cylinder_right: float | None = None
    axis_right: float | None = None
    addition_right: float | None = None
    sphere_left: float | None = None
    cylinder_left: float | None = None
    axis_left: float | None = None
    addition_left: float | None = None


class CosiumDataBundle(BaseModel):
    """All Cosium data for a client in one response."""

    prescriptions: list[CosiumPrescriptionSummary] = []
    cosium_payments: list[CosiumPaymentSummary] = []
    calendar_events: list[CosiumCalendarSummary] = []
    equipments: list[EquipmentItem] = []
    correction_actuelle: CorrectionActuelle | None = None
    total_ca_cosium: float = 0
    last_visit_date: str | None = None
    customer_tags: list[str] = []


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
    cosium_id: str | None = None
    created_at: datetime | None = None
    dossiers: list[DossierSummary] = []
    devis: list[DevisSummary] = []
    factures: list[FactureSummary] = []
    paiements: list[PaiementSummary] = []
    documents: list[DocumentSummary] = []
    pec: list[PecSummary] = []
    consentements: list[ConsentementSummary] = []
    interactions: list[InteractionResponse] = []
    cosium_invoices: list[CosiumInvoiceSummary] = []
    cosium_data: CosiumDataBundle = CosiumDataBundle()
    resume_financier: FinancialSummary = FinancialSummary()
