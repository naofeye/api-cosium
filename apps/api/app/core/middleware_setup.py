"""Configuration de la stack de middlewares FastAPI.

Extrait de `main.py`. Ordre des middlewares : `add_middleware` ajoute
en outermost, donc le dernier ajouté est le premier exécuté. Ordre
souhaité (outer → inner) : CORS > SecurityHeaders > RequestId >
RateLimiter > GZip. Les middlewares sont donc ajoutés dans l'ordre
innermost-first.
"""

import time as _time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware as _BaseGZipMiddleware

from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limiter import RateLimiterMiddleware
from app.core.request_id import RequestIdMiddleware
from app.core.security_headers import SecurityHeadersMiddleware

logger = get_logger("main")

# Paths où on skip GZip : SSE event-stream (doit rester non-compressé)
# et downloads / exports (streaming files, compression inutile + coût CPU).
_GZIP_SKIP_SEGMENTS = ("/sse", "/download", "/export")


class SelectiveGZipMiddleware(_BaseGZipMiddleware):
    """GZip middleware qui bypass les responses streaming (SSE, PDF downloads)."""

    async def __call__(self, scope, receive, send):  # type: ignore[override]
        if scope["type"] == "http":
            path: str = scope.get("path", "")
            if any(seg in path for seg in _GZIP_SKIP_SEGMENTS):
                await self.app(scope, receive, send)
                return
        await super().__call__(scope, receive, send)


def setup_middlewares(app: FastAPI, app_version: str) -> None:
    """Attache la stack de middlewares à l'application + le logger http."""
    # Middleware stack — last added = outermost in Starlette.
    # Desired order (outer → inner): CORS > SecurityHeaders > RequestId > RateLimiter > GZip
    app.add_middleware(SelectiveGZipMiddleware, minimum_size=1000)
    app.add_middleware(RateLimiterMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Idempotency-Key"],
    )

    @app.middleware("http")
    async def log_response_time(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = _time.time()
        response = await call_next(request)
        duration_ms = (_time.time() - start) * 1000
        response.headers["X-Response-Time"] = f"{int(duration_ms)}ms"
        response.headers["X-API-Version"] = app_version
        response.headers["X-Powered-By"] = "OptiFlow AI"
        if duration_ms > 1000:
            logger.warning(
                "slow_request",
                path=request.url.path,
                method=request.method,
                duration_ms=int(duration_ms),
            )
        return response
