from pydantic import BaseModel


class MonthlyCa(BaseModel):
    mois: str
    ca: float = 0


class FinancialKPIs(BaseModel):
    ca_total: float = 0
    montant_facture: float = 0
    montant_encaisse: float = 0
    reste_a_encaisser: float = 0
    taux_recouvrement: float = 0


class AgingBucket(BaseModel):
    tranche: str
    client: float = 0
    mutuelle: float = 0
    secu: float = 0
    total: float = 0


class AgingBalance(BaseModel):
    buckets: list[AgingBucket]
    total: float = 0


class PayerPerf(BaseModel):
    name: str
    type: str
    avg_payment_days: float = 0
    acceptance_rate: float = 0
    rejection_rate: float = 0
    total_requested: float = 0
    total_accepted: float = 0


class PayerPerformance(BaseModel):
    payers: list[PayerPerf]


class OperationalKPIs(BaseModel):
    dossiers_en_cours: int = 0
    dossiers_complets: int = 0
    taux_completude: float = 0
    pieces_manquantes: int = 0
    delai_moyen_jours: float = 0


class CommercialKPIs(BaseModel):
    devis_en_cours: int = 0
    devis_signes: int = 0
    taux_conversion: float = 0
    panier_moyen: float = 0
    ca_par_mois: list[MonthlyCa] = []


class MarketingKPIs(BaseModel):
    campagnes_total: int = 0
    campagnes_envoyees: int = 0
    messages_envoyes: int = 0
    taux_ouverture: float = 0


class CosiumKPIs(BaseModel):
    total_facture_cosium: float = 0
    total_outstanding: float = 0
    total_paid: float = 0
    invoice_count: int = 0
    quote_count: int = 0
    credit_note_count: int = 0
    total_devis_cosium: float = 0
    total_avoirs_cosium: float = 0


class CosiumCounts(BaseModel):
    total_clients: int = 0
    total_rdv: int = 0
    total_prescriptions: int = 0
    total_payments: int = 0


class CosiumMonthlyCa(BaseModel):
    mois: str
    ca: float = 0


class KPIComparison(BaseModel):
    ca_total_delta: float | None = None
    montant_encaisse_delta: float | None = None
    reste_a_encaisser_delta: float | None = None
    taux_recouvrement_delta: float | None = None
    clients_delta: float | None = None
    factures_delta: float | None = None


class DashboardFull(BaseModel):
    financial: FinancialKPIs
    aging: AgingBalance
    payers: PayerPerformance
    operational: OperationalKPIs
    commercial: CommercialKPIs
    marketing: MarketingKPIs
    cosium: CosiumKPIs | None = None
    cosium_counts: CosiumCounts | None = None
    cosium_ca_par_mois: list[CosiumMonthlyCa] = []
    comparison: KPIComparison | None = None
