"""Handlers d'exceptions FastAPI centralisés.

Extrait de `main.py`. Chaque handler convertit une exception métier
(définie dans `app.core.exceptions`) en `JSONResponse` avec le status
HTTP approprié et un payload `{"error": {...}}`. Le `request_id` est
injecté depuis le header `X-Request-ID` pour faciliter le tracing.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AuthenticationError,
    BusinessError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger

logger = get_logger("main")


def _inject_request_id(request: Request, body: dict) -> dict:
    """Ajoute `request_id` depuis les headers dans le body d'erreur."""
    rid = request.headers.get("X-Request-ID", "")
    if "error" in body and isinstance(body["error"], dict):
        body["error"]["request_id"] = rid
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attache tous les handlers d'exceptions métier et le fallback."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        body = _inject_request_id(request, exc.to_dict())
        return JSONResponse(status_code=404, content=body)

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        body = _inject_request_id(request, exc.to_dict())
        return JSONResponse(status_code=401, content=body)

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError) -> JSONResponse:
        body = _inject_request_id(request, exc.to_dict())
        return JSONResponse(status_code=403, content=body)

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        body = _inject_request_id(request, exc.to_dict())
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(ExternalServiceError)
    async def external_service_error_handler(
        request: Request, exc: ExternalServiceError
    ) -> JSONResponse:
        body = _inject_request_id(request, exc.to_dict())
        return JSONResponse(status_code=502, content=body)

    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        body = _inject_request_id(request, exc.to_dict())
        return JSONResponse(status_code=400, content=body)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        exc_type = type(exc).__name__
        sanitized_msg = str(exc)[:200]
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            exc_type=exc_type,
            error_truncated=sanitized_msg,
        )
        rid = request.headers.get("X-Request-ID", "")
        body = {"error": {"code": "INTERNAL_ERROR", "message": "Une erreur interne est survenue"}}
        body = _inject_request_id(request, body)
        return JSONResponse(status_code=500, content=body, headers={"X-Request-ID": rid})
