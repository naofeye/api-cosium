"""Tests endpoint /api/v1/metrics — format Prometheus exposition.

Audit Codex M3 (2026-05-02) : `/metrics` est protege par un bearer token
configurable via METRICS_TOKEN en prod/staging. En dev/test, ouvert si
le token n'est pas defini.
"""
from app.core.config import settings


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_metrics_with_valid_token_returns_text(client, monkeypatch):
    """Avec METRICS_TOKEN configure et bearer correct : 200 + text/plain."""
    monkeypatch.setattr(settings, "metrics_token", "test-secret-token-123")
    resp = client.get("/api/v1/metrics", headers=_auth_headers("test-secret-token-123"))
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


def test_metrics_contains_expected_counters(client, monkeypatch):
    """4 metrics globaux exposes : tenants, users (total + active), customers."""
    monkeypatch.setattr(settings, "metrics_token", "test-secret")
    resp = client.get("/api/v1/metrics", headers=_auth_headers("test-secret"))
    body = resp.text
    assert "optiflow_tenants_total" in body
    assert "optiflow_users_total" in body
    assert "optiflow_users_active" in body
    assert "optiflow_customers_total" in body


def test_metrics_format_help_and_type(client, monkeypatch):
    """Chaque metric a une ligne # HELP et # TYPE (format Prometheus standard)."""
    monkeypatch.setattr(settings, "metrics_token", "test-secret")
    resp = client.get("/api/v1/metrics", headers=_auth_headers("test-secret"))
    body = resp.text
    assert "# HELP optiflow_tenants_total" in body
    assert "# TYPE optiflow_tenants_total gauge" in body


def test_metrics_rejects_missing_token_in_prod(client, monkeypatch):
    """Sans bearer en prod avec METRICS_TOKEN configure : 401."""
    monkeypatch.setattr(settings, "metrics_token", "test-secret")
    monkeypatch.setattr(settings, "app_env", "production")
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 401


def test_metrics_rejects_wrong_token(client, monkeypatch):
    """Bearer invalide : 403."""
    monkeypatch.setattr(settings, "metrics_token", "test-secret")
    resp = client.get("/api/v1/metrics", headers=_auth_headers("wrong"))
    assert resp.status_code == 403


def test_metrics_refuses_in_prod_without_configured_token(client, monkeypatch):
    """En prod, si METRICS_TOKEN n'est pas defini : 403 (defense en profondeur)."""
    monkeypatch.setattr(settings, "metrics_token", "")
    monkeypatch.setattr(settings, "app_env", "production")
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 403


def test_metrics_open_in_dev_without_token(client, monkeypatch):
    """En dev/test, si METRICS_TOKEN vide : ouvert (scrape local sans setup)."""
    monkeypatch.setattr(settings, "metrics_token", "")
    monkeypatch.setattr(settings, "app_env", "test")
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200


def test_metrics_values_are_integers(client, monkeypatch):
    """Les compteurs sont des entiers (count from DB)."""
    monkeypatch.setattr(settings, "metrics_token", "test-secret")
    resp = client.get("/api/v1/metrics", headers=_auth_headers("test-secret"))
    for line in resp.text.split("\n"):
        if line.startswith("optiflow_") and not line.startswith("#"):
            parts = line.rsplit(" ", 1)
            if len(parts) == 2:
                value = parts[1]
                # Doit etre parseable comme int (ou float pour gauge en general)
                assert value.replace(".", "").replace("-", "").isdigit() or value == "0"
