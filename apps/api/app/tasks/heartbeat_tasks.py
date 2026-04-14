"""Celery beat heartbeat — ecrit un timestamp dans Redis chaque minute.

Permet a /api/v1/admin/beat-status de detecter si le scheduler est mort.
"""
import time

import redis as redis_lib

from app.core.config import settings
from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("celery.heartbeat")

HEARTBEAT_KEY = "celery:beat:heartbeat"
HEARTBEAT_TTL = 600  # 10 min : la cle disparait si beat est mort > 10min


@celery_app.task(name="app.tasks.heartbeat_tasks.beat_heartbeat")
def beat_heartbeat() -> dict:
    """Ecrit le timestamp courant dans Redis. Declenche toutes les minutes."""
    ts = int(time.time())
    try:
        r = redis_lib.Redis.from_url(settings.redis_url, socket_timeout=2)
        r.set(HEARTBEAT_KEY, ts, ex=HEARTBEAT_TTL)
        return {"ok": True, "ts": ts}
    except Exception as e:
        logger.error("beat_heartbeat_write_failed", error=str(e))
        raise
