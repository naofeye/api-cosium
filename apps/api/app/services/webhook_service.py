"""Service webhooks : emit() + helpers signature HMAC.

Point d'entree pour les services metier : `emit_webhook_event(...)` cree une
delivery par subscription active et enqueue le job Celery.

Le job worker (`app.tasks.webhook_tasks.deliver_webhook`) est lazy-imported
pour eviter l'import circulaire (celery_app charge les services au boot).

Best-effort : un crash dans `emit_webhook_event` ne doit JAMAIS interrompre
le flux metier (creation de facture, client, etc.). Erreurs loguees + Sentry.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories import webhook_repo

logger = get_logger("webhook_service")

# Backoff exponentiel : 30s, 2min, 15min, 1h, 6h. 5 tentatives total.
RETRY_DELAYS_SECONDS: tuple[int, ...] = (30, 120, 900, 3600, 21600)
MAX_ATTEMPTS = len(RETRY_DELAYS_SECONDS)


def generate_secret() -> str:
    """Genere un secret HMAC URL-safe de ~43 caracteres."""
    return secrets.token_urlsafe(32)


def mask_secret(secret: str) -> str:
    """Masque tout sauf les 4 premiers caracteres (UI display)."""
    if not secret:
        return ""
    if len(secret) <= 4:
        return "*" * len(secret)
    return secret[:4] + "*" * (len(secret) - 4)


def sign_payload(secret: str, body: bytes) -> str:
    """Calcule HMAC-SHA256 hex pour le body et le secret."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def build_envelope(
    *, event_type: str, tenant_id: int, payload: dict
) -> dict[str, Any]:
    """Construit l'enveloppe JSON envoyee au webhook.

    Format stable, documente dans docs/WEBHOOKS.md :
        {
          "event_id": "uuid-v4",
          "event_type": "facture.created",
          "tenant_id": 12,
          "occurred_at": "2026-05-02T07:30:00Z",
          "data": { ...payload metier... }
        }
    """
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "tenant_id": tenant_id,
        "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "data": payload,
    }


def emit_webhook_event(
    db: Session,
    *,
    tenant_id: int,
    event_type: str,
    payload: dict,
) -> int:
    """Cree les deliveries pour les subscriptions actives du tenant et
    enqueue les jobs Celery.

    Best-effort : erreurs loguees, jamais propagees au caller metier.

    Retourne le nombre de subscriptions notifiees.
    """
    try:
        subs = webhook_repo.get_active_subscriptions_for_event(
            db, tenant_id, event_type
        )
        if not subs:
            return 0

        # Lazy import : evite cycle webhook_service -> tasks -> celery -> ... -> service
        from app.tasks.webhook_tasks import deliver_webhook

        envelope = build_envelope(
            event_type=event_type, tenant_id=tenant_id, payload=payload
        )

        notified = 0
        delivery_ids: list[int] = []
        for sub in subs:
            try:
                delivery = webhook_repo.create_delivery(
                    db,
                    subscription_id=sub.id,
                    tenant_id=tenant_id,
                    event_type=event_type,
                    event_id=envelope["event_id"],
                    payload=envelope,
                )
                delivery_ids.append(delivery.id)
                notified += 1
            except Exception as exc:
                logger.warning(
                    "webhook_emit_subscription_failed",
                    tenant_id=tenant_id,
                    subscription_id=sub.id,
                    event_type=event_type,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        # Commit pour rendre les deliveries visibles au worker, puis enqueue
        if delivery_ids:
            db.commit()
            for did in delivery_ids:
                deliver_webhook.delay(did)

        logger.info(
            "webhook_emit_done",
            tenant_id=tenant_id,
            event_type=event_type,
            subscriptions_notified=notified,
        )
        return notified
    except Exception as exc:
        # Best-effort : on ne casse pas le flux metier amont
        logger.error(
            "webhook_emit_failed",
            tenant_id=tenant_id,
            event_type=event_type,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        try:
            from app.core.sentry_helpers import report_incident_to_sentry

            report_incident_to_sentry(
                exc, "webhook_emit_failed", tenant_id=tenant_id, event_type=event_type
            )
        except Exception:
            pass
        return 0
