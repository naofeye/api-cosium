"""Tests du workflow complet d'onboarding : signup → connect cosium (mock) → status."""
from unittest.mock import MagicMock, patch

from app.models import Organization, Tenant, TenantUser, User


def test_signup_creates_org_tenant_user(client, db):
    resp = client.post("/api/v1/onboarding/signup", json={
        "company_name": "Optique Test",
        "owner_email": "owner@test.com",
        "owner_password": "Test12345!",
        "owner_first_name": "Jean",
        "owner_last_name": "Martin",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["tenant_id"] is not None
    assert data["tenant_name"] == "Optique Test"
    assert data["role"] == "admin"
    assert len(data["available_tenants"]) == 1

    org = db.query(Organization).filter(Organization.slug == "optique-test").first()
    assert org is not None
    assert org.plan == "trial"
    assert org.trial_ends_at is not None

    tenant = db.query(Tenant).filter(Tenant.slug == "optique-test").first()
    assert tenant is not None
    assert tenant.organization_id == org.id

    user = db.query(User).filter(User.email == "owner@test.com").first()
    assert user is not None

    tu = db.query(TenantUser).filter(TenantUser.user_id == user.id).first()
    assert tu is not None
    assert tu.role == "admin"


def test_signup_duplicate_email_rejected(client, db):
    client.post("/api/v1/onboarding/signup", json={
        "company_name": "First",
        "owner_email": "dup@test.com",
        "owner_password": "Test12345!",
        "owner_first_name": "A",
        "owner_last_name": "B",
    })
    resp = client.post("/api/v1/onboarding/signup", json={
        "company_name": "Second",
        "owner_email": "dup@test.com",
        "owner_password": "Test12345!",
        "owner_first_name": "C",
        "owner_last_name": "D",
    })
    assert resp.status_code == 422


def test_signup_weak_password_rejected(client):
    resp = client.post("/api/v1/onboarding/signup", json={
        "company_name": "Weak",
        "owner_email": "weak@test.com",
        "owner_password": "short",
        "owner_first_name": "X",
        "owner_last_name": "Y",
    })
    assert resp.status_code == 422


def test_onboarding_status_after_signup(client, db):
    resp = client.post("/api/v1/onboarding/signup", json={
        "company_name": "Status Test",
        "owner_email": "status@test.com",
        "owner_password": "Test12345!",
        "owner_first_name": "A",
        "owner_last_name": "B",
    })
    token = resp.json()["access_token"]

    status = client.get(
        "/api/v1/onboarding/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status.status_code == 200
    data = status.json()
    assert data["current_step"] == "cosium"
    assert data["cosium_connected"] is False
    assert data["first_sync_done"] is False
    assert data["trial_days_remaining"] is not None
    assert data["trial_days_remaining"] >= 13


@patch("app.integrations.erp_factory.get_connector")
def test_connect_cosium_success(mock_get_connector, client, db):
    mock_connector = MagicMock()
    mock_connector.authenticate.return_value = "fake-token"
    mock_get_connector.return_value = mock_connector

    resp = client.post("/api/v1/onboarding/signup", json={
        "company_name": "Cosium Test",
        "owner_email": "cosium@test.com",
        "owner_password": "Test12345!",
        "owner_first_name": "A",
        "owner_last_name": "B",
    })
    token = resp.json()["access_token"]

    connect = client.post(
        "/api/v1/onboarding/connect-cosium",
        json={"cosium_tenant": "mysite", "cosium_login": "user", "cosium_password": "pass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert connect.status_code == 200
    assert connect.json()["status"] == "connected"

    tenant = db.query(Tenant).filter(Tenant.cosium_tenant == "mysite").first()
    assert tenant is not None
    assert tenant.cosium_connected is True


@patch("app.integrations.erp_factory.get_connector")
def test_connect_cosium_failure(mock_get_connector, client, db):
    mock_connector = MagicMock()
    mock_connector.authenticate.side_effect = Exception("Connection refused")
    mock_get_connector.return_value = mock_connector

    resp = client.post("/api/v1/onboarding/signup", json={
        "company_name": "Fail Cosium",
        "owner_email": "fail@test.com",
        "owner_password": "Test12345!",
        "owner_first_name": "A",
        "owner_last_name": "B",
    })
    token = resp.json()["access_token"]

    connect = client.post(
        "/api/v1/onboarding/connect-cosium",
        json={"cosium_tenant": "badsite", "cosium_login": "user", "cosium_password": "pass"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert connect.status_code == 400
