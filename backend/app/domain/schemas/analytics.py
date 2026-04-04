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


class DashboardFull(BaseModel):
    financial: FinancialKPIs
    aging: AgingBalance
    payers: PayerPerformance
    operational: OperationalKPIs
    commercial: CommercialKPIs
    marketing: MarketingKPIs
