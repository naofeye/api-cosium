"""Schemas for admin health check and metrics endpoints."""

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: str
    response_ms: float | None = None
    error: str | None = None


class HealthCheckResponse(BaseModel):
    status: str
    version: str | None = None
    components: dict[str, ServiceStatus] | None = None
    uptime_seconds: int | None = None
    # Legacy alias kept for backwards compatibility
    services: dict[str, ServiceStatus] | None = None


class MetricsTotals(BaseModel):
    clients: int
    dossiers: int
    factures: int
    paiements: int


class MetricsActivity(BaseModel):
    actions_last_hour: int
    active_users_last_hour: int


class MetricsResponse(BaseModel):
    totals: MetricsTotals
    activity: MetricsActivity


class DataQualityEntity(BaseModel):
    total: int
    linked: int
    orphan: int
    link_rate: float


class ExtractionStats(BaseModel):
    total_documents: int = 0
    total_extracted: int = 0
    extraction_rate: float = 0.0
    by_type: dict[str, int] = {}


class DataQualityResponse(BaseModel):
    invoices: DataQualityEntity
    payments: DataQualityEntity
    documents: DataQualityEntity
    prescriptions: DataQualityEntity
    extractions: ExtractionStats | None = None
