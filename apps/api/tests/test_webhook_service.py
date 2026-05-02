"""Tests webhook_service : signature HMAC + emit_webhook_event."""
from __future__ import annotations

import hmac
import hashlib

import pytest

from app.services.webhook_service import (
    MAX_ATTEMPTS,
    RETRY_DELAYS_SECONDS,
    build_envelope,
    emit_webhook_event,
    generate_secret,
    mask_secret,
    sign_payload,
)


def test_generate_secret_url_safe():
    secret = generate_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 40
    # caracteres URL-safe : alnum + - + _
    assert all(c.isalnum() or c in "-_" for c in secret)


def test_mask_secret_short():
    assert mask_secret("") == ""
    assert mask_secret("abc") == "***"
    assert mask_secret("abcd") == "****"


def test_mask_secret_long():
    s = "abcdefghij"
    masked = mask_secret(s)
    assert masked.startswith("abcd")
    assert masked.endswith("******")
    assert len(masked) == len(s)


def test_sign_payload_matches_hmac_sha256():
    secret = "my-secret"
    body = b'{"hello":"world"}'
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    sig = sign_payload(secret, body)
    assert sig == f"sha256={expected}"


def test_build_envelope_shape():
    env = build_envelope(
        event_type="facture.created", tenant_id=42, payload={"id": 7}
    )
    assert env["event_type"] == "facture.created"
    assert env["tenant_id"] == 42
    assert env["data"] == {"id": 7}
    assert "event_id" in env and len(env["event_id"]) >= 32
    assert env["occurred_at"].endswith("Z")


def test_retry_delays_are_increasing():
    assert MAX_ATTEMPTS == len(RETRY_DELAYS_SECONDS)
    for prev, nxt in zip(RETRY_DELAYS_SECONDS, RETRY_DELAYS_SECONDS[1:]):
        assert nxt > prev


def test_emit_no_subscriptions_returns_zero(db, default_tenant):
    """Pas de subscription = pas d'erreur, retourne 0."""
    count = emit_webhook_event(
        db,
        tenant_id=default_tenant.id,
        event_type="facture.created",
        payload={"id": 1},
    )
    assert count == 0


def test_emit_creates_delivery_for_active_subscription(db, default_tenant, monkeypatch):
    """Une subscription active sur l'event genere une delivery + enqueue."""
    from app.repositories import webhook_repo

    sub = webhook_repo.create_subscription(
        db,
        tenant_id=default_tenant.id,
        secret=generate_secret(),
        created_by_user_id=None,
        fields={
            "name": "Test",
            "url": "https://example.test/hook",
            "event_types": ["facture.created", "client.created"],
        },
    )

    enqueued: list[int] = []

    class _FakeDeliverWebhook:
        def delay(self, delivery_id: int) -> None:
            enqueued.append(delivery_id)

    # Patch le lazy import
    import app.tasks.webhook_tasks as wt

    monkeypatch.setattr(wt, "deliver_webhook", _FakeDeliverWebhook())

    count = emit_webhook_event(
        db,
        tenant_id=default_tenant.id,
        event_type="facture.created",
        payload={"id": 7},
    )
    assert count == 1
    assert len(enqueued) == 1

    # La delivery est en BDD avec le bon event_id
    deliveries, _ = webhook_repo.list_deliveries(db, default_tenant.id)
    assert len(deliveries) == 1
    d = deliveries[0]
    assert d.subscription_id == sub.id
    assert d.event_type == "facture.created"
    assert d.status == "pending"
    assert d.payload["data"] == {"id": 7}


def test_emit_skips_subscription_not_listening(db, default_tenant, monkeypatch):
    """Subscription qui n'ecoute pas l'event = ignoree."""
    from app.repositories import webhook_repo

    webhook_repo.create_subscription(
        db,
        tenant_id=default_tenant.id,
        secret=generate_secret(),
        created_by_user_id=None,
        fields={
            "name": "Only clients",
            "url": "https://example.test/hook",
            "event_types": ["client.created"],
        },
    )

    enqueued: list[int] = []
    import app.tasks.webhook_tasks as wt

    class _Fake:
        def delay(self, x):
            enqueued.append(x)

    monkeypatch.setattr(wt, "deliver_webhook", _Fake())

    count = emit_webhook_event(
        db,
        tenant_id=default_tenant.id,
        event_type="facture.created",
        payload={"id": 7},
    )
    assert count == 0
    assert enqueued == []


def test_emit_skips_inactive_subscription(db, default_tenant, monkeypatch):
    from app.repositories import webhook_repo

    webhook_repo.create_subscription(
        db,
        tenant_id=default_tenant.id,
        secret=generate_secret(),
        created_by_user_id=None,
        fields={
            "name": "Disabled",
            "url": "https://example.test/hook",
            "event_types": ["facture.created"],
            "is_active": False,
        },
    )

    enqueued: list[int] = []
    import app.tasks.webhook_tasks as wt

    class _Fake:
        def delay(self, x):
            enqueued.append(x)

    monkeypatch.setattr(wt, "deliver_webhook", _Fake())

    count = emit_webhook_event(
        db,
        tenant_id=default_tenant.id,
        event_type="facture.created",
        payload={"id": 1},
    )
    assert count == 0


def test_emit_isolated_per_tenant(db, default_tenant, monkeypatch):
    """Subscription d'un autre tenant n'est jamais notifiee."""
    from app.models import Organization, Tenant
    from app.repositories import webhook_repo

    other_org = Organization(name="Other Org", slug="other-org", plan="solo")
    db.add(other_org)
    db.flush()
    other_tenant = Tenant(
        organization_id=other_org.id,
        name="Autre Magasin",
        slug="autre-magasin",
        erp_type="cosium",
        cosium_tenant="other",
        cosium_login="other",
        cosium_password_enc="other",
    )
    db.add(other_tenant)
    db.flush()

    webhook_repo.create_subscription(
        db,
        tenant_id=other_tenant.id,
        secret=generate_secret(),
        created_by_user_id=None,
        fields={
            "name": "Other tenant",
            "url": "https://example.test/hook",
            "event_types": ["facture.created"],
        },
    )

    import app.tasks.webhook_tasks as wt

    class _Fake:
        def delay(self, x):
            pass

    monkeypatch.setattr(wt, "deliver_webhook", _Fake())

    count = emit_webhook_event(
        db,
        tenant_id=default_tenant.id,
        event_type="facture.created",
        payload={"id": 1},
    )
    assert count == 0
