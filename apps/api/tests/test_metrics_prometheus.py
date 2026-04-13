"""Tests endpoint /api/v1/metrics — format Prometheus exposition."""


def test_metrics_endpoint_returns_text(client):
    """Le endpoint metrics doit retourner du text/plain (format Prometheus)."""
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]


def test_metrics_contains_expected_counters(client):
    """4 metrics globaux exposes : tenants, users (total + active), customers."""
    resp = client.get("/api/v1/metrics")
    body = resp.text
    assert "optiflow_tenants_total" in body
    assert "optiflow_users_total" in body
    assert "optiflow_users_active" in body
    assert "optiflow_customers_total" in body


def test_metrics_format_help_and_type(client):
    """Chaque metric a une ligne # HELP et # TYPE (format Prometheus standard)."""
    resp = client.get("/api/v1/metrics")
    body = resp.text
    assert "# HELP optiflow_tenants_total" in body
    assert "# TYPE optiflow_tenants_total gauge" in body


def test_metrics_no_auth_required(client):
    """Pas d'auth requise (bind 127.0.0.1 + nginx restrict en prod)."""
    resp = client.get("/api/v1/metrics")
    # Ne doit pas etre 401/403
    assert resp.status_code == 200


def test_metrics_values_are_integers(client):
    """Les compteurs sont des entiers (count from DB)."""
    resp = client.get("/api/v1/metrics")
    for line in resp.text.split("\n"):
        if line.startswith("optiflow_") and not line.startswith("#"):
            parts = line.rsplit(" ", 1)
            if len(parts) == 2:
                value = parts[1]
                # Doit etre parseable comme int (ou float pour gauge en general)
                assert value.replace(".", "").replace("-", "").isdigit() or value == "0"
