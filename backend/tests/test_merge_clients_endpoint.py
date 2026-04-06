"""HTTP-level tests for the client merge endpoint via TestClient."""

from fastapi.testclient import TestClient


def _make_client(client: TestClient, auth_headers: dict, first: str, last: str, **kw) -> int:
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": first, "last_name": last, **kw},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_merge_returns_200(client: TestClient, auth_headers: dict) -> None:
    """POST /clients/merge returns 200 with valid payload."""
    keep_id = _make_client(client, auth_headers, "MergeA", "Test")
    merge_id = _make_client(client, auth_headers, "MergeB", "Test")
    resp = client.post(
        "/api/v1/clients/merge",
        json={"keep_id": keep_id, "merge_id": merge_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["kept_client"]["id"] == keep_id
    assert data["merged_client_deleted"] is True


def test_merge_requires_auth(client: TestClient) -> None:
    """POST /clients/merge without auth returns 401."""
    resp = client.post(
        "/api/v1/clients/merge",
        json={"keep_id": 1, "merge_id": 2},
    )
    assert resp.status_code == 401


def test_merge_same_client_400(client: TestClient, auth_headers: dict) -> None:
    """Merging a client into itself returns 400."""
    cid = _make_client(client, auth_headers, "Self", "Merge")
    resp = client.post(
        "/api/v1/clients/merge",
        json={"keep_id": cid, "merge_id": cid},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_merge_missing_client_404(client: TestClient, auth_headers: dict) -> None:
    """Merging with a non-existent client returns 404."""
    keep_id = _make_client(client, auth_headers, "Keep", "Only")
    resp = client.post(
        "/api/v1/clients/merge",
        json={"keep_id": keep_id, "merge_id": 999999},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_merge_transfers_fields(client: TestClient, auth_headers: dict) -> None:
    """Merge fills empty phone on kept client from merged client."""
    keep_id = _make_client(client, auth_headers, "KeepF", "NoPhone")
    merge_id = _make_client(client, auth_headers, "MergeF", "HasPhone", phone="0698765432")
    resp = client.post(
        "/api/v1/clients/merge",
        json={"keep_id": keep_id, "merge_id": merge_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "phone" in data["fields_filled"]
    assert data["kept_client"]["phone"] == "0698765432"
