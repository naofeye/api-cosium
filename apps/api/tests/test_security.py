"""Tests de securite : auth 401/403, rate limiting, security headers."""
from datetime import UTC


def test_protected_endpoint_returns_401_without_token(client):
    """Les endpoints proteges doivent retourner 401 sans token."""
    protected = [
        "/api/v1/cases",
        "/api/v1/clients",
        "/api/v1/devis",
        "/api/v1/factures",
        "/api/v1/pec",
        "/api/v1/notifications",
        "/api/v1/action-items",
        "/api/v1/analytics/dashboard",
        "/api/v1/marketing/segments",
    ]
    for url in protected:
        resp = client.get(url)
        assert resp.status_code == 401, f"{url} devrait retourner 401, got {resp.status_code}"


def test_admin_endpoint_returns_403_for_non_admin(client, seed_user, db):
    """Les endpoints admin doivent retourner 401/403 pour un role insuffisant."""
    from app.models import Tenant, TenantUser, User
    from app.security import hash_password

    # Create operator user
    operator = User(
        email="operator@test.local",
        password_hash=hash_password("Operator1"),
        role="operator",
        is_active=True,
    )
    db.add(operator)
    db.flush()
    # Assign operator to default tenant
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    tu = TenantUser(user_id=operator.id, tenant_id=tenant.id, role="operator")
    db.add(tu)
    db.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "operator@test.local", "password": "Operator1"},
    )
    token = login.cookies.get("optiflow_token")
    headers = {"Authorization": f"Bearer {token}"}

    admin_endpoints = [
        "/api/v1/audit-logs",
        "/api/v1/admin/metrics",
    ]
    for url in admin_endpoints:
        resp = client.get(url, headers=headers)
        assert resp.status_code == 403, f"{url} devrait bloquer un operator, got {resp.status_code}"


def test_security_headers_present(client):
    """Toutes les reponses doivent contenir les headers de securite."""
    resp = client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-xss-protection") == "1; mode=block"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_login_rate_limiting(client, seed_user):
    """Le rate limiter doit bloquer apres trop de tentatives.

    Skipped en local/test ou le rate limiter est desactive.
    """
    from app.core.config import settings

    if settings.app_env in ("test", "local"):
        return  # Rate limiter disabled

    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": "test@optiflow.com", "password": "wrong"},
        )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "wrong"},
    )
    assert resp.status_code == 429


def test_expired_token_returns_401(client, seed_user):
    """Un token expire doit retourner 401."""
    from datetime import datetime, timedelta

    import jwt as pyjwt

    from app.core.config import settings

    expired_token = pyjwt.encode(
        {
            "sub": "test@optiflow.com",
            "role": "admin",
            "exp": datetime.now(UTC) - timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_invalid_token_returns_401(client):
    """Un token invalide doit retourner 401."""
    resp = client.get(
        "/api/v1/cases",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert resp.status_code == 401


def test_health_endpoint_public(client):
    """Le health check doit etre accessible sans auth."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
