"""Tests endpoint test-ping webhook."""
from __future__ import annotations

import pytest

from app.repositories import webhook_repo
from app.services.webhook_service import generate_secret


@pytest.fixture
def subscription(db, default_tenant):
    sub = webhook_repo.create_subscription(
        db,
        tenant_id=default_tenant.id,
        secret=generate_secret(),
        created_by_user_id=None,
        fields={
            "name": "Test ping target",
            "url": "https://example.test/hook",
            "event_types": ["facture.created"],
        },
    )
    db.commit()
    return sub


def test_test_ping_creates_delivery(client, auth_headers, db, default_tenant, subscription, monkeypatch):
    """Test ping cree une delivery 'webhook.test_ping' + enqueue worker."""
    enqueued: list[int] = []
    import app.tasks.webhook_tasks as wt

    class _Fake:
        def delay(self, x: int) -> None:
            enqueued.append(x)

    monkeypatch.setattr(wt, "deliver_webhook", _Fake())

    resp = client.post(
        f"/api/v1/webhooks/subscriptions/{subscription.id}/test-ping",
        headers=auth_headers,
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["event_type"] == "webhook.test_ping"
    assert body["status"] == "pending"
    assert body["attempts"] == 0
    assert enqueued == [body["id"]]


def test_test_ping_404_unknown_subscription(client, auth_headers):
    resp = client.post(
        "/api/v1/webhooks/subscriptions/99999/test-ping", headers=auth_headers
    )
    assert resp.status_code == 404


def test_webhook_test_ping_in_allowed_events(client, auth_headers):
    resp = client.get("/api/v1/webhooks/events", headers=auth_headers)
    assert resp.status_code == 200
    events = resp.json()["events"]
    assert "webhook.test_ping" in events
