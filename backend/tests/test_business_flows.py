"""Integration tests for critical business flows: Devis->Facture, PEC, Client lifecycle."""

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LIGNES = [
    {"designation": "Monture Ray-Ban", "quantite": 1, "prix_unitaire_ht": 120.0, "taux_tva": 20.0},
    {"designation": "Verres progressifs", "quantite": 2, "prix_unitaire_ht": 85.0, "taux_tva": 20.0},
]


def _create_case(client: TestClient, headers: dict) -> int:
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Flow", "last_name": "Test", "source": "manual"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_signed_devis(client: TestClient, headers: dict, case_id: int) -> int:
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 50.0, "part_mutuelle": 100.0, "lignes": LIGNES},
        headers=headers,
    )
    assert resp.status_code == 201
    devis_id = resp.json()["id"]
    # brouillon -> envoye -> signe
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "envoye"}, headers=headers)
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "signe"}, headers=headers)
    return devis_id


def _setup_pec(client: TestClient, headers: dict) -> tuple[int, int]:
    resp = client.post(
        "/api/v1/payer-organizations",
        json={"name": "MGEN-Flow", "type": "mutuelle", "code": "MGENF01"},
        headers=headers,
    )
    assert resp.status_code == 201
    org_id = resp.json()["id"]
    case_id = _create_case(client, headers)
    return org_id, case_id


# ===========================================================================
# Devis -> Facture flow (5 tests)
# ===========================================================================


