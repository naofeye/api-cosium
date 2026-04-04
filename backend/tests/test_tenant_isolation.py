"""Tests d'isolation multi-tenant : un user ne voit PAS les données d'un autre tenant."""
import pytest
from app.models import Case, Customer, Organization, Tenant, TenantUser, User
from app.security import hash_password


@pytest.fixture(name="two_tenants")
def two_tenants_fixture(db):
    """Crée 2 tenants avec chacun un user et un case."""
    org = db.query(Organization).first()

    # Tenant A (le default 'test-magasin')
    tenant_a = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

    # Tenant B
    tenant_b = Tenant(organization_id=org.id, name="Magasin B", slug="magasin-b")
    db.add(tenant_b)
    db.flush()

    # User A
    user_a = User(email="usera@test.local", password_hash=hash_password("Test1234"), role="admin", is_active=True)
    db.add(user_a)
    db.flush()
    db.add(TenantUser(user_id=user_a.id, tenant_id=tenant_a.id, role="admin"))

    # User B
    user_b = User(email="userb@test.local", password_hash=hash_password("Test1234"), role="admin", is_active=True)
    db.add(user_b)
    db.flush()
    db.add(TenantUser(user_id=user_b.id, tenant_id=tenant_b.id, role="admin"))

    # Customer + Case pour tenant A
    cust_a = Customer(tenant_id=tenant_a.id, first_name="Alice", last_name="A")
    db.add(cust_a)
    db.flush()
    case_a = Case(tenant_id=tenant_a.id, customer_id=cust_a.id, status="draft", source="test")
    db.add(case_a)

    # Customer + Case pour tenant B
    cust_b = Customer(tenant_id=tenant_b.id, first_name="Bob", last_name="B")
    db.add(cust_b)
    db.flush()
    case_b = Case(tenant_id=tenant_b.id, customer_id=cust_b.id, status="draft", source="test")
    db.add(case_b)

    db.commit()
    db.refresh(case_a)
    db.refresh(case_b)
    return {
        "tenant_a": tenant_a, "tenant_b": tenant_b,
        "user_a": user_a, "user_b": user_b,
        "case_a": case_a, "case_b": case_b,
    }


def _login(client, email: str) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Test1234"},
    )
    return resp.cookies.get("optiflow_token")


def test_user_a_sees_only_tenant_a_cases(client, two_tenants):
    token = _login(client, "usera@test.local")
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    cases = resp.json()
    assert len(cases) >= 1
    names = [c["customer_name"] for c in cases]
    assert "Alice A" in names
    assert "Bob B" not in names


def test_user_b_sees_only_tenant_b_cases(client, two_tenants):
    token = _login(client, "userb@test.local")
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    cases = resp.json()
    names = [c["customer_name"] for c in cases]
    assert "Bob B" in names
    assert "Alice A" not in names


def test_user_a_cannot_access_tenant_b_case(client, two_tenants):
    token = _login(client, "usera@test.local")
    case_b_id = two_tenants["case_b"].id
    resp = client.get(f"/api/v1/cases/{case_b_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
