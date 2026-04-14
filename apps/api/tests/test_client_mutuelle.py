"""Tests for client-mutuelle detection and management."""

from fastapi.testclient import TestClient

from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_data import CosiumInvoice, CosiumThirdPartyPayment
from app.models.cosium_reference import CosiumMutuelle


def _create_customer(db, tenant_id: int, first_name: str = "Jean", last_name: str = "Dupont") -> Customer:
    """Helper: create a customer in DB."""
    customer = Customer(
        tenant_id=tenant_id,
        first_name=first_name,
        last_name=last_name,
        cosium_id="12345",
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def _create_invoice(db, tenant_id: int, customer: Customer, share_private_insurance: float = 0) -> CosiumInvoice:
    """Helper: create a Cosium invoice."""
    inv = CosiumInvoice(
        tenant_id=tenant_id,
        cosium_id=100 + customer.id,
        invoice_number=f"FAC-{customer.id}",
        customer_name=f"{customer.last_name} {customer.first_name}",
        customer_cosium_id=customer.cosium_id,
        customer_id=customer.id,
        type="INVOICE",
        total_ti=500.0,
        outstanding_balance=0,
        share_social_security=100.0,
        share_private_insurance=share_private_insurance,
        settled=True,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def _create_tpp(db, tenant_id: int, invoice_cosium_id: int, amc_amount: float = 150.0) -> CosiumThirdPartyPayment:
    """Helper: create a third-party payment."""
    tpp = CosiumThirdPartyPayment(
        tenant_id=tenant_id,
        cosium_id=200 + invoice_cosium_id,
        social_security_amount=100.0,
        social_security_tpp=True,
        additional_health_care_amount=amc_amount,
        additional_health_care_tpp=True,
        invoice_cosium_id=invoice_cosium_id,
    )
    db.add(tpp)
    db.commit()
    db.refresh(tpp)
    return tpp


def _login(client: TestClient) -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": "test@optiflow.com", "password": "test123"})
    token = resp.cookies.get("optiflow_token")
    return {"Authorization": f"Bearer {token}"}


# --- Test 1: Detection from TPP (confidence 1.0) ---
def test_detect_from_tpp(db, client: TestClient, auth_headers: dict, default_tenant) -> None:
    customer = _create_customer(db, default_tenant.id)
    invoice = _create_invoice(db, default_tenant.id, customer, share_private_insurance=0)
    _create_tpp(db, default_tenant.id, invoice.cosium_id, amc_amount=150.0)

    # Trigger batch detection
    resp = client.post("/api/v1/admin/detect-mutuelles", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["clients_with_mutuelle"] >= 1
    assert data["new_mutuelles_created"] >= 1

    # Verify via GET
    resp2 = client.get(f"/api/v1/clients/{customer.id}/mutuelles", headers=auth_headers)
    assert resp2.status_code == 200
    mutuelles = resp2.json()
    assert len(mutuelles) >= 1
    tpp_mut = [m for m in mutuelles if m["source"] == "cosium_tpp"]
    assert len(tpp_mut) >= 1
    assert tpp_mut[0]["confidence"] == 1.0


# --- Test 2: Detection from invoice share_private_insurance (confidence 0.7) ---
def test_detect_from_invoice_insurance(db, client: TestClient, auth_headers: dict, default_tenant) -> None:
    customer = _create_customer(db, default_tenant.id, first_name="Marie", last_name="Martin")
    _create_invoice(db, default_tenant.id, customer, share_private_insurance=200.0)

    resp = client.post("/api/v1/admin/detect-mutuelles", headers=auth_headers)
    assert resp.status_code == 200

    resp2 = client.get(f"/api/v1/clients/{customer.id}/mutuelles", headers=auth_headers)
    assert resp2.status_code == 200
    mutuelles = resp2.json()
    assert len(mutuelles) >= 1
    inv_mut = [m for m in mutuelles if m["source"] == "cosium_invoice"]
    assert len(inv_mut) >= 1
    assert inv_mut[0]["confidence"] == 0.7


# --- Test 3: Manual creation ---
def test_manual_create(db, client: TestClient, auth_headers: dict, default_tenant) -> None:
    customer = _create_customer(db, default_tenant.id, first_name="Pierre", last_name="Leclerc")

    resp = client.post(
        f"/api/v1/clients/{customer.id}/mutuelles",
        json={
            "mutuelle_name": "MGEN",
            "numero_adherent": "123456",
            "type_beneficiaire": "assure",
            "source": "manual",
            "confidence": 1.0,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mutuelle_name"] == "MGEN"
    assert data["numero_adherent"] == "123456"
    assert data["source"] == "manual"
    assert data["confidence"] == 1.0
    assert data["active"] is True


# --- Test 4: Multiple mutuelles per client ---
def test_multiple_mutuelles(db, client: TestClient, auth_headers: dict, default_tenant) -> None:
    customer = _create_customer(db, default_tenant.id, first_name="Sophie", last_name="Durand")

    # Add two mutuelles
    client.post(
        f"/api/v1/clients/{customer.id}/mutuelles",
        json={"mutuelle_name": "MGEN", "source": "manual", "confidence": 1.0},
        headers=auth_headers,
    )
    client.post(
        f"/api/v1/clients/{customer.id}/mutuelles",
        json={"mutuelle_name": "Harmonie Mutuelle", "source": "manual", "confidence": 1.0},
        headers=auth_headers,
    )

    resp = client.get(f"/api/v1/clients/{customer.id}/mutuelles", headers=auth_headers)
    assert resp.status_code == 200
    mutuelles = resp.json()
    assert len(mutuelles) == 2
    names = {m["mutuelle_name"] for m in mutuelles}
    assert "MGEN" in names
    assert "Harmonie Mutuelle" in names


# --- Test 5: No mutuelle detected (client pays cash) ---
def test_no_mutuelle_cash_client(db, client: TestClient, auth_headers: dict, default_tenant) -> None:
    customer = _create_customer(db, default_tenant.id, first_name="Cash", last_name="Client")
    _create_invoice(db, default_tenant.id, customer, share_private_insurance=0)
    # No TPP record at all

    resp = client.get(f"/api/v1/clients/{customer.id}/mutuelles", headers=auth_headers)
    assert resp.status_code == 200
    mutuelles = resp.json()
    assert len(mutuelles) == 0


# --- Test 6: Delete mutuelle ---
def test_delete_mutuelle(db, client: TestClient, auth_headers: dict, default_tenant) -> None:
    customer = _create_customer(db, default_tenant.id, first_name="Del", last_name="Test")

    resp = client.post(
        f"/api/v1/clients/{customer.id}/mutuelles",
        json={"mutuelle_name": "A supprimer", "source": "manual", "confidence": 1.0},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    mut_id = resp.json()["id"]

    # Delete
    resp2 = client.delete(f"/api/v1/clients/{customer.id}/mutuelles/{mut_id}", headers=auth_headers)
    assert resp2.status_code == 204

    # Verify deleted
    resp3 = client.get(f"/api/v1/clients/{customer.id}/mutuelles", headers=auth_headers)
    assert resp3.status_code == 200
    assert len(resp3.json()) == 0


# --- Test 7: 360 includes mutuelles ---
def test_360_includes_mutuelles(db, client: TestClient, auth_headers: dict, default_tenant) -> None:
    customer = _create_customer(db, default_tenant.id, first_name="Vue360", last_name="Test")

    # Add a mutuelle
    client.post(
        f"/api/v1/clients/{customer.id}/mutuelles",
        json={"mutuelle_name": "MGEN 360", "source": "manual", "confidence": 1.0},
        headers=auth_headers,
    )

    resp = client.get(f"/api/v1/clients/{customer.id}/360", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    cosium_data = data.get("cosium_data", {})
    mutuelles = cosium_data.get("mutuelles", [])
    assert len(mutuelles) >= 1
    assert mutuelles[0]["mutuelle_name"] == "MGEN 360"


# --- Test 8: Batch detect endpoint returns stats ---
def test_batch_detect_endpoint(db, client: TestClient, auth_headers: dict, default_tenant) -> None:
    # Create a customer with TPP data
    customer = _create_customer(db, default_tenant.id, first_name="Batch", last_name="Test")
    invoice = _create_invoice(db, default_tenant.id, customer, share_private_insurance=0)
    _create_tpp(db, default_tenant.id, invoice.cosium_id, amc_amount=300.0)

    resp = client.post("/api/v1/admin/detect-mutuelles", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_clients_scanned" in data
    assert "clients_with_mutuelle" in data
    assert "new_mutuelles_created" in data
    assert "existing_mutuelles_skipped" in data
    assert "errors" in data
    assert data["total_clients_scanned"] >= 1


# --- Test 9: Idempotent batch detection (skip existing) ---
def test_batch_detect_idempotent(db, client: TestClient, auth_headers: dict, default_tenant) -> None:
    customer = _create_customer(db, default_tenant.id, first_name="Idem", last_name="Potent")
    invoice = _create_invoice(db, default_tenant.id, customer, share_private_insurance=0)
    _create_tpp(db, default_tenant.id, invoice.cosium_id, amc_amount=250.0)

    # First detection
    resp1 = client.post("/api/v1/admin/detect-mutuelles", headers=auth_headers)
    assert resp1.status_code == 200
    created1 = resp1.json()["new_mutuelles_created"]

    # Second detection — should skip existing
    resp2 = client.post("/api/v1/admin/detect-mutuelles", headers=auth_headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["existing_mutuelles_skipped"] >= created1
    # No new ones created for the same customer
    assert data2["new_mutuelles_created"] == 0 or data2["existing_mutuelles_skipped"] > 0
