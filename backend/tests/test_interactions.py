from fastapi.testclient import TestClient


def _create_client(client: TestClient, headers: dict) -> int:
    resp = client.post("/api/v1/clients", json={"first_name": "Inter", "last_name": "Test", "email": "inter@test.com"}, headers=headers)
    return resp.json()["id"]


def test_create_interaction(client: TestClient, auth_headers: dict) -> None:
    cid = _create_client(client, auth_headers)
    resp = client.post("/api/v1/interactions", json={"client_id": cid, "type": "appel", "direction": "entrant", "subject": "Demande info"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["type"] == "appel"
    assert resp.json()["direction"] == "entrant"


def test_list_interactions_by_client(client: TestClient, auth_headers: dict) -> None:
    cid = _create_client(client, auth_headers)
    client.post("/api/v1/interactions", json={"client_id": cid, "type": "note", "direction": "interne", "subject": "Note 1"}, headers=auth_headers)
    client.post("/api/v1/interactions", json={"client_id": cid, "type": "email", "direction": "sortant", "subject": "Email envoye"}, headers=auth_headers)
    resp = client.get(f"/api/v1/clients/{cid}/interactions", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_filter_interactions_by_type(client: TestClient, auth_headers: dict) -> None:
    cid = _create_client(client, auth_headers)
    client.post("/api/v1/interactions", json={"client_id": cid, "type": "appel", "direction": "entrant", "subject": "Appel 1"}, headers=auth_headers)
    client.post("/api/v1/interactions", json={"client_id": cid, "type": "note", "direction": "interne", "subject": "Note 1"}, headers=auth_headers)
    resp = client.get(f"/api/v1/clients/{cid}/interactions?type=appel", headers=auth_headers)
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["type"] == "appel"


def test_delete_interaction(client: TestClient, auth_headers: dict) -> None:
    cid = _create_client(client, auth_headers)
    resp = client.post("/api/v1/interactions", json={"client_id": cid, "type": "note", "direction": "interne", "subject": "A supprimer"}, headers=auth_headers)
    iid = resp.json()["id"]
    resp = client.delete(f"/api/v1/interactions/{iid}", headers=auth_headers)
    assert resp.status_code == 204
