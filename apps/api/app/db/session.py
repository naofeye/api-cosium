from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Statement timeout : 30s pour l'API, 120s pour les workers Celery.
# Tache > 120s = signe d'un probleme (N+1, dead lock, sync non batchee) a investiguer.
_statement_timeout = 120000 if settings.celery_worker else 30000
_pool_size = max(settings.database_pool_size, 1)
_max_overflow = max(settings.database_max_overflow, 0)
_pool_recycle = max(settings.database_pool_recycle_seconds, 30)
_pool_timeout = max(settings.database_pool_timeout_seconds, 1)

# Pool de connexions PostgreSQL :
# - valeurs configurables par env pour s'adapter aux petits deploiements
# - pool_recycle : recycler les connexions periodiquement
# - pool_pre_ping=True : verifier la connexion avant chaque utilisation
_is_sqlite = settings.database_url.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        settings.database_url,
        future=True,
        echo=False,
    )
else:
    engine = create_engine(
        settings.database_url,
        future=True,
        echo=False,
        pool_size=_pool_size,
        max_overflow=_max_overflow,
        pool_recycle=_pool_recycle,
        pool_pre_ping=True,
        pool_timeout=_pool_timeout,
        connect_args={"options": f"-c statement_timeout={_statement_timeout}"},
    )
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
