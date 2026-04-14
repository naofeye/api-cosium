"""Tests pour le tenant context : extraction du tenant depuis le JWT, validation d'accès."""
from app.models import User
from app.security import hash_password


def test_login_returns_tenant_info(client, seed_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "tenant_id" in data
    assert "tenant_name" in data
    assert "available_tenants" in data
    assert len(data["available_tenants"]) >= 1
    assert data["available_tenants"][0]["slug"] == "test-magasin"


def test_jwt_contains_tenant_id(client, seed_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    token = resp.cookies.get("optiflow_token")
    from app.security import decode_access_token
    payload = decode_access_token(token)
    assert "tenant_id" in payload
    assert payload["tenant_id"] == resp.json()["tenant_id"]


def test_endpoint_requires_tenant_in_jwt(client, seed_user):
    from app.security import create_access_token
    # Token sans tenant_id
    old_token = create_access_token("test@optiflow.com", "admin")
    resp = client.get(
        "/api/v1/cases",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert resp.status_code == 401


def test_user_without_tenant_access_rejected(client, db):
    user = User(email="orphan@test.local", password_hash=hash_password("Test1234"), role="admin", is_active=True)
    db.add(user)
    db.commit()
    # Login should fail: no tenant assigned
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "orphan@test.local", "password": "Test1234"},
    )
    assert resp.status_code == 401
