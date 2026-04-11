"""Tests des endpoints API de renouvellement."""

from fastapi.testclient import TestClient


def test_get_opportunities(client: TestClient, auth_headers: dict) -> None:
    """GET /renewals/opportunities retourne une liste (potentiellement vide)."""
    resp = client.get("/api/v1/renewals/opportunities", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_opportunities_custom_params(client: TestClient, auth_headers: dict) -> None:
    """Les parametres de filtrage sont acceptes."""
    resp = client.get(
        "/api/v1/renewals/opportunities?age_minimum_months=12&min_invoice_amount=100",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_dashboard(client: TestClient, auth_headers: dict) -> None:
    """GET /renewals/dashboard retourne les KPIs."""
    resp = client.get("/api/v1/renewals/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_opportunities" in data
    assert "high_score_count" in data
    assert "estimated_revenue" in data
    assert "campaigns_sent" in data
    assert "top_opportunities" in data
    assert isinstance(data["top_opportunities"], list)


def test_create_campaign_requires_auth(client: TestClient) -> None:
    """POST /renewals/campaign sans auth retourne 401."""
    resp = client.post(
        "/api/v1/renewals/campaign",
        json={"name": "Test", "customer_ids": [1], "channel": "email"},
    )
    assert resp.status_code == 401


def _create_client_for_campaign(client: TestClient, headers: dict) -> int:
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Camp", "last_name": "Test", "email": "camp@test.com"},
        headers=headers,
    )
    return resp.json()["id"]


def test_create_campaign(client: TestClient, auth_headers: dict) -> None:
    """POST /renewals/campaign cree une campagne."""
    client_id = _create_client_for_campaign(client, auth_headers)
    resp = client.post(
        "/api/v1/renewals/campaign",
        json={
            "name": "Renouvellement Avril",
            "channel": "email",
            "customer_ids": [client_id],
            "use_ai_message": False,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "[Renouvellement]" in data["name"]
    assert data["customer_count"] == 1
    assert data["status"] == "draft"


def test_create_campaign_empty_customers(client: TestClient, auth_headers: dict) -> None:
    """Campagne sans clients = erreur validation."""
    resp = client.post(
        "/api/v1/renewals/campaign",
        json={"name": "Test", "channel": "email", "customer_ids": []},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_opportunities_unauthenticated(client: TestClient) -> None:
    """Les endpoints renouvellement necessitent une auth."""
    resp = client.get("/api/v1/renewals/opportunities")
    assert resp.status_code == 401


def test_dashboard_unauthenticated(client: TestClient) -> None:
    resp = client.get("/api/v1/renewals/dashboard")
    assert resp.status_code == 401
