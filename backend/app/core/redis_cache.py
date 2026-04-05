"""Simple Redis cache for expensive queries. Disabled in test env."""

import json

import redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("cache")

_redis: redis.Redis | None = None
_CACHE_DISABLED = settings.app_env == "test"


def _get_redis() -> redis.Redis | None:
    if _CACHE_DISABLED:
        return None
    global _redis
    if _redis is None:
        try:
            _redis = redis.Redis.from_url(
                settings.redis_url or "redis://redis:6379/0",
                decode_responses=True,
                socket_timeout=2,
            )
            _redis.ping()
        except Exception:
            _redis = None
    return _redis


def cache_get(key: str) -> dict | list | None:
    """Get a value from cache. Returns None on miss or error."""
    r = _get_redis()
    if not r:
        return None
    try:
        data = r.get(key)
        return json.loads(data) if data else None
    except Exception:
        return None


def cache_set(key: str, value: dict | list, ttl: int = 300) -> None:
    """Set a value in cache with TTL in seconds."""
    r = _get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning("cache_set_failed", key=key, error=str(exc))


def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern."""
    r = _get_redis()
    if not r:
        return
    try:
        for key in r.scan_iter(match=pattern):
            r.delete(key)
    except Exception as exc:
        logger.warning("cache_delete_pattern_failed", pattern=pattern, error=str(exc))
