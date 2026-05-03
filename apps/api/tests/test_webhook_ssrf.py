"""Tests du guard SSRF webhooks (Codex critique #1, REVIEW.md 2026-05-03).

Couvre `app.services._webhook.url_guard.assert_url_safe` :
- accepte les URLs publiques
- refuse loopback (127/8, ::1)
- refuse RFC1918 (10/8, 172.16/12, 192.168/16)
- refuse link-local (169.254/16, dont metadata cloud 169.254.169.254)
- refuse IPv6 ULA (fc00::/7), IPv6 link-local (fe80::/10), multicast
- refuse hostnames Docker compose internes (api, postgres, redis, ...)
- refuse hostnames qui resolvent vers des IPs internes
- refuse schemes non-http/https
- integration : le worker `deliver_webhook` n'envoie pas la requete et
  marque la delivery comme `url_forbidden`
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.repositories import webhook_repo
from app.services._webhook.url_guard import (
    WebhookUrlForbiddenError,
    assert_url_safe,
)

# --- Tests unitaires du validateur ---------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/hook",
        "https://127.0.0.1/hook",
        "http://localhost/hook",
        "http://[::1]/hook",
        "http://10.0.0.5/hook",
        "http://10.255.255.254/hook",
        "http://172.16.0.1/hook",
        "http://172.31.255.254/hook",
        "http://192.168.1.1/hook",
        "http://169.254.169.254/latest/meta-data/",  # AWS / GCP / Azure IMDS
        "http://169.254.0.1/hook",
        "http://[fe80::1]/hook",  # IPv6 link-local
        "http://[fc00::1]/hook",  # IPv6 ULA
        "http://[::]/hook",        # unspecified
    ],
)
def test_rejects_internal_ip_literal(url):
    with pytest.raises(WebhookUrlForbiddenError):
        assert_url_safe(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://api/hook",
        "http://postgres:5432/hook",
        "http://redis/hook",
        "http://minio/hook",
        "http://web/hook",
        "http://worker/hook",
        "http://beat/hook",
        "http://mailhog/hook",
        "http://localhost:8000/hook",
        "http://LOCALHOST/hook",  # case insensitive
    ],
)
def test_rejects_docker_internal_hostnames(url):
    with pytest.raises(WebhookUrlForbiddenError):
        assert_url_safe(url)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://example.com/",
        "ftp://example.com/",
        "javascript:alert(1)",
        "data:text/html,foo",
    ],
)
def test_rejects_non_http_schemes(url):
    with pytest.raises(WebhookUrlForbiddenError):
        assert_url_safe(url)


def test_rejects_url_without_hostname():
    with pytest.raises(WebhookUrlForbiddenError):
        assert_url_safe("http:///path")


def test_rejects_hostname_resolving_to_internal_ip(monkeypatch):
    """Hostname public en apparence mais resout vers RFC1918 / metadata."""
    import socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        # Resout vers AWS metadata IP
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("169.254.169.254", 0))]

    monkeypatch.setattr(
        "app.services._webhook.url_guard.socket.getaddrinfo", fake_getaddrinfo
    )
    with pytest.raises(WebhookUrlForbiddenError, match="resolu vers IP interne"):
        assert_url_safe("https://innocent.example.com/hook")


def test_rejects_hostname_with_one_internal_ip_among_several(monkeypatch):
    """Defense contre DNS rebinding partiel : si une seule IP est interne,
    on refuse l'URL completement."""
    import socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("8.8.8.8", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.0.0.1", 0)),
        ]

    monkeypatch.setattr(
        "app.services._webhook.url_guard.socket.getaddrinfo", fake_getaddrinfo
    )
    with pytest.raises(WebhookUrlForbiddenError):
        assert_url_safe("https://multi-a-record.example.com/hook")


def test_rejects_hostname_not_resolvable(monkeypatch):
    import socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(
        "app.services._webhook.url_guard.socket.getaddrinfo", fake_getaddrinfo
    )
    with pytest.raises(WebhookUrlForbiddenError, match="non resolvable"):
        assert_url_safe("https://nope.invalid./hook")


def test_accepts_public_ip_literal():
    """8.8.8.8 (Google DNS) est public et doit passer."""
    assert_url_safe("https://8.8.8.8/hook")


def test_accepts_public_hostname(monkeypatch):
    import socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(
        "app.services._webhook.url_guard.socket.getaddrinfo", fake_getaddrinfo
    )
    # Pas d'exception
    assert_url_safe("https://example.com/hook")


# --- Test integration : le worker bloque la delivery sur SSRF ------------


@pytest.fixture
def _patch_session_local_for_integration(db, monkeypatch):
    """Comme test_webhook_tasks.py, on patche SessionLocal -> session test."""

    class _NoCloseSession:
        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            return getattr(self._inner, name)

        def close(self):
            pass

    monkeypatch.setattr(
        "app.tasks.webhook_tasks.SessionLocal", lambda: _NoCloseSession(db)
    )
    return db


def test_worker_marks_delivery_url_forbidden_when_ssrf(
    db, default_tenant, _patch_session_local_for_integration, monkeypatch
):
    """Si le validateur leve, la task ne doit PAS appeler httpx et doit
    enregistrer `url_forbidden : ...` dans last_error."""
    from app.tasks.webhook_tasks import deliver_webhook

    sub = webhook_repo.create_subscription(
        db,
        tenant_id=default_tenant.id,
        secret="test-secret",
        created_by_user_id=None,
        fields={
            "name": "Internal",
            "url": "http://api:8000/admin/hook",  # hostname Docker interne
            "event_types": ["facture.created"],
        },
    )
    delivery = webhook_repo.create_delivery(
        db,
        subscription_id=sub.id,
        tenant_id=default_tenant.id,
        event_type="facture.created",
        event_id="evt-ssrf",
        payload={
            "event_id": "evt-ssrf",
            "event_type": "facture.created",
            "tenant_id": default_tenant.id,
            "occurred_at": "2026-05-02T07:30:00Z",
            "data": {"id": 1},
        },
    )

    with patch("app.tasks.webhook_tasks.httpx.Client") as mock_client_cls, \
         patch.object(deliver_webhook, "apply_async") as mock_apply:
        result = deliver_webhook(delivery.id)
        # httpx ne doit JAMAIS etre instancie : le guard a fail-fast
        mock_client_cls.assert_not_called()

    # 1 retry programme (status retrying, pas success)
    assert result["status"] == "retrying"
    db.refresh(delivery)
    assert delivery.status == "retrying"
    assert delivery.attempts == 1
    assert delivery.last_status_code is None
    assert "url_forbidden" in (delivery.last_error or "")
    assert "api" in (delivery.last_error or "")
    # apply_async a ete appele 1 fois pour le retry
    assert mock_apply.call_count == 1
