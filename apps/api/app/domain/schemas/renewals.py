from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PrescriptionSummary(BaseModel):
    """Resume de la derniere ordonnance pour affichage renouvellement."""

    prescription_date: datetime | None = None
    age_months: int = 0
    od_summary: str = ""
    og_summary: str = ""
    prescriber_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RenewalOpportunity(BaseModel):
    """Opportunite de renouvellement detectee pour un client."""

    customer_id: int
    customer_name: str
    phone: str | None = None
    email: str | None = None
    last_purchase_date: datetime | None = None
    months_since_purchase: int
    equipment_type: str | None = None
    last_invoice_amount: float = 0.0
    has_active_mutuelle: bool = False
    score: float = Field(..., ge=0, le=100, description="Score d'opportunite 0-100")
    suggested_action: str = "email"
    reason: str = ""
    prescription: PrescriptionSummary | None = None

    model_config = ConfigDict(from_attributes=True)


class RenewalConfig(BaseModel):
    """Configuration des criteres de detection."""

    age_minimum_months: int = Field(24, ge=6, le=60)
    equipment_types: list[str] = Field(
        default_factory=lambda: ["monture", "verre", "lentille", "solaire"],
    )
    min_invoice_amount: float = Field(0.0, ge=0)
    mutuelle_bonus: float = Field(15.0, ge=0, le=50)


class RenewalCampaignCreate(BaseModel):
    """Demande de creation d'une campagne de renouvellement."""

    name: str = Field(..., min_length=1, max_length=255)
    channel: str = Field("email", pattern="^(email|sms)$")
    customer_ids: list[int] = Field(..., min_length=1)
    use_ai_message: bool = True
    custom_template: str | None = None


class RenewalCampaignResponse(BaseModel):
    id: int
    name: str
    channel: str
    customer_count: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RenewalDashboardResponse(BaseModel):
    """KPIs du tableau de bord renouvellement."""

    total_opportunities: int = 0
    high_score_count: int = 0
    avg_months_since_purchase: float = 0.0
    estimated_revenue: float = 0.0
    campaigns_sent: int = 0
    campaigns_this_month: int = 0
    top_opportunities: list[RenewalOpportunity] = Field(default_factory=list)


class RenewalAnalysisResult(BaseModel):
    analysis: str


class RenewalMessageResult(BaseModel):
    message: str
    channel: str
    customer_id: int
