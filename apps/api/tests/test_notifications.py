from fastapi.testclient import TestClient


def test_notifications_empty(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 0
    assert isinstance(data["items"], list)
    assert "unread_count" in data


def test_unread_count(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert data["count"] >= 0


def test_notification_created_on_case_create(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Notif", "last_name": "Test", "source": "manual"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    resp = client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    titles = [n["title"] for n in data["items"]]
    assert any("dossier" in t.lower() or "cree" in t.lower() for t in titles)


def test_mark_read(client: TestClient, auth_headers: dict) -> None:
    client.post(
        "/api/v1/cases",
        json={"first_name": "Read", "last_name": "Test", "source": "manual"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/notifications", headers=auth_headers)
    items = resp.json()["items"]
    if items:
        notif_id = items[0]["id"]
        resp = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=auth_headers)
        assert resp.status_code == 204


def test_mark_all_read(client: TestClient, auth_headers: dict) -> None:
    resp = client.patch("/api/v1/notifications/read-all", headers=auth_headers)
    assert resp.status_code == 204
    resp = client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert resp.json()["count"] == 0
