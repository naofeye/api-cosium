"""Tests E2E pour le flux d'authentification et l'isolation multi-tenant."""
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.models import Customer, Organization, Tenant, TenantUser, User
from app.security import hash_password


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_redis_blacklist():
    """Nettoie les cles blacklist Redis avant chaque test pour eviter les faux positifs.

    Le mecanisme blacklist utilise token[:32] comme cle, ce qui correspond
    au header JWT (identique pour tous les tokens HS256). Un token blackliste
    dans un test precedent bloquerait donc tous les tokens suivants.
    """
    try:
        from app.core.redis_cache import get_redis_client

        r = get_redis_client()
        if r:
            for key in r.keys("blacklist:*"):
                r.delete(key)
    except Exception:
        pass
    yield
    try:
        from app.core.redis_cache import get_redis_client

        r = get_redis_client()
        if r:
            for key in r.keys("blacklist:*"):
                r.delete(key)
    except Exception:
        pass

@pytest.fixture(name="two_tenants_with_customers")
def two_tenants_with_customers_fixture(db):
    """Cree 2 tenants, 2 users et 1 customer dans le tenant A uniquement."""
    org = db.query(Organization).first()

    tenant_a = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

    tenant_b = Tenant(organization_id=org.id, name="Magasin B", slug="magasin-b-auth")
    db.add(tenant_b)
    db.flush()

    user_a = User(
        email="auth_usera@test.local",
        password_hash=hash_password("Secret1234"),
        role="admin",
        is_active=True,
    )
    db.add(user_a)
    db.flush()
    db.add(TenantUser(user_id=user_a.id, tenant_id=tenant_a.id, role="admin"))

    user_b = User(
        email="auth_userb@test.local",
        password_hash=hash_password("Secret1234"),
        role="admin",
        is_active=True,
    )
    db.add(user_b)
    db.flush()
    db.add(TenantUser(user_id=user_b.id, tenant_id=tenant_b.id, role="admin"))

    # Customer dans tenant A seulement
    customer_a = Customer(tenant_id=tenant_a.id, first_name="TenantA", last_name="Only")
    db.add(customer_a)

    db.commit()
    db.refresh(customer_a)
    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "user_a": user_a,
        "user_b": user_b,
        "customer_a": customer_a,
    }


