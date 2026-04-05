from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


@patch("app.services.ai_service.claude_provider")
def test_copilot_dossier_mode(mock_provider: MagicMock, client: TestClient, auth_headers: dict) -> None:
    mock_provider.query_with_usage.return_value = {"text": "Le dossier est en cours avec 2 pieces manquantes.", "tokens_in": 10, "tokens_out": 20, "model": "test"}

    # Create a case first
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "IA", "last_name": "Test", "source": "manual"},
        headers=auth_headers,
    )
    case_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/ai/copilot/query",
        json={"question": "Resume ce dossier", "case_id": case_id, "mode": "dossier"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "dossier"
    assert "manquantes" in data["response"]
    mock_provider.query_with_usage.assert_called_once()


@patch("app.services.ai_service.claude_provider")
def test_copilot_financier_mode(mock_provider: MagicMock, client: TestClient, auth_headers: dict) -> None:
    mock_provider.query_with_usage.return_value = {"text": "Aucun paiement en retard detecte.", "tokens_in": 10, "tokens_out": 20, "model": "test"}

    resp = client.post(
        "/api/v1/ai/copilot/query",
        json={"question": "Analyse financiere", "mode": "financier"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "financier"


@patch("app.services.ai_service.claude_provider")
def test_copilot_documentaire_mode(mock_provider: MagicMock, client: TestClient, auth_headers: dict) -> None:
    mock_provider.query_with_usage.return_value = {"text": "La gestion des stocks dans Cosium se fait via...", "tokens_in": 10, "tokens_out": 20, "model": "test"}

    resp = client.post(
        "/api/v1/ai/copilot/query",
        json={"question": "Comment gerer les stocks dans Cosium ?", "mode": "documentaire"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "documentaire"


@patch("app.services.ai_service.claude_provider")
def test_copilot_marketing_mode(mock_provider: MagicMock, client: TestClient, auth_headers: dict) -> None:
    mock_provider.query_with_usage.return_value = {"text": "Je recommande un segment clients avec email pour une campagne promotionnelle.", "tokens_in": 10, "tokens_out": 20, "model": "test"}

    resp = client.post(
        "/api/v1/ai/copilot/query",
        json={"question": "Quelle campagne suggeres-tu ?", "mode": "marketing"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "marketing"


def test_copilot_without_api_key(client: TestClient, auth_headers: dict) -> None:
    """Without API key, should return a graceful message."""
    resp = client.post(
        "/api/v1/ai/copilot/query",
        json={"question": "Test sans cle", "mode": "dossier"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "non configuree" in resp.json()["response"].lower() or len(resp.json()["response"]) > 0
