from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Pool de connexions PostgreSQL :
# - pool_size=20 : 20 connexions permanentes
# - max_overflow=20 : 20 connexions supplementaires en pic (total max = 40)
# - pool_recycle=1800 : recycler les connexions toutes les 30 min
# - pool_pre_ping=True : verifier la connexion avant chaque utilisation
# - statement_timeout=30s : eviter les requetes longues (API)
# Note: les workers Celery partagent ce pool — augmenter si necessaire
engine = create_engine(
    settings.database_url,
    future=True,
    echo=False,
    pool_size=20,
    max_overflow=20,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_timeout=30,
    connect_args={"options": "-c statement_timeout=30000"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
