"""Tests for the client quick-view endpoint."""

from fastapi.testclient import TestClient


def _create_client(client: TestClient, auth_headers: dict) -> int:
    """Helper: create a client and return its ID."""
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Quick", "last_name": "TestClient", "email": "quick@test.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_quick_endpoint_returns_client_data(
    client: TestClient, auth_headers: dict
) -> None:
    """Quick endpoint should return basic client fields."""
    client_id = _create_client(client, auth_headers)
    resp = client.get(f"/api/v1/clients/{client_id}/quick", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == client_id
    assert data["first_name"] == "Quick"
    assert data["last_name"] == "TestClient"
    assert "ca_total" in data
    assert "email" in data


def test_quick_endpoint_includes_correction_fields(
    client: TestClient, auth_headers: dict
) -> None:
    """Quick endpoint should include correction_od and correction_og fields (even if None)."""
    client_id = _create_client(client, auth_headers)
    resp = client.get(f"/api/v1/clients/{client_id}/quick", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Fields exist even when no prescription data
    assert "correction_od" in data
    assert "correction_og" in data
    assert "last_visit" in data


def test_quick_endpoint_nonexistent_client_returns_404(
    client: TestClient, auth_headers: dict
) -> None:
    """Quick endpoint for a non-existent client should return 404."""
    resp = client.get("/api/v1/clients/999999/quick", headers=auth_headers)
    assert resp.status_code == 404
