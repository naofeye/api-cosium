import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Statement timeout : 30s pour l'API, 300s pour les workers Celery (sync longues)
_is_celery_worker = "celery" in os.environ.get("_", "") or os.environ.get("CELERY_WORKER", "")
_statement_timeout = 300000 if _is_celery_worker else 30000

# Pool de connexions PostgreSQL :
# - pool_size=50 : 50 connexions permanentes
# - max_overflow=50 : 50 connexions supplementaires en pic (total max = 100)
# - pool_recycle=1800 : recycler les connexions toutes les 30 min
# - pool_pre_ping=True : verifier la connexion avant chaque utilisation
engine = create_engine(
    settings.database_url,
    future=True,
    echo=False,
    pool_size=50,
    max_overflow=50,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_timeout=30,
    connect_args={"options": f"-c statement_timeout={_statement_timeout}"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
