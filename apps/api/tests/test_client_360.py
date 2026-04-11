from fastapi.testclient import TestClient


def _create_client_with_data(client: TestClient, headers: dict) -> int:
    resp = client.post("/api/v1/clients", json={"first_name": "V360", "last_name": "Test", "email": "v360@test.com"}, headers=headers)
    cid = resp.json()["id"]
    # Create a case
    client.post("/api/v1/cases", json={"first_name": "V360", "last_name": "Test", "source": "test"}, headers=headers)
    # Add interaction
    client.post("/api/v1/interactions", json={"client_id": cid, "type": "note", "direction": "interne", "subject": "Note test"}, headers=headers)
    return cid


def test_client_360_all_sections(client: TestClient, auth_headers: dict) -> None:
    cid = _create_client_with_data(client, auth_headers)
    resp = client.get(f"/api/v1/clients/{cid}/360", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] == "V360"
    assert "dossiers" in data
    assert "devis" in data
    assert "factures" in data
    assert "paiements" in data
    assert "documents" in data
    assert "pec" in data
    assert "consentements" in data
    assert "interactions" in data
    assert "resume_financier" in data


def test_client_360_financial_summary(client: TestClient, auth_headers: dict) -> None:
    cid = _create_client_with_data(client, auth_headers)
    resp = client.get(f"/api/v1/clients/{cid}/360", headers=auth_headers)
    fin = resp.json()["resume_financier"]
    assert "total_facture" in fin
    assert "total_paye" in fin
    assert "reste_du" in fin
    assert "taux_recouvrement" in fin


def test_client_360_not_found(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/clients/99999/360", headers=auth_headers)
    assert resp.status_code == 404


def test_client_360_interactions_included(client: TestClient, auth_headers: dict) -> None:
    cid = _create_client_with_data(client, auth_headers)
    resp = client.get(f"/api/v1/clients/{cid}/360", headers=auth_headers)
    data = resp.json()
    assert len(data["interactions"]) >= 1
    assert data["interactions"][0]["subject"] == "Note test"
