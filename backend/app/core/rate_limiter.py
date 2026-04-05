"""In-memory rate limiter for sensitive endpoints."""

import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# (path, method) -> (max_attempts, window_seconds)
RATE_LIMIT_RULES: dict[tuple[str, str], tuple[int, int]] = {
    ("/api/v1/auth/login", "POST"): (10, 60),
    ("/api/v1/auth/refresh", "POST"): (20, 60),
    ("/api/v1/onboarding/signup", "POST"): (5, 60),
    ("/api/v1/ai/copilot/query", "POST"): (30, 60),
    ("/api/v1/gdpr", "POST"): (5, 60),  # anonymizations
    ("/api/v1/banking/import-statement", "POST"): (5, 60),  # bank imports
}

# Prefix-based rules: matched when no exact rule applies.
# (path_prefix, method) -> (max_attempts, window_seconds)
RATE_LIMIT_PREFIX_RULES: dict[tuple[str, str], tuple[int, int]] = {
    ("/api/v1/clients", "DELETE"): (10, 60),  # client deletions
}


_global_attempts: dict[str, list[float]] = defaultdict(list)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._attempts = _global_attempts

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
        rule = self._find_rule(request.url.path, request.method)
        if rule:
            max_attempts, window = rule
            ip = request.client.host if request.client else "unknown"
            key = f"{ip}:{request.url.path}"
            now = time.time()

            self._attempts[key] = [t for t in self._attempts[key] if now - t < window]

            if len(self._attempts[key]) >= max_attempts:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "RATE_LIMITED",
                        "message": "Trop de tentatives. Reessayez dans une minute.",
                    },
                )

            self._attempts[key].append(now)

        return await call_next(request)
