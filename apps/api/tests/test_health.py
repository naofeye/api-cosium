from fastapi.testclient import TestClient


def test_health_admin_requires_auth(client: TestClient) -> None:
    """/api/v1/admin/health est sous auth admin (hardening anti-fingerprinting)."""
    resp = client.get("/api/v1/admin/health")
    assert resp.status_code == 401


def test_health_liveness_public(client: TestClient) -> None:
    """/health (racine) reste public pour load balancer liveness."""
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_admin_returns_components(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/admin/health", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "components" in data
    assert "database" in data["components"]


def test_health_database_ok(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/admin/health", headers=auth_headers)
    data = resp.json()
    assert data["components"]["database"]["status"] == "ok"
    assert data["components"]["database"]["response_ms"] >= 0


def test_health_includes_version_and_uptime(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/admin/health", headers=auth_headers)
    data = resp.json()
    assert "version" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], int)
    assert data["uptime_seconds"] >= 0


def test_version_endpoint(client: TestClient) -> None:
    """Version endpoint should return version info."""
    resp = client.get("/api/v1/version")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert data["api"] == "v1"
    assert "build" in data


def test_no_fingerprint_headers(client: TestClient) -> None:
    """Headers X-API-Version + X-Powered-By retires post-audit (fingerprint
    reconnaissance attaquant). Version reste dispo via body de /version."""
    resp = client.get("/api/v1/version")
    assert "X-API-Version" not in resp.headers
    assert "X-Powered-By" not in resp.headers
    # Body contient toujours la version
    assert resp.json()["version"]


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
