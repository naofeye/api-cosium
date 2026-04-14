"""Taches de maintenance : purge des tokens orphelins."""
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.repositories import refresh_token_repo
from app.tasks import celery_app

logger = get_logger("celery.cleanup")


@celery_app.task(name="app.tasks.cleanup_tasks.purge_refresh_tokens")
def purge_refresh_tokens(keep_days: int = 30) -> dict:
    """Supprime les refresh tokens revokes ou expires depuis > keep_days.

    Execute quotidiennement via celery beat (voir beat_schedule).
    """
    db = SessionLocal()
    try:
        deleted = refresh_token_repo.purge_orphans(db, keep_days=keep_days)
        db.commit()
        logger.info("refresh_tokens_purged", deleted=deleted, keep_days=keep_days)
        return {"deleted": deleted, "keep_days": keep_days}
    except Exception as e:
        db.rollback()
        logger.error("refresh_tokens_purge_failed", error=str(e))
        raise
    finally:
        db.close()
