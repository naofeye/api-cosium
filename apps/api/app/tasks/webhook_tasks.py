"""Celery task : deliver_webhook + retries avec backoff borne."""
from __future__ import annotations

import json
import time as _time
from datetime import UTC, datetime, timedelta

import httpx

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.repositories import webhook_repo
from app.services._webhook.url_guard import WebhookUrlForbiddenError, assert_url_safe
from app.services.webhook_service import (
    MAX_ATTEMPTS,
    RETRY_DELAYS_SECONDS,
    sign_payload,
)
from app.tasks import celery_app

logger = get_logger("webhook_tasks")

# Timeout aggressif : un endpoint webhook ne doit pas faire pendre les workers.
DELIVERY_TIMEOUT_SECONDS = 10
USER_AGENT = "OptiFlow-Webhooks/1.0"


@celery_app.task(
    name="app.tasks.webhook_tasks.deliver_webhook",
    bind=True,
    max_retries=0,  # On gere les retries manuellement via next_retry_at
    time_limit=30,
    soft_time_limit=20,
)
def deliver_webhook(self, delivery_id: int) -> dict[str, str | int]:
    """Tente de livrer une webhook delivery.

    Strategie de retry maison (pas Celery's auto-retry) pour persister
    `next_retry_at` en BDD et permettre l'inspection humaine.
    """
    db = SessionLocal()
    try:
        delivery = webhook_repo.get_delivery_for_worker(db, delivery_id)
        if delivery is None:
            logger.warning("webhook_delivery_not_found", delivery_id=delivery_id)
            return {"status": "missing", "delivery_id": delivery_id}

        if delivery.status in ("success", "failed"):
            return {
                "status": "skipped",
                "delivery_id": delivery_id,
                "reason": delivery.status,
            }

        sub = delivery.subscription
        if sub is None or not sub.is_active:
            webhook_repo.update_delivery_status(
                db,
                delivery,
                status="failed",
                attempts=delivery.attempts,
                last_error="subscription_inactive_or_deleted",
            )
            db.commit()
            return {"status": "failed_inactive", "delivery_id": delivery_id}

        body = json.dumps(delivery.payload, separators=(",", ":")).encode("utf-8")
        signature = sign_payload(sub.secret, body)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "X-Webhook-Signature-256": signature,
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Event-Id": delivery.event_id,
            "X-Webhook-Delivery-Id": str(delivery.id),
            "X-Webhook-Timestamp": str(int(_time.time())),
        }

        attempt = delivery.attempts + 1
        started = _time.perf_counter()
        last_status_code: int | None = None
        last_error: str | None = None
        success = False

        try:
            # SSRF guard : refuser loopback / RFC1918 / link-local / metadata
            # cloud / hostnames Docker internes AVANT d'envoyer la requete.
            # follow_redirects=False : un endpoint public peut rediriger vers
            # une cible interne ; on ne suit jamais les 3xx.
            assert_url_safe(sub.url)
            with httpx.Client(
                timeout=DELIVERY_TIMEOUT_SECONDS, follow_redirects=False
            ) as client:
                response = client.post(sub.url, content=body, headers=headers)
                last_status_code = response.status_code
                if 200 <= response.status_code < 300:
                    success = True
                else:
                    last_error = (
                        f"HTTP {response.status_code} : {response.text[:500]}"
                    )
        except WebhookUrlForbiddenError as exc:
            last_error = f"url_forbidden : {exc!s}"[:500]
        except httpx.TimeoutException as exc:
            last_error = f"timeout : {exc!s}"[:500]
        except httpx.HTTPError as exc:
            last_error = f"network : {exc!s}"[:500]
        except Exception as exc:
            last_error = f"unexpected : {exc!s}"[:500]

        duration_ms = int((_time.perf_counter() - started) * 1000)

        if success:
            webhook_repo.update_delivery_status(
                db,
                delivery,
                status="success",
                attempts=attempt,
                last_status_code=last_status_code,
                last_error=None,
                next_retry_at=None,
                delivered_at=datetime.now(UTC).replace(tzinfo=None),
                duration_ms=duration_ms,
            )
            db.commit()
            logger.info(
                "webhook_delivered",
                delivery_id=delivery_id,
                tenant_id=delivery.tenant_id,
                event_type=delivery.event_type,
                attempts=attempt,
                duration_ms=duration_ms,
            )
            return {
                "status": "success",
                "delivery_id": delivery_id,
                "duration_ms": duration_ms,
            }

        # Echec : retry programme ou abandon
        if attempt >= MAX_ATTEMPTS:
            webhook_repo.update_delivery_status(
                db,
                delivery,
                status="failed",
                attempts=attempt,
                last_status_code=last_status_code,
                last_error=last_error,
                next_retry_at=None,
                duration_ms=duration_ms,
            )
            db.commit()
            logger.warning(
                "webhook_delivery_failed_final",
                delivery_id=delivery_id,
                tenant_id=delivery.tenant_id,
                event_type=delivery.event_type,
                attempts=attempt,
                last_status_code=last_status_code,
                last_error=last_error,
            )
            return {
                "status": "failed",
                "delivery_id": delivery_id,
                "attempts": attempt,
            }

        # Programmer le prochain retry
        delay = RETRY_DELAYS_SECONDS[attempt - 1] if attempt - 1 < len(RETRY_DELAYS_SECONDS) else RETRY_DELAYS_SECONDS[-1]
        next_retry = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=delay)
        webhook_repo.update_delivery_status(
            db,
            delivery,
            status="retrying",
            attempts=attempt,
            last_status_code=last_status_code,
            last_error=last_error,
            next_retry_at=next_retry,
            duration_ms=duration_ms,
        )
        db.commit()
        # Re-enqueue avec countdown : Celery rejouera la task apres le delai
        deliver_webhook.apply_async(args=[delivery_id], countdown=delay)
        logger.info(
            "webhook_delivery_retry_scheduled",
            delivery_id=delivery_id,
            tenant_id=delivery.tenant_id,
            event_type=delivery.event_type,
            attempts=attempt,
            next_retry_in_s=delay,
            last_error=last_error,
        )
        return {
            "status": "retrying",
            "delivery_id": delivery_id,
            "next_retry_in_s": delay,
        }
    finally:
        db.close()
