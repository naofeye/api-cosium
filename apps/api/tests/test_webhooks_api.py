"""Tests endpoints CRUD webhooks."""
from __future__ import annotations

import pytest


def test_list_allowed_events(client, auth_headers):
    resp = client.get("/api/v1/webhooks/events", headers=auth_headers)
    assert resp.status_code == 200
    events = resp.json()["events"]
    assert "client.created" in events
    assert "facture.created" in events
    assert events == sorted(events)


def test_create_subscription_returns_secret_once(client, auth_headers):
    resp = client.post(
        "/api/v1/webhooks/subscriptions",
        headers=auth_headers,
        json={
            "name": "Test sub",
            "url": "https://example.com/hook",
            "event_types": ["facture.created", "client.created"],
            "description": "test",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test sub"
    assert "secret" in data and len(data["secret"]) >= 40
    assert data["secret_masked"] != data["secret"]
    assert data["secret_masked"].startswith(data["secret"][:4])


def test_list_subscriptions_masks_secret(client, auth_headers):
    client.post(
        "/api/v1/webhooks/subscriptions",
        headers=auth_headers,
        json={
            "name": "Sub 1",
            "url": "https://example.com/hook",
            "event_types": ["facture.created"],
        },
    )
    resp = client.get("/api/v1/webhooks/subscriptions", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    for item in items:
        assert "secret_masked" in item
        assert "secret" not in item


def test_create_rejects_invalid_event_type(client, auth_headers):
    resp = client.post(
        "/api/v1/webhooks/subscriptions",
        headers=auth_headers,
        json={
            "name": "Bad",
            "url": "https://example.com/hook",
            "event_types": ["unknown.event"],
        },
    )
    assert resp.status_code == 422


def test_create_rejects_invalid_url(client, auth_headers):
    resp = client.post(
        "/api/v1/webhooks/subscriptions",
        headers=auth_headers,
        json={
            "name": "Bad",
            "url": "not-a-url",
            "event_types": ["client.created"],
        },
    )
    assert resp.status_code == 422


def test_update_subscription(client, auth_headers):
    create = client.post(
        "/api/v1/webhooks/subscriptions",
        headers=auth_headers,
        json={
            "name": "Original",
            "url": "https://example.com/hook",
            "event_types": ["facture.created"],
        },
    )
    sub_id = create.json()["id"]

    resp = client.patch(
        f"/api/v1/webhooks/subscriptions/{sub_id}",
        headers=auth_headers,
        json={"name": "Updated", "is_active": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated"
    assert data["is_active"] is False


def test_delete_subscription(client, auth_headers):
    create = client.post(
        "/api/v1/webhooks/subscriptions",
        headers=auth_headers,
        json={
            "name": "Doomed",
            "url": "https://example.com/hook",
            "event_types": ["facture.created"],
        },
    )
    sub_id = create.json()["id"]

    resp = client.delete(
        f"/api/v1/webhooks/subscriptions/{sub_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    detail = client.get(
        f"/api/v1/webhooks/subscriptions/{sub_id}", headers=auth_headers
    )
    assert detail.status_code == 404


def test_get_subscription_404(client, auth_headers):
    resp = client.get(
        "/api/v1/webhooks/subscriptions/99999", headers=auth_headers
    )
    assert resp.status_code == 404


def test_list_deliveries_empty(client, auth_headers):
    resp = client.get("/api/v1/webhooks/deliveries", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_replay_delivery(db, default_tenant, client, auth_headers, monkeypatch):
    from app.repositories import webhook_repo

    sub = webhook_repo.create_subscription(
        db,
        tenant_id=default_tenant.id,
        secret="x",
        created_by_user_id=None,
        fields={
            "name": "T",
            "url": "https://example.com/h",
            "event_types": ["facture.created"],
        },
    )
    delivery = webhook_repo.create_delivery(
        db,
        subscription_id=sub.id,
        tenant_id=default_tenant.id,
        event_type="facture.created",
        event_id="evt-r",
        payload={"data": {}},
    )
    delivery = webhook_repo.update_delivery_status(
        db,
        delivery,
        status="failed",
        attempts=5,
        last_status_code=500,
        last_error="boom",
    )

    enqueued: list[int] = []
    import app.tasks.webhook_tasks as wt

    class _Fake:
        def delay(self, x):
            enqueued.append(x)

    monkeypatch.setattr(wt, "deliver_webhook", _Fake())

    resp = client.post(
        f"/api/v1/webhooks/deliveries/{delivery.id}/replay",
        headers=auth_headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert data["attempts"] == 0
    assert enqueued == [delivery.id]
