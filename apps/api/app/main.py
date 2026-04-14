import time as _time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware as _BaseGZipMiddleware

from app import models  # noqa: F401, E402
from app.api.routers import (
    action_items,
    admin_health,
    admin_users,
    ai,
    ai_usage,
    analytics,
    audit,
    auth,
    banking,
    batch_operations,
    billing,
    cases,
    client_360,
    client_mutuelles,
    clients,
    consents,
    cosium_catalog,
    cosium_commercial,
    cosium_documents,
    cosium_fidelity,
    cosium_invoices,
    cosium_notes,
    cosium_reference,
    cosium_sav,
    cosium_spectacles,
    dashboard,
    devis,
    documents,
    exports,
    extractions,
    factures,
    gdpr,
    marketing,
    metrics,
    notifications,
    ocam_operators,
    onboarding,
    payments,
    pec,
    pec_preparation,
    reconciliation,
    reminders,
    renewals,
    search,
    sse,
    sync,
)
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    BusinessError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.core.rate_limiter import RateLimiterMiddleware
from app.core.request_id import RequestIdMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.session import SessionLocal
from app.seed import seed_data

_APP_VERSION = "1.0.0"
_APP_START_TIME = _time.time()

logger = get_logger("main")

# Sentry (optional)

if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment=settings.app_env,
    )

_is_dev = settings.app_env in ("local", "development", "test")
app = FastAPI(
    title="OptiFlow AI API",
    description="API de gestion pour opticiens connectee a Cosium — CRM, devis, facturation, PEC, marketing et IA.",
    version="1.2.0",
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
    openapi_tags=[
        {"name": "auth", "description": "Authentification et gestion de session"},
        {"name": "clients", "description": "Gestion des clients"},
        {"name": "client-360", "description": "Vue 360 client consolidee"},
        {"name": "client-mutuelles", "description": "Associations clients-mutuelles"},
        {"name": "cases", "description": "Gestion des dossiers"},
        {"name": "devis", "description": "Devis et offres commerciales"},
        {"name": "factures", "description": "Facturation"},
        {"name": "payments", "description": "Paiements et encaissements"},
        {"name": "banking", "description": "Rapprochement bancaire et import releves"},
        {"name": "pec", "description": "Prise en charge et tiers payant"},
        {"name": "pec-preparation", "description": "Assistance preparation PEC"},
        {"name": "ocam-operators", "description": "Operateurs OCAM (mutuelles/complementaires)"},
        {"name": "documents", "description": "Gestion electronique des documents (GED)"},
        {"name": "extractions", "description": "Extraction OCR et analyse de documents"},
        {"name": "cosium-invoices", "description": "Factures synchronisees depuis Cosium (lecture seule)"},
        {"name": "cosium-documents", "description": "Documents synchronises depuis Cosium (lecture seule)"},
        {"name": "cosium-reference", "description": "Donnees de reference Cosium (produits, moyens de paiement)"},
        {"name": "sync", "description": "Synchronisation ERP Cosium"},
        {"name": "notifications", "description": "Notifications utilisateur"},
        {"name": "action-items", "description": "Actions a traiter (file d'attente)"},
        {"name": "reconciliation", "description": "Rapprochement paiements-factures et lettrage"},
        {"name": "reminders", "description": "Relances et rappels clients"},
        {"name": "renewals", "description": "Renouvellements d'equipements"},
        {"name": "marketing", "description": "Campagnes marketing et segmentation"},
        {"name": "consents", "description": "Consentements marketing (RGPD)"},
        {"name": "analytics", "description": "Tableau de bord et KPIs"},
        {"name": "dashboard", "description": "Donnees du tableau de bord principal"},
        {"name": "search", "description": "Recherche globale multi-entites"},
        {"name": "exports", "description": "Exports de donnees (FEC, CSV)"},
        {"name": "audit", "description": "Logs d'audit et tracabilite"},
        {"name": "gdpr", "description": "Conformite RGPD (anonymisation, export donnees)"},
        {"name": "ai", "description": "Assistants IA et copilote"},
        {"name": "ai-usage", "description": "Suivi de consommation IA"},
        {"name": "billing", "description": "Facturation et abonnement OptiFlow"},
        {"name": "onboarding", "description": "Inscription et configuration initiale"},
        {"name": "admin", "description": "Administration, sante systeme et gestion utilisateurs"},
        {"name": "batch", "description": "Operations batch PEC (Groupes marketing)"},
        {"name": "sse", "description": "Evenements temps reel (Server-Sent Events)"},
    ],
)

