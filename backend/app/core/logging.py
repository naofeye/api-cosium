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