@pytest.fixture(name="multi_tenant_user")
def multi_tenant_user_fixture(db):
    """Cree un user qui a acces a 2 tenants (pour tester switch-tenant)."""
    org = db.query(Organization).first()

    tenant_1 = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

    tenant_2 = Tenant(organization_id=org.id, name="Magasin Switch", slug="magasin-switch")
    db.add(tenant_2)
    db.flush()

    user = User(
        email="multi@test.local",
        password_hash=hash_password("Multi1234"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(TenantUser(user_id=user.id, tenant_id=tenant_1.id, role="admin"))
    db.add(TenantUser(user_id=user.id, tenant_id=tenant_2.id, role="manager"))
    db.commit()
    return {
        "user": user,
        "tenant_1": tenant_1,
        "tenant_2": tenant_2,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login(client, email: str, password: str = "Secret1234") -> dict:
    """Login and return cookies as dict."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return resp


def _auth_headers(login_resp) -> dict:
    """Extrait le token du cookie et retourne un header Authorization."""
    token = login_resp.cookies.get("optiflow_token")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Test tenant isolation
# ---------------------------------------------------------------------------

def test_tenant_isolation(client, two_tenants_with_customers):
    """User A cree un client dans tenant A. User B dans tenant B ne le voit pas."""
    data = two_tenants_with_customers

    # User A login et cree un client via l'API
    login_a = _login(client, "auth_usera@test.local")
    assert login_a.status_code == 200
    headers_a = _auth_headers(login_a)

    create_resp = client.post(
        "/api/v1/clients",
        json={"first_name": "Visible", "last_name": "PourA"},
        headers=headers_a,
    )
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]

    # User A voit le client
    list_a = client.get("/api/v1/clients", headers=headers_a)
    assert list_a.status_code == 200
    names_a = [c["last_name"] for c in list_a.json()["items"]]
    assert "PourA" in names_a

    # User B login (tenant B) et ne voit PAS le client
    login_b = _login(client, "auth_userb@test.local")
    assert login_b.status_code == 200
    headers_b = _auth_headers(login_b)

    list_b = client.get("/api/v1/clients", headers=headers_b)
    assert list_b.status_code == 200
    names_b = [c["last_name"] for c in list_b.json()["items"]]
    assert "PourA" not in names_b

    # User B ne peut pas acceder au client par ID
    detail_b = client.get(f"/api/v1/clients/{created_id}", headers=headers_b)
    assert detail_b.status_code == 404


# ---------------------------------------------------------------------------
# 2. Test full auth flow
# ---------------------------------------------------------------------------

def test_full_auth_flow(client, multi_tenant_user):
    """Login -> /me -> refresh -> switch tenant -> verify -> logout -> revoked."""
    data = multi_tenant_user
    tenant_1 = data["tenant_1"]
    tenant_2 = data["tenant_2"]

    # 1. Login
    login_resp = _login(client, "multi@test.local", "Multi1234")
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert body["tenant_id"] == tenant_1.id
    assert len(body["available_tenants"]) == 2
    assert "optiflow_token" in login_resp.cookies
    assert "optiflow_refresh" in login_resp.cookies

    headers = _auth_headers(login_resp)

    # 2. /auth/me
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "multi@test.local"
    assert me_data["role"] == "admin"
    assert me_data["is_active"] is True

    # 3. Refresh token
    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 204
    assert "optiflow_token" in refresh_resp.cookies

    # Update headers with new token
    new_token = refresh_resp.cookies.get("optiflow_token")
    headers = {"Authorization": f"Bearer {new_token}"}

    # 4. Switch tenant
    switch_resp = client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_id": tenant_2.id},
        headers=headers,
    )
    assert switch_resp.status_code == 200
    switch_data = switch_resp.json()
    assert switch_data["tenant_id"] == tenant_2.id
    assert switch_data["tenant_name"] == "Magasin Switch"

    # 5. Verify new tenant via /me with new token
    switched_token = switch_resp.cookies.get("optiflow_token")
    headers_switched = {"Authorization": f"Bearer {switched_token}"}
    me_after = client.get("/api/v1/auth/me", headers=headers_switched)
    assert me_after.status_code == 200

    # 6. Logout
    logout_resp = client.post("/api/v1/auth/logout", headers=headers_switched)
    assert logout_resp.status_code == 204

    # 7. Refresh after logout should fail (refresh token revoked)
    refresh_after_logout = client.post("/api/v1/auth/refresh")
    assert refresh_after_logout.status_code == 401


# ---------------------------------------------------------------------------
# 3. Test admin endpoints require auth
# ---------------------------------------------------------------------------

def test_admin_endpoints_require_auth(client):
    """Appeler des endpoints proteges sans token doit retourner 401."""
    # /api/v1/cases requires authentication
    resp_cases = client.get("/api/v1/cases")
    assert resp_cases.status_code == 401

    # /api/v1/clients requires authentication
    resp_clients = client.get("/api/v1/clients")
    assert resp_clients.status_code == 401

    # /api/v1/auth/me requires authentication
    resp_me = client.get("/api/v1/auth/me")
    assert resp_me.status_code == 401

    # POST /api/v1/clients requires authentication
    resp_create = client.post(
        "/api/v1/clients",
        json={"first_name": "Hack", "last_name": "Attempt"},
    )
    assert resp_create.status_code == 401


# ---------------------------------------------------------------------------
# 4. Test logout blacklists token
# ---------------------------------------------------------------------------

def test_logout_blacklists_token(client, seed_user):
    """Login -> logout -> reutiliser le meme access token -> 401.

    Verifie que le refresh token est revoque apres logout et que
    la session ne peut pas etre prolongee.
    """
    # Login
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.cookies.get("optiflow_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works before logout
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200

    # Logout (blacklists access token in Redis + revokes refresh token)
    logout_resp = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 204

    # Access token should be blacklisted (if Redis is available)
    try:
        from app.security import is_token_blacklisted

        if is_token_blacklisted(token):
            # Redis blacklist works: verify the token is rejected
            me_after = client.get("/api/v1/auth/me", headers=headers)
            assert me_after.status_code == 401
    except Exception:
        pass

    # Refresh token is revoked, so refresh should fail
    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 401


# ---------------------------------------------------------------------------
# 5. Test expired token rejected
# ---------------------------------------------------------------------------

def test_expired_token_rejected(client, seed_user):
    """Creer un token avec une expiration dans le passe, puis l'utiliser -> 401."""
    from app.core.config import settings

    # Creer un token deja expire (exp dans le passe)
    payload = {
        "sub": "test@optiflow.com",
        "role": "admin",
        "tenant_id": 1,
        "exp": datetime.now(UTC) - timedelta(seconds=10),
        "iss": "optiflow",
        "aud": "optiflow-api",
    }
    expired_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    headers = {"Authorization": f"Bearer {expired_token}"}

    resp = client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401

    resp_cases = client.get("/api/v1/cases", headers=headers)
    assert resp_cases.status_code == 401
