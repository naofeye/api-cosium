from fastapi.testclient import TestClient


def _setup_pec(client: TestClient, headers: dict) -> tuple[int, int]:
    """Create org + case, return (org_id, case_id)."""
    resp = client.post(
        "/api/v1/payer-organizations",
        json={"name": "MGEN", "type": "mutuelle", "code": "MGEN001"},
        headers=headers,
    )
    assert resp.status_code == 201
    org_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "PEC", "last_name": "Test", "source": "manual"},
        headers=headers,
    )
    case_id = resp.json()["id"]
    return org_id, case_id


def test_create_organization(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        "/api/v1/payer-organizations",
        json={"name": "CPAM Paris", "type": "secu", "code": "CPAM75"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "secu"


def test_list_organizations(client: TestClient, auth_headers: dict) -> None:
    client.post(
        "/api/v1/payer-organizations",
        json={"name": "TestOrg", "type": "mutuelle", "code": "TO001"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/payer-organizations", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_create_pec(client: TestClient, auth_headers: dict) -> None:
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 250.0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "soumise"
    assert data["montant_demande"] == 250.0
    assert data["organization_name"] is not None


def test_pec_workflow(client: TestClient, auth_headers: dict) -> None:
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 300.0},
        headers=auth_headers,
    )
    pec_id = resp.json()["id"]

    # soumise -> en_attente
    resp = client.patch(
        f"/api/v1/pec/{pec_id}/status",
        json={"status": "en_attente", "comment": "Dossier en cours de traitement"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "en_attente"

    # en_attente -> acceptee
    resp = client.patch(
        f"/api/v1/pec/{pec_id}/status",
        json={"status": "acceptee", "montant_accorde": 280.0, "comment": "Accord partiel"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "acceptee"
    assert resp.json()["montant_accorde"] == 280.0

    # acceptee -> cloturee
    resp = client.patch(
        f"/api/v1/pec/{pec_id}/status",
        json={"status": "cloturee"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cloturee"


def test_invalid_pec_transition(client: TestClient, auth_headers: dict) -> None:
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 100.0},
        headers=auth_headers,
    )
    pec_id = resp.json()["id"]

    # soumise -> cloturee (interdit)
    resp = client.patch(
        f"/api/v1/pec/{pec_id}/status",
        json={"status": "cloturee"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_pec_history(client: TestClient, auth_headers: dict) -> None:
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 150.0},
        headers=auth_headers,
    )
    pec_id = resp.json()["id"]

    client.patch(f"/api/v1/pec/{pec_id}/status",
                 json={"status": "en_attente", "comment": "Reception du dossier"}, headers=auth_headers)

    resp = client.get(f"/api/v1/pec/{pec_id}/history", headers=auth_headers)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 2  # soumise + en_attente


def test_relance(client: TestClient, auth_headers: dict) -> None:
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 200.0},
        headers=auth_headers,
    )
    pec_id = resp.json()["id"]

    resp = client.post(
        f"/api/v1/pec/{pec_id}/relances",
        json={"type": "email", "contenu": "Relance pour dossier en attente"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "email"

    resp = client.get(f"/api/v1/pec/{pec_id}/relances", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_pec_detail(client: TestClient, auth_headers: dict) -> None:
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 100.0},
        headers=auth_headers,
    )
    pec_id = resp.json()["id"]
    resp = client.get(f"/api/v1/pec/{pec_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data
    assert len(data["history"]) >= 1
