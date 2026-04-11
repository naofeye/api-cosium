from fastapi.testclient import TestClient


def test_list_templates(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/reminders/templates", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_create_template(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        "/api/v1/reminders/templates",
        json={"name": "Test template", "channel": "email", "payer_type": "client",
              "subject": "Test", "body": "Bonjour {{client_name}}"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test template"


def test_create_plan(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        "/api/v1/reminders/plans",
        json={"name": "Plan client standard", "payer_type": "client",
              "rules_json": {"min_days_overdue": 7, "min_amount": 10, "max_reminders": 3},
              "channel_sequence": ["email", "courrier", "telephone"],
              "interval_days": 7},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Plan client standard"


def test_list_plans(client: TestClient, auth_headers: dict) -> None:
    client.post(
        "/api/v1/reminders/plans",
        json={"name": "Plan test", "payer_type": "client"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/reminders/plans", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_overdue(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/reminders/overdue?min_days=0", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_stats(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/reminders/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_overdue_amount" in data
    assert "overdue_by_age" in data
    assert "recovery_rate" in data


def test_create_manual_reminder(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        "/api/v1/reminders",
        json={"target_type": "client", "target_id": 1, "channel": "telephone",
              "content": "Appel pour relance paiement"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["channel"] == "telephone"
    assert resp.json()["status"] == "scheduled"


def test_list_reminders(client: TestClient, auth_headers: dict) -> None:
    client.post(
        "/api/v1/reminders",
        json={"target_type": "client", "target_id": 1, "channel": "email",
              "content": "Test relance"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/reminders", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_execute_plan(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        "/api/v1/reminders/plans",
        json={"name": "Exec plan", "payer_type": "client",
              "rules_json": {"min_days_overdue": 0, "min_amount": 0, "max_reminders": 5},
              "channel_sequence": ["email"]},
        headers=auth_headers,
    )
    plan_id = resp.json()["id"]
    resp = client.post(f"/api/v1/reminders/plans/{plan_id}/execute", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
