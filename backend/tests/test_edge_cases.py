"""Tests d'edge cases — divisions par zero, listes vides, valeurs nulles."""

from fastapi.testclient import TestClient


def test_dashboard_with_no_data(client: TestClient, auth_headers: dict) -> None:
    """Dashboard sans aucune donnee ne doit pas crasher."""
    resp = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_due"] >= 0
    assert data["total_paid"] >= 0
    assert data["remaining"] >= 0


def test_analytics_with_no_data(client: TestClient, auth_headers: dict) -> None:
    """Analytics sans donnees — tous les taux doivent etre 0, pas de crash."""
    resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["financial"]["taux_recouvrement"] >= 0
    assert data["commercial"]["taux_conversion"] >= 0
    assert data["operational"]["taux_completude"] >= 0


def test_devis_requires_at_least_one_line(client: TestClient, auth_headers: dict) -> None:
    """Creer un devis sans lignes doit echouer (422)."""
    # D'abord creer un case
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Edge", "last_name": "Case", "source": "test"},
        headers=auth_headers,
    )
    case_id = resp.json()["id"]

    # Devis sans lignes
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0, "lignes": []},
        headers=auth_headers,
    )
    assert resp.status_code == 422  # Pydantic validation: min_length=1


def test_devis_invalid_status_transition(client: TestClient, auth_headers: dict) -> None:
    """Transition de statut invalide (signe → brouillon) doit echouer."""
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Transition", "last_name": "Test", "source": "test"},
        headers=auth_headers,
    )
    case_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/devis",
        json={
            "case_id": case_id,
            "part_secu": 0,
            "part_mutuelle": 0,
            "lignes": [{"designation": "Test", "quantite": 1, "prix_unitaire_ht": 100, "taux_tva": 20}],
        },
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]

    # brouillon → envoye → signe OK
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "envoye"}, headers=auth_headers)
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "signe"}, headers=auth_headers)

    # signe → brouillon INTERDIT
    resp = client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "brouillon"}, headers=auth_headers)
    assert resp.status_code == 400


def test_facture_from_unsigned_devis_fails(client: TestClient, auth_headers: dict) -> None:
    """Generer une facture depuis un devis non signe doit echouer."""
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Facture", "last_name": "Fail", "source": "test"},
        headers=auth_headers,
    )
    case_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/devis",
        json={
            "case_id": case_id,
            "part_secu": 0,
            "part_mutuelle": 0,
            "lignes": [{"designation": "Test", "quantite": 1, "prix_unitaire_ht": 50, "taux_tva": 20}],
        },
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]

    # Devis en brouillon → facture doit echouer
    resp = client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    assert resp.status_code == 400


def test_case_not_found_returns_404(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/cases/999999", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_client_not_found_returns_404(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/clients/999999", headers=auth_headers)
    assert resp.status_code == 404


def test_action_item_invalid_status(client: TestClient, auth_headers: dict) -> None:
    """Envoyer un status invalide a un action item doit echouer (422)."""
    resp = client.get("/api/v1/action-items?status=pending", headers=auth_headers)
    items = resp.json()["items"]
    if items:
        item_id = items[0]["id"]
        resp = client.patch(
            f"/api/v1/action-items/{item_id}",
            json={"status": "invalide_status"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
