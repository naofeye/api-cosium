"""Taches Celery pour le cycle de vie des devis (expiration auto)."""

from datetime import UTC, datetime

from sqlalchemy import update

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.devis import Devis
from app.tasks import celery_app

logger = get_logger("celery.devis")


@celery_app.task(name="app.tasks.devis_tasks.expire_devis")
def expire_devis() -> dict:
    """Marque les devis arrives a echeance comme `expire`.

    Critere : status in ('brouillon', 'envoye') AND valid_until < now() AND deleted_at IS NULL.
    Les devis signes/refuses/factures sont laisses intacts.

    Execute quotidiennement via celery beat (3h15 du matin, hors heures ouvrees).
    Cross-tenant : un seul UPDATE atomique balaie tous les tenants — pas de fuite
    de donnees car on ne lit/affiche rien, on update uniquement le champ status.
    """
    db = SessionLocal()
    try:
        now = datetime.now(UTC).replace(tzinfo=None)
        result = db.execute(
            update(Devis)
            .where(
                Devis.status.in_(("brouillon", "envoye")),
                Devis.valid_until.is_not(None),
                Devis.valid_until < now,
                Devis.deleted_at.is_(None),
            )
            .values(status="expire", updated_at=now)
        )
        expired = result.rowcount
        db.commit()
        logger.info("devis_expiration_run", expired=expired)
        return {"expired": expired, "ran_at": now.isoformat()}
    except Exception as exc:
        db.rollback()
        logger.error("devis_expiration_failed", error=str(exc), error_type=type(exc).__name__)
        raise
    finally:
        db.close()
