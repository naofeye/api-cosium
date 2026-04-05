from fastapi.testclient import TestClient


def test_create_client(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Alice", "last_name": "Martin", "email": "alice@test.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "Alice"
    assert data["last_name"] == "Martin"
    assert data["email"] == "alice@test.com"
    assert "id" in data


def test_list_clients(client: TestClient, auth_headers: dict) -> None:
    client.post(
        "/api/v1/clients",
        json={"first_name": "Bob", "last_name": "Leroy"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/clients", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


def test_search_clients(client: TestClient, auth_headers: dict) -> None:
    client.post(
        "/api/v1/clients",
        json={"first_name": "Charlie", "last_name": "Unique123"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/clients?q=Unique123", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["last_name"] == "Unique123"


def test_get_client(client: TestClient, auth_headers: dict) -> None:
    create_resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Diana", "last_name": "Prince"},
        headers=auth_headers,
    )
    client_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Diana"


def test_get_client_not_found(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/clients/99999", headers=auth_headers)
    assert resp.status_code == 404


def test_update_client(client: TestClient, auth_headers: dict) -> None:
    create_resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Eve", "last_name": "Adams", "city": "Paris"},
        headers=auth_headers,
    )
    client_id = create_resp.json()["id"]
    resp = client.put(
        f"/api/v1/clients/{client_id}",
        json={"city": "Lyon", "phone": "0601020304"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "Lyon"
    assert data["phone"] == "0601020304"
    assert data["first_name"] == "Eve"


def test_delete_client(client: TestClient, auth_headers: dict) -> None:
    create_resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Frank", "last_name": "ToDelete"},
        headers=auth_headers,
    )
    client_id = create_resp.json()["id"]
    resp = client.delete(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert "message" in resp.json()
    resp2 = client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert resp2.status_code == 404


def test_create_client_validation(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "", "last_name": "Test"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_clients_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/clients")
    assert resp.status_code == 401
