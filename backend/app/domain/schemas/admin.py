"""Schemas for admin health check and metrics endpoints."""

from pydantic import BaseModel


class ServiceStatus(BaseModel):
    status: str
    response_ms: float | None = None
    error: str | None = None


class HealthCheckResponse(BaseModel):
    status: str
    services: dict[str, ServiceStatus]


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


class DataQualityResponse(BaseModel):
    invoices: DataQualityEntity
    payments: DataQualityEntity
    documents: DataQualityEntity
    prescriptions: DataQualityEntity
