import json
from fastapi.testclient import TestClient


def _seed_client(client: TestClient, headers: dict) -> int:
    resp = client.post("/api/v1/clients",
                       json={"first_name": "RGPD", "last_name": "Dupont", "email": "rgpd@dupont.fr",
                             "phone": "0612345678"},
                       headers=headers)
    return resp.json()["id"]


def test_gdpr_get_data_all_sections(client: TestClient, auth_headers: dict) -> None:
    cid = _seed_client(client, auth_headers)
    resp = client.get(f"/api/v1/gdpr/clients/{cid}/data", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "informations_personnelles" in data
    assert data["informations_personnelles"]["prenom"] == "RGPD"
    assert data["informations_personnelles"]["nom"] == "Dupont"
    assert data["informations_personnelles"]["email"] == "rgpd@dupont.fr"
    assert "dossiers" in data
    assert "consentements_marketing" in data
    assert "interactions" in data


def test_gdpr_export_json(client: TestClient, auth_headers: dict) -> None:
    cid = _seed_client(client, auth_headers)
    resp = client.post(f"/api/v1/gdpr/clients/{cid}/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    data = json.loads(resp.content)
    assert "informations_personnelles" in data


def test_gdpr_anonymize(client: TestClient, auth_headers: dict) -> None:
    cid = _seed_client(client, auth_headers)
    resp = client.post(f"/api/v1/gdpr/clients/{cid}/anonymize", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "anonymized"

    # Verify personal data is gone
    resp = client.get(f"/api/v1/gdpr/clients/{cid}/data", headers=auth_headers)
    perso = resp.json()["informations_personnelles"]
    assert perso["prenom"] == "ANONYMISE"
    assert perso["email"] is None
    assert perso["telephone"] is None


def test_gdpr_anonymize_preserves_financials(client: TestClient, auth_headers: dict) -> None:
    """After anonymization, financial data (dossiers, factures) should still be accessible."""
    cid = _seed_client(client, auth_headers)
    client.post(f"/api/v1/gdpr/clients/{cid}/anonymize", headers=auth_headers)
    resp = client.get(f"/api/v1/gdpr/clients/{cid}/data", headers=auth_headers)
    data = resp.json()
    # Structure still present even if empty
    assert "dossiers" in data
    assert "consentements_marketing" in data


def test_gdpr_audit_trail(client: TestClient, auth_headers: dict) -> None:
    """GDPR operations must be logged in audit trail."""
    cid = _seed_client(client, auth_headers)
    # Access
    client.get(f"/api/v1/gdpr/clients/{cid}/data", headers=auth_headers)
    # Export
    client.post(f"/api/v1/gdpr/clients/{cid}/export", headers=auth_headers)
    # Anonymize
    client.post(f"/api/v1/gdpr/clients/{cid}/anonymize", headers=auth_headers)

    # Check audit logs
    resp = client.get("/api/v1/audit-logs?entity_type=gdpr_access", headers=auth_headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?entity_type=gdpr_export", headers=auth_headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit-logs?entity_type=gdpr_anonymize", headers=auth_headers)
    assert resp.status_code == 200


def test_gdpr_not_found(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/gdpr/clients/99999/data", headers=auth_headers)
    assert resp.status_code == 404
