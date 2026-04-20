import time as _time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401, E402
from app.api.registry import register_routers
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import get_logger
from app.core.middleware_setup import setup_middlewares
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


def _startup_checks() -> None:
    """Verifications et initialisations au demarrage (migrations, tables, seed, bucket)."""
    if settings.app_env == "test":
        logger.info("startup_external_checks_skipped", env=settings.app_env)
        return

    # Verifier les migrations Alembic pending
    try:
        from alembic.config import Config as AlembicConfig
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from app.db.session import engine  # noqa: I001

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
                if settings.app_env in ("production", "staging"):
                    raise RuntimeError(
                        f"Schema Alembic incoherent en {settings.app_env}: "
                        f"current={current_rev} head={head_rev}. "
                        "Executer 'alembic upgrade head' avant de demarrer."
                    )
    except RuntimeError:
        raise
    except Exception as e:
        logger.warning("alembic_check_skipped", error=str(e)[:100], error_type=type(e).__name__)

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
        logger.error("table_verification_failed", error=str(e), error_type=type(e).__name__)

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
        logger.error("minio_bucket_init_failed", error=str(e), error_type=type(e).__name__)
    logger.info("application_started", env=settings.app_env)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Remplace @app.on_event('startup') deprecie. Execute checks au demarrage."""
    _startup_checks()
    yield


app = FastAPI(
    lifespan=_lifespan,
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

# Setup : middlewares → exception handlers → routers
setup_middlewares(app, _APP_VERSION)
register_exception_handlers(app)
register_routers(app)


@app.get(
    "/api/v1/version",
    summary="Version de l'API",
    description="Retourne la version courante de l'API, le prefixe et la date de build.",
    tags=["admin"],
)
def api_version() -> dict:
    return {"version": _APP_VERSION, "api": "v1", "build": "2026-04-06"}


@app.get(
    "/health",
    summary="Liveness check",
    description="Verification rapide que l'API est en ligne (pour load balancer).",
)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/health/ready",
    summary="Readiness check",
    description="Verifie que PostgreSQL et Redis sont accessibles.",
)
def health_ready() -> dict:
    from sqlalchemy import text

    checks: dict[str, str] = {}
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("readiness_check_db_failed", error=str(exc), error_type=type(exc).__name__)
        checks["database"] = "error"
    finally:
        db.close()

    try:
        import redis as redis_lib

        r = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.warning("readiness_check_redis_failed", error=str(exc), error_type=type(exc).__name__)
        checks["redis"] = "error"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "not_ready", "checks": checks}
