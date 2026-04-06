"""Admin health check, metrics, and Cosium cookie management endpoints."""

import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.admin import DataQualityResponse, HealthCheckResponse, MetricsResponse
from app.models import AuditLog, Case, Customer, Facture, Payment
from app.models.cosium_data import CosiumDocument, CosiumInvoice, CosiumPayment, CosiumPrescription
from app.services import onboarding_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _check_cosium_status() -> dict:
    """Quick Cosium connectivity check (cookie-based, no heavy call)."""
    try:
        from app.integrations.cosium.client import CosiumClient

        client = CosiumClient()
        client.authenticate()
        return {"status": "ok"}
    except Exception as exc:
        msg = str(exc)
        if "401" in msg:
            return {"status": "degraded", "error": "cookie expired"}
        return {"status": "error", "error": "unavailable"}


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Verification de sante",
    description="Verifie l'etat de sante de tous les services (PostgreSQL, Redis, MinIO, Cosium).",
)
def health_check(db: Session = Depends(get_db)) -> HealthCheckResponse:
    """Public health check for load balancer. No auth required."""
    from app.main import _APP_START_TIME, _APP_VERSION

    checks: dict[str, dict] = {}

    # PostgreSQL
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok", "response_ms": round((time.time() - start) * 1000, 1)}
    except Exception:
        checks["database"] = {"status": "error", "error": "unavailable"}

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

    # Cosium
    checks["cosium"] = _check_cosium_status()

    all_ok = all(c["status"] == "ok" for c in checks.values())
    uptime_seconds = int(time.time() - _APP_START_TIME)

    return {
        "status": "ok" if all_ok else "degraded",
        "version": _APP_VERSION,
        "components": checks,
        "uptime_seconds": uptime_seconds,
    }


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


def _entity_quality(db: Session, model: type, tenant_id: int) -> dict:
    """Compute link stats for a cosium data model."""
    total = db.scalar(
        select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
    ) or 0
    linked = db.scalar(
        select(func.count()).select_from(model).where(
            model.tenant_id == tenant_id,
            model.customer_id.isnot(None),
        )
    ) or 0
    orphan = total - linked
    link_rate = round((linked / total) * 100, 1) if total > 0 else 0.0
    return {"total": total, "linked": linked, "orphan": orphan, "link_rate": link_rate}


@router.get(
    "/data-quality",
    response_model=DataQualityResponse,
    summary="Qualite des donnees",
    description="Retourne le taux de liaison client pour chaque type de donnee Cosium.",
)
def data_quality(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> DataQualityResponse:
    """Data quality dashboard: link rates for invoices, payments, documents, prescriptions."""
    tid = tenant_ctx.tenant_id
    return DataQualityResponse(
        invoices=_entity_quality(db, CosiumInvoice, tid),
        payments=_entity_quality(db, CosiumPayment, tid),
        documents=_entity_quality(db, CosiumDocument, tid),
        prescriptions=_entity_quality(db, CosiumPrescription, tid),
    )


@router.get(
    "/sentry-test",
    summary="Test Sentry",
    description="Leve une exception de test pour verifier que Sentry capture bien les erreurs (admin uniquement).",
)
def test_sentry(
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> dict:
    """Admin-only: raise a test exception captured by Sentry."""
    raise ValueError("Sentry test exception from OptiFlow")


class CosiumConnectionTest(BaseModel):
    connected: bool
    error: str | None = None
    tenant: str = ""
    customers_total: int | None = None


@router.get(
    "/cosium-test",
    response_model=CosiumConnectionTest,
    summary="Tester la connexion Cosium",
    description="Verifie si les cookies Cosium sont valides en faisant un appel API test.",
)
def test_cosium_connection(
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> CosiumConnectionTest:
    """Test Cosium connection. Returns connected=False if cookie expired (401)."""
    try:
        from app.integrations.cosium.client import CosiumClient

        client = CosiumClient()
        client.authenticate()
        data = client.get("/customers", {"page_size": 1, "page_number": 0})
        total = data.get("page", {}).get("totalElements") or data.get("totalElements", 0)
        return CosiumConnectionTest(
            connected=True, tenant=client.tenant or "", customers_total=total
        )
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            return CosiumConnectionTest(
                connected=False,
                error="Cookie expire. Veuillez vous reconnecter a Cosium et copier le nouveau cookie access_token.",
            )
        return CosiumConnectionTest(connected=False, error="Erreur de connexion Cosium. Verifiez vos identifiants et la disponibilite du service.")


class CosiumCookiesPayload(BaseModel):
    access_token: str = Field(..., min_length=1, description="Cookie access_token depuis le navigateur Cosium")
    device_credential: str = Field(
        ..., min_length=1, description="Cookie device-credential depuis le navigateur Cosium"
    )


class CosiumCookiesResponse(BaseModel):
    status: str
    message: str


@router.post(
    "/cosium-cookies",
    response_model=CosiumCookiesResponse,
    summary="Mettre a jour les cookies Cosium",
    description="Enregistre les cookies access_token et device-credential du navigateur Cosium (chiffres en base).",
)
def update_cosium_cookies(
    payload: CosiumCookiesPayload,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> CosiumCookiesResponse:
    """Admin-only: store encrypted Cosium browser cookies for the tenant."""
    onboarding_service.update_cosium_cookies(
        db,
        tenant_id=tenant_ctx.tenant_id,
        access_token=payload.access_token,
        device_credential=payload.device_credential,
    )
    return CosiumCookiesResponse(status="ok", message="Cookies Cosium mis a jour avec succes")
