"""Integration tests for critical API endpoints.

Covers:
- GET  /api/v1/clients              — list clients (paginated)
- POST /api/v1/clients              — create client (validates input)
- GET  /api/v1/cases                — list cases
- GET  /api/v1/dashboard/summary    — dashboard KPIs
- GET  /api/v1/notifications        — list notifications
- POST /api/v1/push/subscribe       — subscribe to Web Push
- DELETE /api/v1/push/unsubscribe   — unsubscribe from Web Push

Each endpoint is tested for:
  - 401 without authentication
  - 200/201/204 with valid auth + data
  - 422 with invalid/missing input where applicable
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# GET /api/v1/clients
# ---------------------------------------------------------------------------


class TestListClients:
    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/clients")
        assert resp.status_code == 401

    def test_returns_empty_list_when_no_clients(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/clients", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 0

    def test_returns_created_client(self, client: TestClient, auth_headers: dict) -> None:
        client.post(
            "/api/v1/clients",
            json={"first_name": "ListTest", "last_name": "Dupont"},
            headers=auth_headers,
        )
        resp = client.get("/api/v1/clients", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        names = [c["last_name"] for c in data["items"]]
        assert "Dupont" in names

    def test_pagination_params_respected(self, client: TestClient, auth_headers: dict) -> None:
        # Create 3 clients
        for i in range(3):
            client.post(
                "/api/v1/clients",
                json={"first_name": f"Page{i}", "last_name": "Paginee"},
                headers=auth_headers,
            )
        resp = client.get("/api/v1/clients?page=1&page_size=2", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) <= 2

    def test_search_by_query(self, client: TestClient, auth_headers: dict) -> None:
        client.post(
            "/api/v1/clients",
            json={"first_name": "Unique", "last_name": "XYZ9999"},
            headers=auth_headers,
        )
        resp = client.get("/api/v1/clients?q=XYZ9999", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["last_name"] == "XYZ9999"

    def test_page_size_too_large_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/clients?page_size=999", headers=auth_headers)
        assert resp.status_code == 422

    def test_page_zero_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/clients?page=0", headers=auth_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/clients
# ---------------------------------------------------------------------------


class TestCreateClient:
    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/clients",
            json={"first_name": "Alice", "last_name": "Martin"},
        )
        assert resp.status_code == 401

    def test_creates_client_with_minimal_fields(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/clients",
            json={"first_name": "Alice", "last_name": "Martin"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["first_name"] == "Alice"
        assert data["last_name"] == "Martin"
        assert "id" in data

    def test_creates_client_with_all_fields(self, client: TestClient, auth_headers: dict) -> None:
        payload = {
            "first_name": "Bernard",
            "last_name": "Leclerc",
            "email": "bernard@example.com",
            "phone": "0612345678",
            "address": "12 rue de la Paix",
            "city": "Paris",
            "postal_code": "75001",
            "notes": "Client VIP",
        }
        resp = client.post("/api/v1/clients", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "bernard@example.com"
        assert data["city"] == "Paris"
        assert data["postal_code"] == "75001"

    def test_missing_first_name_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/clients",
            json={"last_name": "Martin"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_missing_last_name_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/clients",
            json={"first_name": "Alice"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_empty_first_name_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/clients",
            json={"first_name": "", "last_name": "Martin"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_invalid_email_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/clients",
            json={"first_name": "Alice", "last_name": "Martin", "email": "not-an-email"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_first_name_too_long_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/clients",
            json={"first_name": "A" * 121, "last_name": "Martin"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_response_contains_expected_fields(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/clients",
            json={"first_name": "Chantal", "last_name": "Rousseau"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        required_fields = {"id", "first_name", "last_name"}
        assert required_fields.issubset(data.keys())


# ---------------------------------------------------------------------------
# GET /api/v1/cases
# ---------------------------------------------------------------------------


class TestListCases:
    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/cases")
        assert resp.status_code == 401

    def test_returns_list(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/cases", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_created_case_appears_in_list(self, client: TestClient, auth_headers: dict) -> None:
        client.post(
            "/api/v1/cases",
            json={"first_name": "Jean", "last_name": "Valjean", "source": "manual"},
            headers=auth_headers,
        )
        resp = client.get("/api/v1/cases", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        names = [c["customer_name"] for c in data]
        assert any("Valjean" in name for name in names)

    def test_case_response_fields(self, client: TestClient, auth_headers: dict) -> None:
        client.post(
            "/api/v1/cases",
            json={"first_name": "Marie", "last_name": "Curie"},
            headers=auth_headers,
        )
        resp = client.get("/api/v1/cases", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1
        case = items[0]
        required_fields = {"id", "customer_name", "status", "source"}
        assert required_fields.issubset(case.keys())

    def test_pagination_page_size(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/cases?page=1&page_size=5", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    def test_invalid_page_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/cases?page=0", headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_page_size_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/cases?page_size=200", headers=auth_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/dashboard/summary
# ---------------------------------------------------------------------------


class TestDashboardSummary:
    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 401

    def test_returns_kpis(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        expected_keys = {"cases_count", "documents_count", "alerts_count", "total_due", "total_paid", "remaining"}
        assert expected_keys.issubset(data.keys())

    def test_kpi_values_are_numeric(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["cases_count"], int)
        assert isinstance(data["documents_count"], int)
        assert isinstance(data["alerts_count"], int)
        assert isinstance(data["total_due"], (int, float))
        assert isinstance(data["total_paid"], (int, float))
        assert isinstance(data["remaining"], (int, float))

    def test_kpis_reflect_created_case(self, client: TestClient, auth_headers: dict) -> None:
        before = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
        client.post(
            "/api/v1/cases",
            json={"first_name": "Dashboard", "last_name": "Test"},
            headers=auth_headers,
        )
        after = client.get("/api/v1/dashboard/summary", headers=auth_headers).json()
        assert after["cases_count"] >= before["cases_count"] + 1


# ---------------------------------------------------------------------------
# GET /api/v1/notifications
# ---------------------------------------------------------------------------


class TestListNotifications:
    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/api/v1/notifications")
        assert resp.status_code == 401

    def test_returns_paginated_response(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/notifications", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "unread_count" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["unread_count"], int)

    def test_unread_only_filter(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/notifications?unread_only=true", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["items"], list)
        for item in data["items"]:
            assert item["is_read"] is False

    def test_pagination_params(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/notifications?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 10

    def test_invalid_page_size_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.get("/api/v1/notifications?page_size=200", headers=auth_headers)
        assert resp.status_code == 422

    def test_notification_fields_when_present(self, client: TestClient, auth_headers: dict) -> None:
        # Create a case which should trigger a notification
        client.post(
            "/api/v1/cases",
            json={"first_name": "Notif", "last_name": "Check"},
            headers=auth_headers,
        )
        resp = client.get("/api/v1/notifications", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        if items:
            notif = items[0]
            required_fields = {"id", "type", "title", "message", "is_read", "created_at"}
            assert required_fields.issubset(notif.keys())


# ---------------------------------------------------------------------------
# POST /api/v1/push/subscribe
# ---------------------------------------------------------------------------

_PUSH_ENDPOINT = "https://fcm.googleapis.com/fcm/send/fake-device-token-001"
_PUSH_KEYS = {"p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtskv0wPT", "auth": "tBHItJI5svbpez7KI4CCXg"}


class TestPushSubscribe:
    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/push/subscribe",
            json={"endpoint": _PUSH_ENDPOINT, "keys": _PUSH_KEYS},
        )
        assert resp.status_code == 401

    def test_subscribe_with_valid_data(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/push/subscribe",
            json={"endpoint": _PUSH_ENDPOINT, "keys": _PUSH_KEYS},
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_subscribe_idempotent(self, client: TestClient, auth_headers: dict) -> None:
        # Subscribing twice with same endpoint should not raise an error (upsert)
        payload = {"endpoint": _PUSH_ENDPOINT + "-idem", "keys": _PUSH_KEYS}
        resp1 = client.post("/api/v1/push/subscribe", json=payload, headers=auth_headers)
        resp2 = client.post("/api/v1/push/subscribe", json=payload, headers=auth_headers)
        assert resp1.status_code == 204
        assert resp2.status_code == 204

    def test_missing_endpoint_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/push/subscribe",
            json={"keys": _PUSH_KEYS},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_missing_keys_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/push/subscribe",
            json={"endpoint": _PUSH_ENDPOINT},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_missing_p256dh_key_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/push/subscribe",
            json={"endpoint": _PUSH_ENDPOINT, "keys": {"auth": "tBHItJI5"}},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_missing_auth_key_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post(
            "/api/v1/push/subscribe",
            json={"endpoint": _PUSH_ENDPOINT, "keys": {"p256dh": "BNcRdreALRFX"}},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_empty_body_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.post("/api/v1/push/subscribe", json={}, headers=auth_headers)
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/push/unsubscribe
# ---------------------------------------------------------------------------


class TestPushUnsubscribe:
    def test_requires_auth(self, client: TestClient) -> None:
        resp = client.delete(
            "/api/v1/push/unsubscribe",
            json={"endpoint": _PUSH_ENDPOINT},
        )
        assert resp.status_code == 401

    def test_unsubscribe_existing_subscription(self, client: TestClient, auth_headers: dict) -> None:
        endpoint = _PUSH_ENDPOINT + "-unsub"
        # First subscribe
        client.post(
            "/api/v1/push/subscribe",
            json={"endpoint": endpoint, "keys": _PUSH_KEYS},
            headers=auth_headers,
        )
        # Then unsubscribe
        resp = client.delete(
            "/api/v1/push/unsubscribe",
            json={"endpoint": endpoint},
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_unsubscribe_non_existent_is_silent(self, client: TestClient, auth_headers: dict) -> None:
        # Unsubscribing an endpoint that does not exist should still succeed (DELETE is idempotent)
        resp = client.delete(
            "/api/v1/push/unsubscribe",
            json={"endpoint": "https://fcm.example.com/not-registered"},
            headers=auth_headers,
        )
        assert resp.status_code == 204

    def test_missing_endpoint_returns_422(self, client: TestClient, auth_headers: dict) -> None:
        resp = client.delete(
            "/api/v1/push/unsubscribe",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422
