"""Admin health check, metrics, and Cosium cookie management endpoints."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.admin import DataQualityResponse, ExtractionStats, HealthCheckResponse, MetricsResponse
from app.models.cosium_data import CosiumDocument, CosiumInvoice, CosiumPayment, CosiumPrescription
from app.models.document_extraction import DocumentExtraction
from app.repositories import onboarding_repo
from app.services import admin_metrics_service, onboarding_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _check_cosium_status(db: Session, tenant_id: int | None = None) -> dict:
    """Quick Cosium connectivity check using tenant-scoped credentials.

    If tenant_id is provided, uses tenant-stored cookies/credentials.
    Otherwise falls back to global settings.
    """
    try:
        from app.core.encryption import decrypt
        from app.integrations.cosium.client import CosiumClient

        client = CosiumClient()
        client.base_url = settings.cosium_base_url

        if tenant_id is not None:
            tenant = onboarding_repo.get_tenant_by_id(db, tenant_id)
            if not tenant:
                return {"status": "error", "error": "tenant introuvable"}

            client.tenant = tenant.cosium_tenant or settings.cosium_tenant or ""

            # Try tenant-stored cookies first
            tenant_at = getattr(tenant, "cosium_cookie_access_token_enc", None)
            tenant_dc = getattr(tenant, "cosium_cookie_device_credential_enc", None)
            if tenant_at and tenant_dc:
                at_plain = decrypt(tenant_at)
                dc_plain = decrypt(tenant_dc)
                client._authenticate_cookie(access_token=at_plain, device_credential=dc_plain)
                return {"status": "ok"}

        # Fallback to global settings
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
        r = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=2)
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
    checks["cosium"] = _check_cosium_status(db)

    all_ok = all(c["status"] == "ok" for c in checks.values())
    uptime_seconds = int(time.time() - _APP_START_TIME)

    return {
        "status": "healthy" if all_ok else "degraded",
        "version": _APP_VERSION,
        "services": checks,
        "components": checks,  # backward compat
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
    from app.core.redis_cache import cache_get, cache_set

    tid = tenant_ctx.tenant_id
    cache_key = f"admin:metrics:{tid}"
    cached = cache_get(cache_key)
    if cached:
        return MetricsResponse(**cached)

    result = admin_metrics_service.get_tenant_metrics(db, tid)
    cache_set(cache_key, result, ttl=300)
    return result


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
    from app.core.redis_cache import cache_get, cache_set

    tid = tenant_ctx.tenant_id
    cache_key = f"admin:data_quality:{tid}"
    cached = cache_get(cache_key)
    if cached:
        return DataQualityResponse(**cached)

    # Extraction stats from DocumentExtraction table
    total_documents = db.scalar(
        select(func.count()).select_from(CosiumDocument).where(CosiumDocument.tenant_id == tid)
    ) or 0
    total_extracted = db.scalar(
        select(func.count()).select_from(DocumentExtraction).where(DocumentExtraction.tenant_id == tid)
    ) or 0
    extraction_rate = round((total_extracted / total_documents) * 100, 1) if total_documents > 0 else 0.0

    # Count by document_type
    type_counts_raw = db.execute(
        select(DocumentExtraction.document_type, func.count())
        .where(
            DocumentExtraction.tenant_id == tid,
            DocumentExtraction.document_type.isnot(None),
        )
        .group_by(DocumentExtraction.document_type)
    ).all()
    by_type = {row[0]: row[1] for row in type_counts_raw}

    result = DataQualityResponse(
        invoices=admin_metrics_service.get_entity_quality(db, CosiumInvoice, tid),
        payments=admin_metrics_service.get_entity_quality(db, CosiumPayment, tid),
        documents=admin_metrics_service.get_entity_quality(db, CosiumDocument, tid),
        prescriptions=admin_metrics_service.get_entity_quality(db, CosiumPrescription, tid),
        extractions=ExtractionStats(
            total_documents=total_documents,
            total_extracted=total_extracted,
            extraction_rate=extraction_rate,
            by_type=by_type,
        ),
    )
    cache_set(cache_key, result.model_dump(), ttl=600)
    return result


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
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> CosiumConnectionTest:
    """Test Cosium connection using tenant-scoped credentials."""
    try:
        from app.core.encryption import decrypt
        from app.integrations.cosium.client import CosiumClient

        tenant = onboarding_repo.get_tenant_by_id(db, tenant_ctx.tenant_id)
        client = CosiumClient()
        client.base_url = settings.cosium_base_url

        if tenant:
            client.tenant = tenant.cosium_tenant or settings.cosium_tenant or ""
            tenant_at = getattr(tenant, "cosium_cookie_access_token_enc", None)
            tenant_dc = getattr(tenant, "cosium_cookie_device_credential_enc", None)
            if tenant_at and tenant_dc:
                at_plain = decrypt(tenant_at)
                dc_plain = decrypt(tenant_dc)
                client._authenticate_cookie(access_token=at_plain, device_credential=dc_plain)
            else:
                client.authenticate()
        else:
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
