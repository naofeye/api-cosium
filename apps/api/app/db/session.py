from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Statement timeout : 30s pour l'API, 120s pour les workers Celery.
# Tache > 120s = signe d'un probleme (N+1, dead lock, sync non batchee) a investiguer.
_statement_timeout = 120000 if settings.celery_worker else 30000

# Pool de connexions PostgreSQL :
# - pool_size=50 : 50 connexions permanentes
# - max_overflow=50 : 50 connexions supplementaires en pic (total max = 100)
# - pool_recycle=1800 : recycler les connexions toutes les 30 min
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
