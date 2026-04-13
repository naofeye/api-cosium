"""Tests : les endpoints /admin/* refusent les users non-admin (403/404)."""
import pytest

from app.models import Tenant, TenantUser, User
from app.security import hash_password


@pytest.fixture(name="operator_user")
def operator_user_fixture(db):
    """User avec role=operator sur le tenant par defaut (pas admin)."""
    user = User(
        email="operator@optiflow.local",
        password_hash=hash_password("Test1234"),
        role="operator",
        is_active=True,
    )
    db.add(user)
    db.flush()
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    db.add(TenantUser(user_id=user.id, tenant_id=tenant.id, role="operator"))
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(name="operator_headers")
def operator_headers_fixture(client, operator_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "operator@optiflow.local", "password": "Test1234"},
    )
    token = resp.cookies.get("optiflow_token")
    return {"Authorization": f"Bearer {token}"}


ADMIN_ENDPOINTS = [
    ("GET", "/api/v1/admin/users"),
    ("POST", "/api/v1/admin/users"),
    ("GET", "/api/v1/audit-logs"),
]


@pytest.mark.parametrize("method,url", ADMIN_ENDPOINTS)
def test_admin_endpoints_forbid_non_admin(client, operator_headers, method, url):
    """Un operator (role non-admin) doit etre rejete sur tous les /admin/*."""
    resp = client.request(method, url, headers=operator_headers, json={} if method == "POST" else None)
    # 403 si RBAC enforcing, 404 si route non montée dans ce build, 405 si methode pas autorisee
    assert resp.status_code in (401, 403, 404, 405), (
        f"{method} {url} devrait etre refuse (401/403/404), got {resp.status_code}: {resp.text[:200]}"
    )
    # Le contenu sensible ne doit JAMAIS fuiter
    if resp.status_code == 200:
        pytest.fail(f"LEAK: {method} {url} a retourne 200 pour un non-admin")


@pytest.mark.parametrize("method,url", ADMIN_ENDPOINTS)
def test_admin_endpoints_require_auth(client, method, url):
    """Sans token, tous les /admin/* doivent rejeter (401/403)."""
    resp = client.request(method, url, json={} if method == "POST" else None)
    assert resp.status_code in (401, 403), (
        f"{method} {url} sans auth devrait rejeter, got {resp.status_code}"
    )
