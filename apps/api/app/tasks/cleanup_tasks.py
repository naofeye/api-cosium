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


@celery_app.task(name="app.tasks.cleanup_tasks.apply_retention_policy")
def apply_retention_policy(audit_log_keep_days: int = 365, action_items_resolved_keep_days: int = 90) -> dict:
    """Politique de retention RGPD : purge audit_logs > 12 mois et action_items resolus > 90j.

    Execution quotidienne via beat (3h45 AM).
    """
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import delete

    from app.models import AuditLog
    from app.models.notification import ActionItem

    db = SessionLocal()
    deleted_audit = 0
    deleted_actions = 0
    try:
        cutoff_audit = (datetime.now(UTC) - timedelta(days=audit_log_keep_days)).replace(tzinfo=None)
        result_audit = db.execute(
            delete(AuditLog).where(AuditLog.created_at < cutoff_audit)
        )
        deleted_audit = result_audit.rowcount or 0

        cutoff_actions = (datetime.now(UTC) - timedelta(days=action_items_resolved_keep_days)).replace(tzinfo=None)
        result_actions = db.execute(
            delete(ActionItem).where(
                ActionItem.status.in_(["resolved", "dismissed"]),
                ActionItem.created_at < cutoff_actions,
            )
        )
        deleted_actions = result_actions.rowcount or 0

        db.commit()
        logger.info(
            "retention_policy_applied",
            deleted_audit=deleted_audit,
            deleted_actions=deleted_actions,
            audit_keep_days=audit_log_keep_days,
            actions_keep_days=action_items_resolved_keep_days,
        )
        return {"deleted_audit": deleted_audit, "deleted_actions": deleted_actions}
    except Exception as e:
        db.rollback()
        logger.error("retention_policy_failed", error=str(e))
        raise
    finally:
        db.close()
