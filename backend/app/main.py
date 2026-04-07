import time as _time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware as _BaseGZipMiddleware

_APP_VERSION = "1.0.0"
_APP_START_TIME = _time.time()

from app import models  # noqa: F401
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
    billing,
    cases,
    client_360,
    client_mutuelles,
    clients,
    consents,
    cosium_documents,
    cosium_invoices,
    cosium_reference,
    dashboard,
    ocam_operators,
    devis,
    documents,
    exports,
    extractions,
    factures,
    gdpr,
    marketing,
    notifications,
    onboarding,
    payments,
    pec,
    pec_preparation,
    reminders,
    renewals,
    search,
    sse,
    sync,
)
from app.core.exceptions import (
    AuthenticationError,
    BusinessError,
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

logger = get_logger("main")

# Sentry (optional)
from app.core.config import settings

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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
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


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    body = _inject_request_id(request, exc.to_dict())
    return JSONResponse(status_code=400, content=body)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_type=type(exc).__name__)
    body = {"error": {"code": "INTERNAL_ERROR", "message": "Une erreur interne est survenue"}}
    body = _inject_request_id(request, body)
    return JSONResponse(status_code=500, content=body)


@app.middleware("http")
async def add_version_header(request: Request, call_next):  # type: ignore[no-untyped-def]
    response = await call_next(request)
    response.headers["X-API-Version"] = _APP_VERSION
    response.headers["X-Powered-By"] = "OptiFlow AI"
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
    # Security check: refuse to start with default secret in production
    if settings.app_env in ("production", "staging") and settings.jwt_secret == "change-me-super-secret":
        raise RuntimeError(
            "FATAL: JWT_SECRET is set to default value. Change it in .env before starting in production."
        )

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
    logger.info("application_started")


@app.get("/health", summary="Health check", description="Verification rapide que l'API est en ligne.")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
app.include_router(reminders.router)
app.include_router(renewals.router)
app.include_router(consents.router)
app.include_router(marketing.router)
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
app.include_router(ocam_operators.router)
app.include_router(sse.router)
