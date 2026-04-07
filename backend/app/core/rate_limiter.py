"""Redis-based rate limiter for sensitive endpoints.

Uses Redis INCR + EXPIRE for atomic counting.
Falls back to in-memory dict if Redis is unavailable.
"""

import threading
import time
from collections import defaultdict

import redis
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("rate_limiter")

# (path, method) -> (max_attempts, window_seconds)
RATE_LIMIT_RULES: dict[tuple[str, str], tuple[int, int]] = {
    ("/api/v1/auth/login", "POST"): (10, 60),
    ("/api/v1/auth/forgot-password", "POST"): (3, 3600),
    ("/api/v1/auth/reset-password", "POST"): (5, 3600),
    ("/api/v1/auth/refresh", "POST"): (20, 60),
    ("/api/v1/onboarding/signup", "POST"): (5, 60),
    ("/api/v1/ai/copilot/query", "POST"): (30, 60),
    ("/api/v1/gdpr", "POST"): (5, 60),
    ("/api/v1/banking/import-statement", "POST"): (5, 60),
    ("/api/v1/exports/fec", "GET"): (5, 60),
    ("/api/v1/clients/merge", "POST"): (5, 60),
    ("/api/v1/clients/import", "POST"): (5, 60),
    ("/api/v1/admin/users", "POST"): (10, 60),
    ("/api/v1/admin/detect-mutuelles", "POST"): (2, 300),
}

# Prefix-based rules: matched when no exact rule applies.
RATE_LIMIT_PREFIX_RULES: dict[tuple[str, str], tuple[int, int]] = {
    ("/api/v1/clients", "DELETE"): (10, 60),
    ("/api/v1/exports", "GET"): (5, 60),
    ("/api/v1/sync", "POST"): (3, 300),
    ("/api/v1/pec-preparations", "POST"): (5, 60),
    ("/api/v1/documents", "POST"): (10, 60),
    ("/api/v1/pec", "PATCH"): (10, 60),
    ("/api/v1/batch", "POST"): (5, 300),
}

# In-memory fallback — thread-safe (also exported as _global_attempts for backward compat in tests)
_fallback_lock = threading.Lock()
_fallback_attempts: dict[str, list[float]] = defaultdict(list)
_global_attempts = _fallback_attempts


def _get_redis_client() -> redis.Redis | None:
    """Create a Redis client, return None if unavailable."""
    try:
        r = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)
        r.ping()
        return r
    except Exception:
        return None


# Initialize Redis connection at module level
_redis: redis.Redis | None = _get_redis_client()


def _check_rate_limit_redis(key: str, max_attempts: int, window: int) -> bool:
    """Check rate limit using Redis. Returns True if request is allowed."""
    global _redis
    try:
        if _redis is None:
            _redis = _get_redis_client()
            if _redis is None:
                return _check_rate_limit_memory(key, max_attempts, window)

        redis_key = f"rate:{key}:{window}"
        current = _redis.incr(redis_key)
        if current == 1:
            _redis.expire(redis_key, window)

        return current <= max_attempts
    except (redis.ConnectionError, redis.TimeoutError, OSError) as e:
        logger.warning("rate_limiter_redis_fallback", error=str(e))
        _redis = None
        return _check_rate_limit_memory(key, max_attempts, window)


def _check_rate_limit_memory(key: str, max_attempts: int, window: int) -> bool:
    """Fallback in-memory rate limit check (thread-safe). Returns True if request is allowed."""
    now = time.time()
    with _fallback_lock:
        _fallback_attempts[key] = [t for t in _fallback_attempts[key] if now - t < window]

        if len(_fallback_attempts[key]) >= max_attempts:
            return False

        _fallback_attempts[key].append(now)
        return True


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    @staticmethod
    def _find_rule(path: str, method: str) -> tuple[int, int] | None:
        """Find rate-limit rule: exact match first, then prefix match."""
        exact = RATE_LIMIT_RULES.get((path, method))
        if exact:
            return exact
        for (prefix, m), rule in RATE_LIMIT_PREFIX_RULES.items():
            if method == m and path.startswith(prefix):
                return rule
        return None

    async def dispatch(self, request: Request, call_next):
        # Disable rate limiting in test/local environment
        if settings.app_env in ("test", "local"):
            return await call_next(request)

        rule = self._find_rule(request.url.path, request.method)
        if rule:
            max_attempts, window = rule
            # Utiliser X-Forwarded-For si derriere un proxy (nginx)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip = forwarded.split(",")[0].strip()
            else:
                ip = request.client.host if request.client else "unknown"
            key = f"{ip}:{request.url.path}"

            if not _check_rate_limit_redis(key, max_attempts, window):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "RATE_LIMITED",
                        "message": "Trop de tentatives. Reessayez dans une minute.",
                    },
                )

        return await call_next(request)
