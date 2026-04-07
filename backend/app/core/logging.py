import logging
from typing import Any

import structlog

from app.core.config import settings

# Niveau de log selon l'environnement
_LOG_LEVELS = {
    "local": logging.DEBUG,
    "development": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.INFO,
}
_level = _LOG_LEVELS.get(settings.app_env, logging.INFO)

# Champs sensibles a masquer dans les logs
_SENSITIVE_FIELDS = frozenset({
    "password", "password_hash", "old_password", "new_password",
    "token", "access_token", "refresh_token", "api_key",
    "secret", "jwt_secret", "encryption_key",
    "cosium_password", "cosium_access_token", "cosium_device_credential",
    "stripe_secret_key", "stripe_webhook_secret",
    "s3_secret_key",
})


def _mask_sensitive_fields(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Remplace les valeurs des champs sensibles par '***' dans les logs."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_FIELDS or key.lower().endswith(("_secret", "_key", "_token", "_password")):
            event_dict[key] = "***"
    return event_dict


structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _mask_sensitive_fields,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(logger_name=name)


# ---------------------------------------------------------------------------
# Decorator for structured operation logging (sync, PEC, exports, payments)
# ---------------------------------------------------------------------------

import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

_F = TypeVar("_F", bound=Callable[..., Any])

_op_logger = get_logger("operations")


def _extract_context(args: tuple, kwargs: dict) -> dict[str, Any]:
    """Try to pull tenant_id, user_id, and other useful context from args/kwargs."""
    ctx: dict[str, Any] = {}
    for key in ("tenant_id", "user_id", "preparation_id", "entity_type", "format"):
        if key in kwargs:
            ctx[key] = kwargs[key]
    return ctx


def log_operation(operation_name: str) -> Callable[[_F], _F]:
    """Decorator that logs start/end/failure of a critical operation with duration."""

    def decorator(func: _F) -> _F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            context = _extract_context(args, kwargs)
            _op_logger.info(f"{operation_name}_start", **context)
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start) * 1000)
                _op_logger.info(
                    f"{operation_name}_done", duration_ms=duration_ms, **context,
                )
                return result
            except Exception as exc:
                duration_ms = int((time.time() - start) * 1000)
                _op_logger.error(
                    f"{operation_name}_failed",
                    duration_ms=duration_ms,
                    error=str(exc)[:200],
                    **context,
                )
                raise

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            context = _extract_context(args, kwargs)
            _op_logger.info(f"{operation_name}_start", **context)
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.time() - start) * 1000)
                _op_logger.info(
                    f"{operation_name}_done", duration_ms=duration_ms, **context,
                )
                return result
            except Exception as exc:
                duration_ms = int((time.time() - start) * 1000)
                _op_logger.error(
                    f"{operation_name}_failed",
                    duration_ms=duration_ms,
                    error=str(exc)[:200],
                    **context,
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return wrapper  # type: ignore[return-value]

    return decorator
