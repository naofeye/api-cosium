"""Helpers d'alerting Sentry pour incidents critiques.

Centralise la logique de capture Sentry + tags + scope. Utilisable
depuis n'importe quel module (security.py, tasks/sync_tasks.py, etc.).

Principe : best-effort. Sentry non configure = no-op. Une erreur dans
Sentry lui-meme ne doit JAMAIS casser le flow appelant.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("sentry_helpers")


def report_incident_to_sentry(
    exc: Exception,
    tag: str,
    *,
    category: str = "incident",
    level: str = "error",
    **context: Any,
) -> None:
    """Capture l'exception vers Sentry avec des tags contextuels.

    Args:
        exc: exception a capturer.
        tag: identifiant court de l'incident (ex: "blacklist_setex_failed",
             "cosium_sync_failed"). Indexe par Sentry comme tag principal.
        category: categorie haut niveau (ex: "security", "sync", "infra").
                  Defaut "incident".
        level: severite Sentry ("error", "warning", "fatal").
        **context: champs libres (tenant_id, user_id, domain, etc.) ajoutes
                   comme tags Sentry pour filtrage.

    No-op si `settings.sentry_dsn` vide (dev/test).
    """
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("incident_category", category)
            scope.set_tag("incident", tag)
            scope.set_level(level)
            for key, value in context.items():
                if value is not None:
                    scope.set_tag(key, str(value))
            sentry_sdk.capture_exception(exc)
    except Exception as sentry_exc:  # noqa: BLE001 — Sentry failure ne doit jamais bloquer l'appelant
        logger.warning(
            "sentry_capture_failed",
            tag=tag,
            category=category,
            sentry_error=str(sentry_exc),
            sentry_error_type=type(sentry_exc).__name__,
            original_error=str(exc),
        )
