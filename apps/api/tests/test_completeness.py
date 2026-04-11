from fastapi.testclient import TestClient


def test_completeness(client: TestClient, auth_headers: dict) -> None:
    # Create a case first
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Test", "last_name": "Complete", "source": "manual"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    case_id = resp.json()["id"]

    # Get completeness
    resp = client.get(f"/api/v1/cases/{case_id}/completeness", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == case_id
    assert data["total_required"] >= 1
    assert data["total_missing"] == data["total_required"]
    assert len(data["items"]) >= 1


def test_completeness_not_found(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/cases/99999/completeness", headers=auth_headers)
    assert resp.status_code == 404
