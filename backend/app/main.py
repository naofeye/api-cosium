from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401
from app.api.routers import (
    action_items,
    admin_health,
    ai,
    ai_usage,
    analytics,
    audit,
    auth,
    banking,
    billing,
    cases,
    client_360,
    clients,
    consents,
    dashboard,
    devis,
    documents,
    exports,
    factures,
    gdpr,
    marketing,
    notifications,
    onboarding,
    payments,
    pec,
    reminders,
    renewals,
    search,
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
    version="1.2.0",
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
)

# Middleware stack (order matters: first added = outermost)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Idempotency-Key"],
)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content=exc.to_dict())


@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=401, content=exc.to_dict())


@app.exception_handler(ForbiddenError)
async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
    return JSONResponse(status_code=403, content=exc.to_dict())


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content=exc.to_dict())


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    return JSONResponse(status_code=400, content=exc.to_dict())


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Une erreur interne est survenue"}},
    )


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(action_items.router)
app.include_router(ai.router)
app.include_router(ai_usage.router)
app.include_router(analytics.router)
app.include_router(audit.router)
app.include_router(banking.router)
app.include_router(billing.router)
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(clients.router)
app.include_router(devis.router)
app.include_router(documents.router)
app.include_router(factures.router)
app.include_router(notifications.router)
app.include_router(payments.router)
app.include_router(pec.router)
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
app.include_router(dashboard.router)
app.include_router(onboarding.router)
