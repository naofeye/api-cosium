from fastapi.testclient import TestClient


def test_action_items_empty(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/action-items", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["items"], list)
    assert "total" in data
    assert "counts" in data


def test_refresh_generates_items(client: TestClient, auth_headers: dict) -> None:
    client.post(
        "/api/v1/cases",
        json={"first_name": "Action", "last_name": "Test", "source": "manual"},
        headers=auth_headers,
    )
    resp = client.post("/api/v1/action-items/refresh", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    types = [item["type"] for item in data["items"]]
    assert "dossier_incomplet" in types


def test_update_action_item_status(client: TestClient, auth_headers: dict) -> None:
    client.post(
        "/api/v1/cases",
        json={"first_name": "Update", "last_name": "Test", "source": "manual"},
        headers=auth_headers,
    )
    client.post("/api/v1/action-items/refresh", headers=auth_headers)

    resp = client.get("/api/v1/action-items?status=pending", headers=auth_headers)
    items = resp.json()["items"]
    if items:
        item_id = items[0]["id"]
        resp = client.patch(
            f"/api/v1/action-items/{item_id}",
            json={"status": "done"},
            headers=auth_headers,
        )
        assert resp.status_code == 204
