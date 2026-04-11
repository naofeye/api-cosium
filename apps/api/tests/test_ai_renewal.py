"""Tests du copilote IA renouvellement (avec mock IA)."""

from unittest.mock import patch

from fastapi.testclient import TestClient


import uuid


def _create_client(client: TestClient, headers: dict) -> int:
    uid = uuid.uuid4().hex[:8]
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Renewal", "last_name": f"Test{uid}", "email": f"renewal{uid}@test.com"},
        headers=headers,
    )
    assert resp.status_code == 201, f"Client creation failed: {resp.status_code} {resp.text[:200]}"
    return resp.json()["id"]


@patch("app.services.ai_renewal_copilot.claude_provider")
def test_generate_message_endpoint(mock_provider, client: TestClient, auth_headers: dict) -> None:
    """L'endpoint de generation de message appelle le provider IA."""
    mock_provider.query_with_usage.return_value = {
        "text": "Bonjour, il est temps de renouveler vos lunettes !",
        "tokens_in": 100,
        "tokens_out": 50,
        "model": "claude-haiku",
    }
    client_id = _create_client(client, auth_headers)
    resp = client.post(
        f"/api/v1/renewals/generate-message?customer_id={client_id}&channel=email",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    assert data["channel"] == "email"
    assert data["customer_id"] == client_id


@patch("app.services.ai_renewal_copilot.claude_provider")
def test_ai_analysis_endpoint(mock_provider, client: TestClient, auth_headers: dict) -> None:
    """L'endpoint d'analyse IA retourne une analyse textuelle."""
    mock_provider.query_with_usage.return_value = {
        "text": "Analyse: 5 opportunites detectees, concentrez-vous sur les clients a fort score.",
        "tokens_in": 200,
        "tokens_out": 100,
        "model": "claude-haiku",
    }
    resp = client.get("/api/v1/renewals/ai-analysis", headers=auth_headers)
    assert resp.status_code == 200
    assert "analysis" in resp.json()


@patch("app.services.ai_renewal_copilot.claude_provider")
def test_generate_message_sms(mock_provider, client: TestClient, auth_headers: dict) -> None:
    """La generation SMS fonctionne aussi."""
    mock_provider.query_with_usage.return_value = {
        "text": "RDV renouvellement lunettes?",
        "tokens_in": 80,
        "tokens_out": 20,
        "model": "claude-haiku",
    }
    client_id = _create_client(client, auth_headers)
    resp = client.post(
        f"/api/v1/renewals/generate-message?customer_id={client_id}&channel=sms",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["channel"] == "sms"
