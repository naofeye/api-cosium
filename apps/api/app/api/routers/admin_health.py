"""Admin health check and metrics endpoints."""

import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_tenant_role
from app.core.logging import get_logger
from app.core.tenant_context import TenantContext

_health_logger = get_logger("admin_health")
from app.db.session import get_db
from app.domain.schemas.admin import DataQualityResponse, ExtractionStats, HealthCheckResponse, MetricsResponse
from app.models.cosium_data import CosiumDocument, CosiumInvoice, CosiumPayment, CosiumPrescription
from app.models.document_extraction import DocumentExtraction
from app.services import admin_metrics_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Verification de sante (admin)",
    description=(
        "Verifie l'etat detaille des services (PostgreSQL, Redis, MinIO, Celery beat). "
        "Endpoint sous auth admin pour eviter le fingerprinting. "
        "Utiliser /health (racine) pour le liveness check public du load balancer."
    ),
)
def health_check(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> HealthCheckResponse:
    """Detailed health check — admin only. /health (public) reste pour load balancer."""
    from app.main import _APP_START_TIME, _APP_VERSION

    checks: dict[str, dict] = {}

    # PostgreSQL
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok", "response_ms": round((time.time() - start) * 1000, 1)}
    except Exception as exc:
        _health_logger.warning("health_db_check_failed", error=str(exc))
        checks["database"] = {"status": "error", "error": "unavailable"}

    # Redis
    try:
        import redis as redis_lib

        start = time.time()
        r = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=2)
        r.ping()
        checks["redis"] = {"status": "ok", "response_ms": round((time.time() - start) * 1000, 1)}
    except Exception as exc:
        _health_logger.warning("health_redis_check_failed", error=str(exc))
        checks["redis"] = {"status": "error", "error": "unavailable"}

    # Celery beat heartbeat : alerte si scheduler mort > 5 min
    try:
        import redis as redis_lib

        r = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=2)
        raw = r.get("celery:beat:heartbeat")
        if raw is None:
            checks["celery_beat"] = {"status": "error", "error": "no_heartbeat"}
        else:
            age_s = int(time.time() - int(raw))
            checks["celery_beat"] = {
                "status": "ok" if age_s < 300 else "error",
                "last_beat_age_s": age_s,
            }
    except Exception as exc:
        _health_logger.warning("health_celery_beat_check_failed", error=str(exc))
        checks["celery_beat"] = {"status": "error", "error": "unavailable"}

    # MinIO
    try:
        import httpx

        start = time.time()
        resp = httpx.get("http://minio:9000/minio/health/live", timeout=2)
        checks["minio"] = {
            "status": "ok" if resp.status_code == 200 else "degraded",
            "response_ms": round((time.time() - start) * 1000, 1),
        }
    except Exception as exc:
        _health_logger.warning("health_minio_check_failed", error=str(exc))
        checks["minio"] = {"status": "error", "error": "unavailable"}

    # Cosium: not checked here because health is public (no tenant context).
    # Use tenant-scoped /api/v1/admin/cosium-test instead.

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



class HealthDetailResponse(BaseModel):
    """Snapshot riche : services + queues + versions."""
    status: str
    version: str
    uptime_seconds: int
    services: dict
    db_pool: dict
    celery: dict
    runtime: dict


@router.get(
    "/health-detail",
    response_model=HealthDetailResponse,
    summary="Health check enrichi (admin)",
    description=(
        "Etend /health avec pool DB, queues Celery, versions runtime. "
        "Pour le dashboard admin avec auto-refresh."
    ),
)
def health_detail(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> HealthDetailResponse:
    import platform
    import sys

    from app.main import _APP_START_TIME, _APP_VERSION

    base = health_check(db, tenant_ctx)

    # Pool DB stats (SQLAlchemy QueuePool)
    pool_info: dict = {}
    try:
        from app.db.session import engine

        pool = engine.pool
        pool_info = {
            "size": pool.size() if hasattr(pool, "size") else None,
            "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else None,
            "checked_out": pool.checkedout() if hasattr(pool, "checkedout") else None,
            "overflow": pool.overflow() if hasattr(pool, "overflow") else None,
        }
    except Exception as exc:
        _health_logger.warning("pool_info_failed", error=str(exc))
        pool_info = {"error": "unavailable"}

    # Celery queues (Redis brpop) - lecture longueur file
    celery_info: dict = {}
    try:
        import redis as redis_lib
        r = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=2)
        queues = ["default", "email", "sync", "extraction", "batch", "reminder"]
        celery_info["queues"] = {q: int(r.llen(q) or 0) for q in queues}
    except Exception as exc:
        _health_logger.warning("celery_queues_failed", error=str(exc))
        celery_info = {"error": "unavailable"}

    # Runtime versions
    try:
        import fastapi as _fastapi
        fastapi_version = _fastapi.__version__
    except Exception:
        fastapi_version = "unknown"
    try:
        pg_version = db.scalar(text("SHOW server_version")) or "unknown"
    except Exception:
        pg_version = "unknown"

    runtime = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "fastapi": fastapi_version,
        "postgres": pg_version,
    }

    base_dict = base if isinstance(base, dict) else base.model_dump()
    return HealthDetailResponse(
        status=base_dict.get("status", "unknown"),
        version=base_dict.get("version", _APP_VERSION),
        uptime_seconds=base_dict.get("uptime_seconds", int(time.time() - _APP_START_TIME)),
        services=base_dict.get("services", {}),
        db_pool=pool_info,
        celery=celery_info,
        runtime=runtime,
    )

