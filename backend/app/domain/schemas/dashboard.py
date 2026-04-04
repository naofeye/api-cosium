from pydantic import BaseModel


class DashboardSummary(BaseModel):
    cases_count: int
    documents_count: int
    alerts_count: int
    total_due: float
    total_paid: float
    remaining: float
