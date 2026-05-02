"""Tests Celery webhook delivery + retry / backoff."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.repositories import webhook_repo
from app.services.webhook_service import generate_secret


@pytest.fixture(autouse=True)
def _patch_session_local(db, monkeypatch):
    """Le worker utilise SessionLocal (postgres prod). En test on patch
    pour reutiliser la session SQLite in-memory du fixture `db`."""

    def _fake_session_local():
        # Wrapper qui ignore close() pour que la session test reste
        # consultable apres l'appel au worker.
        class _NoCloseSession:
            def __init__(self, inner):
                self._inner = inner

            def __getattr__(self, name):
                return getattr(self._inner, name)

            def close(self):
                pass

        return _NoCloseSession(db)

    monkeypatch.setattr(
        "app.tasks.webhook_tasks.SessionLocal", _fake_session_local
    )
    return db


@pytest.fixture
def subscription(db, default_tenant):
    return webhook_repo.create_subscription(
        db,
        tenant_id=default_tenant.id,
        secret="test-secret",
        created_by_user_id=None,
        fields={
            "name": "Test",
            "url": "https://example.test/hook",
            "event_types": ["facture.created"],
        },
    )


@pytest.fixture
def delivery(db, default_tenant, subscription):
    return webhook_repo.create_delivery(
        db,
        subscription_id=subscription.id,
        tenant_id=default_tenant.id,
        event_type="facture.created",
        event_id="evt-1",
        payload={
            "event_id": "evt-1",
            "event_type": "facture.created",
            "tenant_id": default_tenant.id,
            "occurred_at": "2026-05-02T07:30:00Z",
            "data": {"id": 7},
        },
    )


def _mock_response(status_code: int = 200, text: str = "ok"):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    return resp


def test_delivery_success_marks_status_success(db, delivery):
    from app.tasks.webhook_tasks import deliver_webhook

    with patch("app.tasks.webhook_tasks.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.return_value = _mock_response(200)
        mock_client_cls.return_value = mock_client

        result = deliver_webhook(delivery.id)

    assert result["status"] == "success"

    db.refresh(delivery)
    assert delivery.status == "success"
    assert delivery.attempts == 1
    assert delivery.last_status_code == 200
    assert delivery.delivered_at is not None
    assert delivery.last_error is None


def test_delivery_signs_payload_with_hmac(db, delivery, subscription):
    """Le header X-Webhook-Signature-256 doit etre present et bien forme."""
    import hashlib
    import hmac
    import json

    from app.tasks.webhook_tasks import deliver_webhook

    captured_headers: dict = {}
    captured_body: bytes | None = None

    def _capture(url, content=None, headers=None, **kwargs):
        nonlocal captured_body
        captured_headers.update(headers or {})
        captured_body = content
        return _mock_response(200)

    with patch("app.tasks.webhook_tasks.httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.side_effect = _capture
        mock_client_cls.return_value = mock_client

        deliver_webhook(delivery.id)

    assert "X-Webhook-Signature-256" in captured_headers
    sig = captured_headers["X-Webhook-Signature-256"]
    assert sig.startswith("sha256=")

    expected = hmac.new(
        subscription.secret.encode("utf-8"),
        captured_body,
        hashlib.sha256,
    ).hexdigest()
    assert sig == f"sha256={expected}"

    # Le body doit etre du JSON parsable et contenir l'enveloppe attendue
    parsed = json.loads(captured_body.decode("utf-8"))
    assert parsed["event_type"] == "facture.created"
    assert parsed["data"] == {"id": 7}


def test_delivery_5xx_schedules_retry(db, delivery):
    from app.tasks.webhook_tasks import deliver_webhook

    enqueued: list[tuple[int, int]] = []

    def _fake_apply_async(args=None, countdown=None, **kwargs):
        enqueued.append((args[0], countdown))

    with patch("app.tasks.webhook_tasks.httpx.Client") as mock_client_cls, \
         patch.object(deliver_webhook, "apply_async", side_effect=_fake_apply_async):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.return_value = _mock_response(503, "service unavailable")
        mock_client_cls.return_value = mock_client

        result = deliver_webhook(delivery.id)

    assert result["status"] == "retrying"
    assert enqueued and enqueued[0][0] == delivery.id
    # 1er retry : 30s
    assert enqueued[0][1] == 30

    db.refresh(delivery)
    assert delivery.status == "retrying"
    assert delivery.attempts == 1
    assert delivery.last_status_code == 503
    assert delivery.next_retry_at is not None


def test_delivery_timeout_schedules_retry(db, delivery):
    from app.tasks.webhook_tasks import deliver_webhook

    with patch("app.tasks.webhook_tasks.httpx.Client") as mock_client_cls, \
         patch.object(deliver_webhook, "apply_async"):
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        mock_client_cls.return_value = mock_client

        result = deliver_webhook(delivery.id)

    assert result["status"] == "retrying"
    db.refresh(delivery)
    assert delivery.status == "retrying"
    assert "timeout" in (delivery.last_error or "")


def test_delivery_max_attempts_marks_failed(db, default_tenant, subscription):
    """Apres MAX_ATTEMPTS-1 echecs deja persistes, le prochain echec doit
    passer en `failed` (pas de re-enqueue)."""
    from app.services.webhook_service import MAX_ATTEMPTS
    from app.tasks.webhook_tasks import deliver_webhook

    delivery = webhook_repo.create_delivery(
        db,
        subscription_id=subscription.id,
        tenant_id=default_tenant.id,
        event_type="facture.created",
        event_id="evt-x",
        payload={
            "event_id": "evt-x",
            "event_type": "facture.created",
            "tenant_id": default_tenant.id,
            "occurred_at": "2026-05-02T07:30:00Z",
            "data": {"id": 1},
        },
    )
    delivery.attempts = MAX_ATTEMPTS - 1
    delivery.status = "retrying"
    db.commit()

    with patch("app.tasks.webhook_tasks.httpx.Client") as mock_client_cls, \
         patch.object(deliver_webhook, "apply_async") as mock_apply:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = False
        mock_client.post.return_value = _mock_response(500)
        mock_client_cls.return_value = mock_client

        result = deliver_webhook(delivery.id)

    assert result["status"] == "failed"
    assert mock_apply.call_count == 0

    db.refresh(delivery)
    assert delivery.status == "failed"
    assert delivery.attempts == MAX_ATTEMPTS


def test_delivery_skips_already_completed(db, delivery):
    from app.tasks.webhook_tasks import deliver_webhook

    delivery.status = "success"
    db.commit()

    result = deliver_webhook(delivery.id)
    assert result["status"] == "skipped"


def test_delivery_skips_inactive_subscription(db, delivery, subscription):
    from app.tasks.webhook_tasks import deliver_webhook

    subscription.is_active = False
    db.commit()

    result = deliver_webhook(delivery.id)
    assert result["status"] == "failed_inactive"
    db.refresh(delivery)
    assert delivery.status == "failed"