# --- Selective GZip that skips SSE / file-download streams ---

_GZIP_SKIP_SEGMENTS = ("/sse", "/download", "/export")


class SelectiveGZipMiddleware(_BaseGZipMiddleware):
    """GZip middleware that bypasses streaming responses (SSE, PDF downloads)."""

    async def __call__(self, scope, receive, send):  # type: ignore[override]
        if scope["type"] == "http":
            path: str = scope.get("path", "")
            if any(seg in path for seg in _GZIP_SKIP_SEGMENTS):
                await self.app(scope, receive, send)
                return
        await super().__call__(scope, receive, send)


# Middleware stack — last added = outermost in Starlette.
# Desired order (outer → inner): CORS > SecurityHeaders > RequestId > RateLimiter > GZip
# So we add them innermost-first:

app.add_middleware(SelectiveGZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Idempotency-Key"],
)


def _inject_request_id(request: Request, body: dict) -> dict:
    """Add request_id from headers into the error response body."""
    rid = request.headers.get("X-Request-ID", "")
    if "error" in body and isinstance(body["error"], dict):
        body["error"]["request_id"] = rid
    return body


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    body = _inject_request_id(request, exc.to_dict())
    return JSONResponse(status_code=404, content=body)


@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    body = _inject_request_id(request, exc.to_dict())
    return JSONResponse(status_code=401, content=body)


@app.exception_handler(ForbiddenError)
async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    body = _inject_request_id(request, exc.to_dict())
    return JSONResponse(status_code=403, content=body)


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    body = _inject_request_id(request, exc.to_dict())
    return JSONResponse(status_code=422, content=body)


@app.exception_handler(ExternalServiceError)
async def external_service_error_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
    body = _inject_request_id(request, exc.to_dict())
    return JSONResponse(status_code=502, content=body)


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    body = _inject_request_id(request, exc.to_dict())
    return JSONResponse(status_code=400, content=body)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    exc_type = type(exc).__name__
    sanitized_msg = str(exc)[:200]
    logger.error("unhandled_exception", path=request.url.path, exc_type=exc_type, error_truncated=sanitized_msg)
    rid = request.headers.get("X-Request-ID", "")
    body = {"error": {"code": "INTERNAL_ERROR", "message": "Une erreur interne est survenue"}}
    body = _inject_request_id(request, body)
    return JSONResponse(status_code=500, content=body, headers={"X-Request-ID": rid})


@app.middleware("http")
async def log_response_time(request: Request, call_next):  # type: ignore[no-untyped-def]
    start = _time.time()
    response = await call_next(request)
    duration_ms = (_time.time() - start) * 1000
    response.headers["X-Response-Time"] = f"{int(duration_ms)}ms"
    response.headers["X-API-Version"] = _APP_VERSION
    response.headers["X-Powered-By"] = "OptiFlow AI"
    if duration_ms > 1000:
        logger.warning(
            "slow_request",
            path=request.url.path,
            method=request.method,
            duration_ms=int(duration_ms),
        )
    return response


@app.get(
    "/api/v1/version",
    summary="Version de l'API",
    description="Retourne la version courante de l'API, le prefixe et la date de build.",
    tags=["admin"],
)
def api_version() -> dict:
    return {"version": _APP_VERSION, "api": "v1", "build": "2026-04-06"}


