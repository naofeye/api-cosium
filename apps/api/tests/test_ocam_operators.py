"""Tests for OCAM operators (mutuelles/complementaires)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Tenant
from app.services import ocam_operator_service


def test_list_ocam_operators_returns_seeded_data(
    client: TestClient, auth_headers: dict, db: Session
) -> None:
    """After seeding, list should return default operators."""
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    ocam_operator_service.seed_default_operators(db, tenant_id=tenant.id)

    resp = client.get("/api/v1/ocam-operators", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 4
    names = [op["name"] for op in data]
    assert "Almerys" in names
    assert "SP Sante" in names


def test_create_ocam_operator(
    client: TestClient, auth_headers: dict
) -> None:
    """Creating a new OCAM operator should return 201 with the created data."""
    payload = {
        "name": "Test Mutuelle",
        "code": "TEST_MUT",
        "portal_url": "https://test-mutuelle.fr",
        "required_fields": ["nom", "prenom", "numero_secu"],
        "required_documents": ["ordonnance"],
        "specific_rules": {"max_amount": 5000},
        "active": True,
    }
    resp = client.post("/api/v1/ocam-operators", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Mutuelle"
    assert data["code"] == "TEST_MUT"
    assert "ordonnance" in data["required_documents"]
    assert data["specific_rules"]["max_amount"] == 5000


def test_seed_default_operators(db: Session) -> None:
    """seed_default_operators should create 4 operators on first call and 0 on second."""
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    count = ocam_operator_service.seed_default_operators(db, tenant_id=tenant.id)
    assert count == 4

    # Second call should return 0 (already seeded)
    count2 = ocam_operator_service.seed_default_operators(db, tenant_id=tenant.id)
    assert count2 == 0


def test_create_ocam_operator_forbidden_for_viewer(
    client: TestClient, db: Session
) -> None:
    """Un viewer ne doit PAS pouvoir creer un operateur OCAM (RBAC)."""
    from app.models import Tenant, TenantUser, User
    from app.security import hash_password

    viewer = User(
        email="viewer-ocam@test.local",
        password_hash=hash_password("Viewer123"),
        role="viewer",
        is_active=True,
    )
    db.add(viewer)
    db.flush()
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    db.add(TenantUser(user_id=viewer.id, tenant_id=tenant.id, role="viewer"))
    db.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer-ocam@test.local", "password": "Viewer123"},
    )
    token = login.cookies.get("optiflow_token")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "name": "Forbidden Mutuelle",
        "code": "FORBID",
        "required_fields": [],
        "required_documents": [],
        "specific_rules": {},
        "active": True,
    }
    resp = client.post("/api/v1/ocam-operators", json=payload, headers=headers)
    assert resp.status_code == 403


def test_pec_operator_specific_rules(
    client: TestClient, auth_headers: dict, db: Session
) -> None:
    """An operator with specific_rules should expose those rules in the response."""
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    ocam_operator_service.seed_default_operators(db, tenant_id=tenant.id)

    resp = client.get("/api/v1/ocam-operators", headers=auth_headers)
    assert resp.status_code == 200
    operators = resp.json()

    # SP Sante requires prescriber RPPS
    sp_sante = next((op for op in operators if op["code"] == "SP_SANTE"), None)
    assert sp_sante is not None
    assert sp_sante["specific_rules"]["requires_prescriber_rpps"] is True
    assert "attestation_mutuelle" in sp_sante["required_documents"]

    # Almerys does not require prescriber RPPS
    almerys = next((op for op in operators if op["code"] == "ALMERYS"), None)
    assert almerys is not None
    assert almerys["specific_rules"].get("requires_prescriber_rpps") is False
