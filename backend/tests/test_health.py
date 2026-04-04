from fastapi.testclient import TestClient


def test_health_public(client: TestClient) -> None:
    """Health check should work without auth (public for load balancer)."""
    resp = client.get("/api/v1/admin/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "services" in data
    assert "postgres" in data["services"]


def test_health_postgres_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/admin/health")
    data = resp.json()
    assert data["services"]["postgres"]["status"] == "ok"
    assert data["services"]["postgres"]["response_ms"] >= 0


def test_metrics_requires_auth(client: TestClient) -> None:
    """Metrics endpoint should require authentication."""
    resp = client.get("/api/v1/admin/metrics")
    assert resp.status_code == 401


def test_metrics_returns_data(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/admin/metrics", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "totals" in data
    assert "activity" in data
    assert data["totals"]["clients"] >= 0  # scoped to tenant
    assert "actions_last_hour" in data["activity"]
    assert "active_users_last_hour" in data["activity"]