@app.on_event("startup")
def startup() -> None:
    # La validation des secrets production est geree par le model_validator de Settings.
    # Si on arrive ici, les secrets sont acceptables pour l'environnement courant.

    # Verifier les migrations Alembic pending
    try:
        from alembic.config import Config as AlembicConfig
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from app.db.session import engine

        alembic_cfg = AlembicConfig("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            head_rev = script.get_current_head()
            if current_rev != head_rev:
                logger.warning(
                    "alembic_migrations_pending",
                    current=current_rev,
                    head=head_rev,
                    hint="Executer 'alembic upgrade head'",
                )
    except Exception as e:
        logger.warning("alembic_check_skipped", error=str(e)[:100])

    # Verifier les tables manquantes (WARNING seulement, pas de create_all)
    from app.db.base import Base
    from app.db.session import engine

    try:
        from sqlalchemy import inspect as sa_inspect

        inspector = sa_inspect(engine)
        db_tables = set(inspector.get_table_names())
        model_tables = set(Base.metadata.tables.keys())
        missing = model_tables - db_tables
        if missing:
            logger.error(
                "missing_tables_detected",
                missing=sorted(missing),
                count=len(missing),
                hint="Executer 'alembic upgrade head' pour creer les tables manquantes",
            )
            if settings.app_env in ("production", "staging"):
                raise RuntimeError(
                    f"Tables manquantes en {settings.app_env}: {sorted(missing)}. "
                    "Executer 'alembic upgrade head' avant de demarrer."
                )
        else:
            logger.info("all_model_tables_present", count=len(model_tables))
    except RuntimeError:
        raise
    except Exception as e:
        logger.error("table_verification_failed", error=str(e))

    # Seeding conditionnel — uniquement en dev/local et si active
    if settings.app_env in ("local", "development") and settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_data(db)
        finally:
            db.close()

    from app.integrations.storage import storage

    try:
        storage.ensure_bucket(settings.s3_bucket)
    except Exception as e:
        logger.error("minio_bucket_init_failed", error=str(e))
    logger.info("application_started", env=settings.app_env)


@app.get("/health", summary="Liveness check", description="Verification rapide que l'API est en ligne (pour load balancer).")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", summary="Readiness check", description="Verifie que PostgreSQL et Redis sont accessibles.")
def health_ready() -> dict:
    from sqlalchemy import text

    checks: dict[str, str] = {}
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    finally:
        db.close()

    try:
        import redis as redis_lib
        r = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "not_ready", "checks": checks}


app.include_router(action_items.router)
app.include_router(ai.router)
app.include_router(cosium_documents.router)
app.include_router(cosium_invoices.router)
app.include_router(ai_usage.router)
app.include_router(analytics.router)
app.include_router(audit.router)
app.include_router(banking.router)
app.include_router(billing.router)
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(client_mutuelles.router)
app.include_router(clients.router)
app.include_router(devis.router)
app.include_router(documents.router)
app.include_router(extractions.router)
app.include_router(factures.router)
app.include_router(notifications.router)
app.include_router(payments.router)
app.include_router(pec.router)
app.include_router(pec_preparation.router)
app.include_router(reconciliation.router)
app.include_router(reminders.router)
app.include_router(renewals.router)
app.include_router(consents.router)
app.include_router(marketing.router)
app.include_router(metrics.router)
app.include_router(search.router)
app.include_router(sync.router)
app.include_router(exports.router)
app.include_router(gdpr.router)
app.include_router(client_360.router)
app.include_router(admin_health.router)
app.include_router(admin_users.router)
app.include_router(dashboard.router)
app.include_router(onboarding.router)
app.include_router(cosium_reference.router)
app.include_router(cosium_spectacles.router)
app.include_router(cosium_catalog.router)
app.include_router(cosium_sav.router)
app.include_router(cosium_notes.router)
app.include_router(cosium_fidelity.router)
app.include_router(cosium_commercial.router)
app.include_router(ocam_operators.router)
app.include_router(batch_operations.router)
app.include_router(sse.router)