def test_devis_sign_convert_to_facture(client: TestClient, auth_headers: dict) -> None:
    """1. Create devis -> sign -> convert to facture -> verify facture exists."""
    case_id = _create_case(client, auth_headers)
    devis_id = _create_signed_devis(client, auth_headers, case_id)

    # Convert to facture
    resp = client.post(
        "/api/v1/factures",
        json={"devis_id": devis_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    facture = resp.json()
    assert facture["devis_id"] == devis_id
    assert facture["numero"]  # Has a numero (format may vary: F-YYYY-NNNN)

    # Verify facture exists via list
    resp = client.get("/api/v1/factures", headers=auth_headers)
    assert resp.status_code == 200
    facture_ids = [f["id"] for f in resp.json()]
    assert facture["id"] in facture_ids


def test_cannot_convert_unsigned_devis(client: TestClient, auth_headers: dict) -> None:
    """2. Try to convert unsigned devis -> expect error."""
    case_id = _create_case(client, auth_headers)
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0, "lignes": LIGNES},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    devis_id = resp.json()["id"]  # status = brouillon

    resp = client.post(
        "/api/v1/factures",
        json={"devis_id": devis_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    error_data = resp.json()["error"]
    error_text = f"{error_data.get('code', '')} {error_data.get('message', '')}".lower()
    assert "signe" in error_text or "sign" in error_text


def test_convert_devis_twice_is_idempotent(client: TestClient, auth_headers: dict) -> None:
    """3. Convert same devis twice -> expect idempotent (return existing facture)."""
    case_id = _create_case(client, auth_headers)
    devis_id = _create_signed_devis(client, auth_headers, case_id)

    # First conversion
    resp1 = client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    assert resp1.status_code == 201
    facture_id_1 = resp1.json()["id"]

    # Second conversion (devis status is now 'facture')
    resp2 = client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    # Should succeed (idempotent) and return the same facture
    assert resp2.status_code in (200, 201)
    facture_id_2 = resp2.json()["id"]
    assert facture_id_1 == facture_id_2


def test_devis_status_changes_to_facture_after_conversion(client: TestClient, auth_headers: dict) -> None:
    """4. Verify devis status changes to 'facture' after conversion."""
    case_id = _create_case(client, auth_headers)
    devis_id = _create_signed_devis(client, auth_headers, case_id)

    client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)

    # Check devis status
    resp = client.get(f"/api/v1/devis/{devis_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "facture"


def test_facture_has_correct_amounts_from_devis(client: TestClient, auth_headers: dict) -> None:
    """5. Verify facture has correct amounts from devis."""
    case_id = _create_case(client, auth_headers)
    devis_id = _create_signed_devis(client, auth_headers, case_id)

    # Get devis amounts
    devis_resp = client.get(f"/api/v1/devis/{devis_id}", headers=auth_headers)
    devis_data = devis_resp.json()

    # Convert
    resp = client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    facture = resp.json()

    assert facture["montant_ht"] == devis_data["montant_ht"]
    assert facture["montant_ttc"] == devis_data["montant_ttc"]
    assert facture["tva"] == devis_data["tva"]


# ===========================================================================
# PEC flow (4 tests)
# ===========================================================================


def test_pec_accept_with_valid_montant(client: TestClient, auth_headers: dict) -> None:
    """1. Create PEC -> change status to acceptee with valid montant -> verify."""
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 250.0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    pec_id = resp.json()["id"]

    # soumise -> en_attente
    client.patch(
        f"/api/v1/pec/{pec_id}/status",
        json={"status": "en_attente"},
        headers=auth_headers,
    )

    # en_attente -> acceptee with montant_accorde
    resp = client.patch(
        f"/api/v1/pec/{pec_id}/status",
        json={"status": "acceptee", "montant_accorde": 200.0, "comment": "Accord partiel"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "acceptee"
    assert resp.json()["montant_accorde"] == 200.0


def test_pec_montant_accorde_exceeds_demande(client: TestClient, auth_headers: dict) -> None:
    """2. Try PEC with montant_accorde > montant_demande -> expect error."""
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 100.0},
        headers=auth_headers,
    )
    pec_id = resp.json()["id"]

    # soumise -> acceptee with montant_accorde > montant_demande
    resp = client.patch(
        f"/api/v1/pec/{pec_id}/status",
        json={"status": "acceptee", "montant_accorde": 150.0},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    error_data = resp.json()["error"]
    error_text = f"{error_data.get('code', '')} {error_data.get('message', '')}".lower()
    assert "depasse" in error_text


def test_pec_negative_montant_accorde(client: TestClient, auth_headers: dict) -> None:
    """3. Try PEC with negative montant_accorde -> expect error."""
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 100.0},
        headers=auth_headers,
    )
    pec_id = resp.json()["id"]

    resp = client.patch(
        f"/api/v1/pec/{pec_id}/status",
        json={"status": "acceptee", "montant_accorde": -10.0},
        headers=auth_headers,
    )
    # Rejected either by Pydantic validation (422) or business rule (400)
    assert resp.status_code in (400, 422)


def test_pec_invalid_direct_transition_soumise_to_cloturee(client: TestClient, auth_headers: dict) -> None:
    """4. Try PEC status transition from soumise directly to cloturee -> expect error."""
    org_id, case_id = _setup_pec(client, auth_headers)
    resp = client.post(
        "/api/v1/pec",
        json={"case_id": case_id, "organization_id": org_id, "montant_demande": 200.0},
        headers=auth_headers,
    )
    pec_id = resp.json()["id"]

    resp = client.patch(
        f"/api/v1/pec/{pec_id}/status",
        json={"status": "cloturee"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    error_data = resp.json()["error"]
    error_text = f"{error_data.get('code', '')} {error_data.get('message', '')}".lower()
    assert "non autorisee" in error_text or "transition" in error_text


# ===========================================================================
# Client lifecycle (3 tests)
# ===========================================================================


def test_client_soft_delete_and_restore(client: TestClient, auth_headers: dict) -> None:
    """1. Create -> soft delete -> verify not in list -> restore -> verify back in list."""
    # Create client
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Lifecycle", "last_name": "TestDelete", "email": "lifecycle@test.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    client_id = resp.json()["id"]

    # Soft delete
    resp = client.delete(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert resp.status_code == 200

    # Verify not in list (default excludes deleted)
    resp = client.get("/api/v1/clients?q=TestDelete", headers=auth_headers)
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()["items"]]
    assert client_id not in ids

    # Verify also not found by direct GET
    resp = client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert resp.status_code == 404

    # Restore
    resp = client.post(f"/api/v1/clients/{client_id}/restore", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == client_id

    # Verify back in list
    resp = client.get("/api/v1/clients?q=TestDelete", headers=auth_headers)
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()["items"]]
    assert client_id in ids


def test_delete_client_create_same_email_restore_conflict(client: TestClient, auth_headers: dict) -> None:
    """2. Delete client -> create new with same email -> try restore deleted -> expect conflict or success
    depending on business rules (email uniqueness constraint)."""
    # Create first client
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Original", "last_name": "Email", "email": "conflict@test.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    original_id = resp.json()["id"]

    # Soft delete first client
    resp = client.delete(f"/api/v1/clients/{original_id}", headers=auth_headers)
    assert resp.status_code == 200

    # Create second client with same email
    resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Second", "last_name": "Email", "email": "conflict@test.com"},
        headers=auth_headers,
    )
    # Depending on email uniqueness constraints, this may or may not succeed
    # If it succeeds, restoring the original should either fail or handle gracefully
    if resp.status_code == 201:
        second_id = resp.json()["id"]
        # Try to restore original -- should still work (soft delete uses deleted_at, not email uniqueness)
        resp = client.post(f"/api/v1/clients/{original_id}/restore", headers=auth_headers)
        # Accept either success (both coexist) or conflict error
        assert resp.status_code in (200, 400, 409)
    else:
        # Email uniqueness constraint prevents creation -- that's also valid behavior
        assert resp.status_code in (400, 409, 422)


def test_delete_client_cases_still_accessible(client: TestClient, auth_headers: dict) -> None:
    """3. Delete client -> verify associated cases still accessible (orphan protection)."""
    # Create a case (which also creates a customer)
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Orphan", "last_name": "Protection", "source": "manual"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    case_id = resp.json()["id"]
    customer_id = resp.json().get("customer_id")

    # Get the case to find the customer
    resp = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
    assert resp.status_code == 200

    # If we have the customer_id, delete them
    if customer_id:
        resp = client.delete(f"/api/v1/clients/{customer_id}", headers=auth_headers)
        assert resp.status_code == 200

        # Case should still be accessible (orphan protection via FK, not cascade delete)
        resp = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == case_id
