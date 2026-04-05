"""Tests pour le switch de tenant."""
import pytest

from app.models import Case, Customer, Organization, Tenant, TenantUser, User
from app.security import hash_password


@pytest.fixture(name="multi_tenant_user")
def multi_tenant_user_fixture(db):
    """Crée un user qui a accès à 2 tenants."""
    org = db.query(Organization).first()
    tenant_a = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    tenant_b = Tenant(organization_id=org.id, name="Magasin B", slug="magasin-b")
    db.add(tenant_b)
    db.flush()

    user = User(email="multi@test.local", password_hash=hash_password("Test1234"), role="admin", is_active=True)
    db.add(user)
    db.flush()
    db.add(TenantUser(user_id=user.id, tenant_id=tenant_a.id, role="admin"))
    db.add(TenantUser(user_id=user.id, tenant_id=tenant_b.id, role="operator"))

    # Données tenant A
    cust_a = Customer(tenant_id=tenant_a.id, first_name="Alice", last_name="A")
    db.add(cust_a)
    db.flush()
    db.add(Case(tenant_id=tenant_a.id, customer_id=cust_a.id, status="draft", source="test"))

    # Données tenant B
    cust_b = Customer(tenant_id=tenant_b.id, first_name="Bob", last_name="B")
    db.add(cust_b)
    db.flush()
    db.add(Case(tenant_id=tenant_b.id, customer_id=cust_b.id, status="draft", source="test"))

    db.commit()
    return {"user": user, "tenant_a": tenant_a, "tenant_b": tenant_b}


def test_login_returns_multiple_tenants(client, multi_tenant_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "multi@test.local", "password": "Test1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["available_tenants"]) == 2


def test_switch_tenant_changes_data(client, multi_tenant_user):
    # Login (default tenant A)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "multi@test.local", "password": "Test1234"},
    )
    token_a = resp.cookies.get("optiflow_token")
    tenant_b_id = multi_tenant_user["tenant_b"].id

    # Vérifier données tenant A
    cases_a = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token_a}"}).json()
    names_a = [c["customer_name"] for c in cases_a]
    assert "Alice A" in names_a

    # Switch vers tenant B
    resp_switch = client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": tenant_b_id},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_switch.status_code == 200
    data_switch = resp_switch.json()
    assert data_switch["tenant_id"] == tenant_b_id
    token_b = resp_switch.cookies.get("optiflow_token")

    # Vérifier données tenant B
    cases_b = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token_b}"}).json()
    names_b = [c["customer_name"] for c in cases_b]
    assert "Bob B" in names_b
    assert "Alice A" not in names_b


def test_switch_to_unauthorized_tenant_fails(client, multi_tenant_user, db):
    org = db.query(Organization).first()
    tenant_c = Tenant(organization_id=org.id, name="Magasin C", slug="magasin-c")
    db.add(tenant_c)
    db.commit()
    db.refresh(tenant_c)

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "multi@test.local", "password": "Test1234"},
    )
    token = resp.cookies.get("optiflow_token")

    resp_switch = client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": tenant_c.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_switch.status_code == 401
