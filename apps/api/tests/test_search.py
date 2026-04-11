"""Tests pour la recherche globale."""

from fastapi.testclient import TestClient


def test_search_empty_query(client: TestClient, auth_headers: dict) -> None:
    """Recherche vide retourne des listes vides."""
    resp = client.get("/api/v1/search?q=", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["clients"] == []
    assert data["dossiers"] == []
    assert data["devis"] == []
    assert data["factures"] == []


def test_search_short_query(client: TestClient, auth_headers: dict) -> None:
    """Recherche avec < 2 caracteres retourne vide."""
    resp = client.get("/api/v1/search?q=a", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["clients"] == []


def test_search_finds_clients(client: TestClient, auth_headers: dict) -> None:
    """Recherche par nom de client fonctionne."""
    # Creer un client
    client.post(
        "/api/v1/clients",
        json={"first_name": "Recherche", "last_name": "Globale", "email": "rg@test.com"},
        headers=auth_headers,
    )

    resp = client.get("/api/v1/search?q=Globale", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["clients"]) >= 1
    assert any("Globale" in c["label"] for c in data["clients"])


def test_search_finds_devis(client: TestClient, auth_headers: dict) -> None:
    """Recherche par numero de devis fonctionne."""
    # Creer un case + devis
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Search", "last_name": "Devis", "source": "test"},
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
    numero = resp.json()["numero"]

    resp = client.get(f"/api/v1/search?q={numero}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["devis"]) >= 1


def test_search_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/search?q=test")
    assert resp.status_code == 401
