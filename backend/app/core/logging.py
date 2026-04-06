import logging

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

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
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

import time
from functools import wraps
from typing import Any, Callable, TypeVar

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
                    error=str(exc),
                    **context,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
