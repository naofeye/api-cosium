"""Simple Redis cache for expensive queries. Disabled in test env."""

import json
import threading
import time

import redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("cache")

_redis: redis.Redis | None = None
_CACHE_DISABLED = settings.app_env == "test"
_fallback_lock = threading.Lock()
_fallback_locks: dict[str, float] = {}


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
        except Exception as exc:
            logger.warning("redis_connection_failed", error=str(exc))
            _redis = None
    return _redis


def get_redis_client() -> redis.Redis | None:
    """Public accessor for the Redis client (used by lockout, etc.)."""
    return _get_redis()


def _reset_on_connection_error() -> None:
    """Reset the global Redis reference so the next call attempts to reconnect."""
    global _redis
    _redis = None


def cache_get(key: str) -> dict | list | None:
    """Get a value from cache. Returns None on miss or error."""
    r = _get_redis()
    if not r:
        return None
    try:
        data = r.get(key)
        return json.loads(data) if data else None
    except (redis.ConnectionError, redis.TimeoutError):
        _reset_on_connection_error()
        return None
    except Exception as exc:
        logger.warning("cache_get_failed", key=key, error=str(exc))
        return None


def cache_set(key: str, value: dict | list, ttl: int = 300) -> None:
    """Set a value in cache with TTL in seconds."""
    r = _get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except (redis.ConnectionError, redis.TimeoutError):
        _reset_on_connection_error()
        logger.warning("cache_set_connection_lost", key=key)
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
    except (redis.ConnectionError, redis.TimeoutError):
        _reset_on_connection_error()
        logger.warning("cache_delete_connection_lost", pattern=pattern)
    except Exception as exc:
        logger.warning("cache_delete_pattern_failed", pattern=pattern, error=str(exc))


def acquire_lock(key: str, ttl: int = 300) -> bool:
    """Try to acquire a distributed lock. Returns True if acquired, False otherwise.

    Falls back to an in-memory TTL lock when Redis is unavailable so local/test
    environments keep working without silently allowing duplicate execution.
    """
    r = _get_redis()
    if not r:
        now = time.monotonic()
        with _fallback_lock:
            expires_at = _fallback_locks.get(key, 0.0)
            if expires_at > now:
                logger.warning("acquire_lock_fallback_conflict", key=key)
                return False
            _fallback_locks[key] = now + ttl
            logger.info("acquire_lock_fallback", key=key, ttl=ttl)
            return True
    try:
        return bool(r.set(key, "1", nx=True, ex=ttl))
    except Exception as exc:
        logger.warning("acquire_lock_redis_error", key=key, error=str(exc))
        now = time.monotonic()
        with _fallback_lock:
            expires_at = _fallback_locks.get(key, 0.0)
            if expires_at > now:
                return False
            _fallback_locks[key] = now + ttl
            return True


def release_lock(key: str) -> None:
    """Release a distributed lock."""
    with _fallback_lock:
        _fallback_locks.pop(key, None)
    r = _get_redis()
    if not r:
        return
    try:
        r.delete(key)
    except Exception:
        pass
