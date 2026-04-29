"""Middleware d'injection de request_id pour la correlation des logs."""

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Le X-Request-ID client n'est accepte qu'en dev/test. En prod c'est un
        # vecteur de log poisoning : un attaquant peut imposer un ID arbitraire
        # qui sera ensuite injecte dans tous les logs et headers de reponse,
        # brouillant le tracing forensic post-incident.
        accept_client_id = settings.app_env in ("local", "development", "test")
        client_id = request.headers.get("X-Request-ID", "") if accept_client_id else ""
        if client_id and client_id.isalnum() and len(client_id) <= 64:
            request_id = client_id
        else:
            request_id = uuid.uuid4().hex[:16]

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
