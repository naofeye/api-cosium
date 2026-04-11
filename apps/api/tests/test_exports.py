from fastapi.testclient import TestClient


def _seed_client(client: TestClient, headers: dict) -> int:
    resp = client.post("/api/v1/clients", json={"first_name": "Export", "last_name": "Test", "email": "exp@test.com"}, headers=headers)
    return resp.json()["id"]


def test_export_clients_csv(client: TestClient, auth_headers: dict) -> None:
    _seed_client(client, auth_headers)
    resp = client.get("/api/v1/exports/clients?format=csv", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.content.decode("utf-8-sig")
    assert "Prenom" in content
    assert "Nom" in content
    assert "Export" in content


def test_export_clients_xlsx(client: TestClient, auth_headers: dict) -> None:
    _seed_client(client, auth_headers)
    resp = client.get("/api/v1/exports/clients?format=xlsx", headers=auth_headers)
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
    assert len(resp.content) > 100


def test_export_factures_csv(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/exports/factures?format=csv", headers=auth_headers)
    assert resp.status_code == 200
    content = resp.content.decode("utf-8-sig")
    assert "Numero" in content


def test_export_devis_csv(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/exports/devis?format=csv", headers=auth_headers)
    assert resp.status_code == 200


def test_export_paiements_csv(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/exports/paiements?format=csv", headers=auth_headers)
    assert resp.status_code == 200


def test_export_audit_logs_csv(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/exports/audit_logs?format=csv", headers=auth_headers)
    assert resp.status_code == 200


def test_export_unknown_entity(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/exports/nonexistent?format=csv", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.content) < 10  # Empty
