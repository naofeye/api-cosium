from unittest.mock import patch

from fastapi.testclient import TestClient


def _create_client(client: TestClient, headers: dict) -> int:
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Marketing", "last_name": "Test", "email": "mktg@test.com"},
        headers=headers,
    )
    return resp.json()["id"]


def test_grant_consent(client: TestClient, auth_headers: dict) -> None:
    client_id = _create_client(client, auth_headers)
    resp = client.put(
        f"/api/v1/clients/{client_id}/consents/email",
        json={"consented": True, "source": "formulaire"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["consented"] is True
    assert resp.json()["channel"] == "email"


def test_revoke_consent(client: TestClient, auth_headers: dict) -> None:
    client_id = _create_client(client, auth_headers)
    client.put(f"/api/v1/clients/{client_id}/consents/email",
               json={"consented": True}, headers=auth_headers)
    resp = client.put(f"/api/v1/clients/{client_id}/consents/email",
                      json={"consented": False}, headers=auth_headers)
    assert resp.json()["consented"] is False
    assert resp.json()["revoked_at"] is not None


def test_get_consents(client: TestClient, auth_headers: dict) -> None:
    client_id = _create_client(client, auth_headers)
    client.put(f"/api/v1/clients/{client_id}/consents/email",
               json={"consented": True}, headers=auth_headers)
    client.put(f"/api/v1/clients/{client_id}/consents/sms",
               json={"consented": False}, headers=auth_headers)
    resp = client.get(f"/api/v1/clients/{client_id}/consents", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_create_segment(client: TestClient, auth_headers: dict) -> None:
    _create_client(client, auth_headers)
    resp = client.post(
        "/api/v1/marketing/segments",
        json={"name": "Tous clients email", "rules_json": {"has_email": True}},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["member_count"] >= 1


def test_list_segments(client: TestClient, auth_headers: dict) -> None:
    _create_client(client, auth_headers)
    client.post("/api/v1/marketing/segments",
                json={"name": "Test seg", "rules_json": {}}, headers=auth_headers)
    resp = client.get("/api/v1/marketing/segments", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_create_campaign(client: TestClient, auth_headers: dict) -> None:
    _create_client(client, auth_headers)
    resp = client.post("/api/v1/marketing/segments",
                       json={"name": "Camp seg", "rules_json": {"has_email": True}},
                       headers=auth_headers)
    seg_id = resp.json()["id"]
    resp = client.post(
        "/api/v1/marketing/campaigns",
        json={"name": "Promo ete", "segment_id": seg_id, "channel": "email",
              "subject": "Offre speciale", "template": "Bonjour {{client_name}} !"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "draft"


def test_send_campaign_without_consent(client: TestClient, auth_headers: dict) -> None:
    client_id = _create_client(client, auth_headers)
    # No consent granted
    resp = client.post("/api/v1/marketing/segments",
                       json={"name": "No consent seg", "rules_json": {"has_email": True}},
                       headers=auth_headers)
    seg_id = resp.json()["id"]
    resp = client.post("/api/v1/marketing/campaigns",
                       json={"name": "No consent camp", "segment_id": seg_id,
                             "channel": "email", "template": "Test"},
                       headers=auth_headers)
    camp_id = resp.json()["id"]
    resp = client.post(f"/api/v1/marketing/campaigns/{camp_id}/send", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total_sent"] == 0  # No consent = no send


@patch("app.integrations.email_sender.email_sender.send_email", return_value=True)
def test_send_campaign_with_consent(_mock_send, client: TestClient, auth_headers: dict) -> None:
    client_id = _create_client(client, auth_headers)
    client.put(f"/api/v1/clients/{client_id}/consents/email",
               json={"consented": True}, headers=auth_headers)
    resp = client.post("/api/v1/marketing/segments",
                       json={"name": "Consent seg", "rules_json": {"has_email": True}},
                       headers=auth_headers)
    seg_id = resp.json()["id"]
    resp = client.post("/api/v1/marketing/campaigns",
                       json={"name": "Consent camp", "segment_id": seg_id,
                             "channel": "email", "subject": "Test",
                             "template": "Bonjour {{client_name}}"},
                       headers=auth_headers)
    camp_id = resp.json()["id"]
    resp = client.post(f"/api/v1/marketing/campaigns/{camp_id}/send", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total_sent"] >= 1


@patch("app.integrations.email_sender.email_sender.send_email", return_value=True)
def test_campaign_stats(_mock_send, client: TestClient, auth_headers: dict) -> None:
    client_id = _create_client(client, auth_headers)
    client.put(f"/api/v1/clients/{client_id}/consents/email",
               json={"consented": True}, headers=auth_headers)
    resp = client.post("/api/v1/marketing/segments",
                       json={"name": "Stats seg", "rules_json": {"has_email": True}},
                       headers=auth_headers)
    seg_id = resp.json()["id"]
    resp = client.post("/api/v1/marketing/campaigns",
                       json={"name": "Stats camp", "segment_id": seg_id,
                             "channel": "email", "template": "Hello"},
                       headers=auth_headers)
    camp_id = resp.json()["id"]
    client.post(f"/api/v1/marketing/campaigns/{camp_id}/send", headers=auth_headers)
    resp = client.get(f"/api/v1/marketing/campaigns/{camp_id}/stats", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["campaign_id"] == camp_id
