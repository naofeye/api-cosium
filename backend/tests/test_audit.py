from fastapi.testclient import TestClient


def test_audit_logs_after_client_create(client: TestClient, auth_headers: dict) -> None:
    # Create a client (should generate audit log)
    client.post(
        "/api/v1/clients",
        json={"first_name": "Audit", "last_name": "Test"},
        headers=auth_headers,
    )
    # Check audit logs
    resp = client.get("/api/v1/audit-logs?entity_type=client", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["entity_type"] == "client"
    assert data["items"][0]["action"] == "create"


def test_audit_logs_requires_admin(client: TestClient) -> None:
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 401


def test_audit_logs_pagination(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/audit-logs?page=1&page_size=5", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 5
