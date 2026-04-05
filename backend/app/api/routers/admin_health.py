"""Admin health check and metrics endpoints."""

import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.admin import HealthCheckResponse, MetricsResponse
from app.models import AuditLog, Case, Customer, Facture, Payment

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Verification de sante",
    description="Verifie l'etat de sante de tous les services (PostgreSQL, Redis, MinIO).",
)
def health_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    """Public health check for load balancer. No auth required."""
    checks = {}

    # PostgreSQL
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        checks["postgres"] = {"status": "ok", "response_ms": round((time.time() - start) * 1000, 1)}
    except Exception:
        checks["postgres"] = {"status": "error", "error": "unavailable"}

    # Redis
    try:
        import redis as redis_lib

        start = time.time()
        r = redis_lib.Redis.from_url("redis://redis:6379/0", socket_timeout=2)
        r.ping()
        checks["redis"] = {"status": "ok", "response_ms": round((time.time() - start) * 1000, 1)}
    except Exception:
        checks["redis"] = {"status": "error", "error": "unavailable"}

    # MinIO
    try:
        import httpx

        start = time.time()
        resp = httpx.get("http://minio:9000/minio/health/live", timeout=2)
        checks["minio"] = {
            "status": "ok" if resp.status_code == 200 else "degraded",
            "response_ms": round((time.time() - start) * 1000, 1),
        }
    except Exception:
        checks["minio"] = {"status": "error", "error": "unavailable"}

    all_ok = all(c["status"] == "ok" for c in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "services": checks}


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Metriques du tenant",
    description="Retourne les compteurs et metriques d'activite du tenant (admin).",
)
def metrics(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> MetricsResponse:
    """Admin-only metrics scoped to current tenant."""
    tid = tenant_ctx.tenant_id
    one_hour_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)

    total_clients = db.scalar(select(func.count()).select_from(Customer).where(Customer.tenant_id == tid)) or 0
    total_cases = db.scalar(select(func.count()).select_from(Case).where(Case.tenant_id == tid)) or 0
    total_factures = db.scalar(select(func.count()).select_from(Facture).where(Facture.tenant_id == tid)) or 0
    total_payments = db.scalar(select(func.count()).select_from(Payment).where(Payment.tenant_id == tid)) or 0

    recent_actions = (
        db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.tenant_id == tid, AuditLog.created_at >= one_hour_ago)
        )
        or 0
    )

    active_users = (
        db.scalar(
            select(func.count(func.distinct(AuditLog.user_id))).where(
                AuditLog.tenant_id == tid, AuditLog.created_at >= one_hour_ago
            )
        )
        or 0
    )

    return {
        "totals": {
            "clients": total_clients,
            "dossiers": total_cases,
            "factures": total_factures,
            "paiements": total_payments,
        },
        "activity": {
            "actions_last_hour": recent_actions,
            "active_users_last_hour": active_users,
        },
    }
