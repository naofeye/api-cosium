"""Repository for AI usage logging."""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import AiUsageLog

logger = get_logger("ai_usage_repo")


def create(
    db: Session,
    tenant_id: int,
    user_id: int,
    copilot_type: str,
    model_used: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
) -> AiUsageLog | None:
    """Insert an AI usage log record. Returns None on failure."""
    try:
        usage = AiUsageLog(
            tenant_id=tenant_id,
            user_id=user_id,
            copilot_type=copilot_type,
            model_used=model_used,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
        )
        db.add(usage)
        db.commit()
        return usage
    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("ai_usage_log_failed", error=str(e))
        return None
