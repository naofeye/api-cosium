"""Tests for core/deps.py — authentication & role-based access."""

import pytest
from app.models import Tenant, TenantUser, User
from app.security import hash_password


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    def test_valid_token_returns_user(self, client, auth_headers):
        resp = client.get("/api/v1/cases", headers=auth_headers)
        assert resp.status_code != 401

    def test_no_token_returns_401(self, client, seed_user):
        resp = client.get("/api/v1/cases")
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_invalid_token_returns_401(self, client, seed_user):
        resp = client.get(
            "/api/v1/cases",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client, seed_user):
        import jwt as pyjwt
        from app.core.config import settings

        expired = pyjwt.encode(
            {"sub": "test@optiflow.local", "exp": 0},
            settings.jwt_secret,
            algorithm="HS256",
        )
        resp = client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert resp.status_code == 401

    def test_token_with_no_sub_returns_401(self, client, seed_user):
        import jwt as pyjwt
        from app.core.config import settings
        import time

        token = pyjwt.encode(
            {"exp": int(time.time()) + 3600},
            settings.jwt_secret,
            algorithm="HS256",
        )
        resp = client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    def test_token_for_nonexistent_user_returns_401(self, client, seed_user):
        import jwt as pyjwt
        from app.core.config import settings
        import time

        token = pyjwt.encode(
            {"sub": "ghost@optiflow.local", "exp": int(time.time()) + 3600},
            settings.jwt_secret,
            algorithm="HS256",
        )
        resp = client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    def test_inactive_user_returns_401(self, client, db):
        user = User(
            email="inactive@optiflow.local",
            password_hash=hash_password("test123"),
            role="admin",
            is_active=False,
        )
        db.add(user)
        db.commit()

        import jwt as pyjwt
        from app.core.config import settings
        import time

        token = pyjwt.encode(
            {"sub": "inactive@optiflow.local", "exp": int(time.time()) + 3600},
            settings.jwt_secret,
            algorithm="HS256",
        )
        resp = client.get(
            "/api/v1/cases",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401


class TestRequireRole:
    """Tests for require_role dependency."""

    def test_admin_can_access_admin_endpoint(self, client, auth_headers):
        # audit-logs requires require_tenant_role("admin")
        resp = client.get("/api/v1/audit-logs", headers=auth_headers)
        # seed_user has tenant role admin — should not be 403
        assert resp.status_code != 403

    def test_operator_cannot_access_admin_endpoint(self, client, db):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        operator = User(
            email="operator@optiflow.local",
            password_hash=hash_password("test123"),
            role="operator",
            is_active=True,
        )
        db.add(operator)
        db.flush()
        tu = TenantUser(user_id=operator.id, tenant_id=tenant.id, role="operator")
        db.add(tu)
        db.commit()

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "operator@optiflow.local", "password": "test123"},
        )
        token = resp.cookies.get("optiflow_token")
        headers = {"Authorization": f"Bearer {token}"}

        # audit-logs requires admin tenant role — operator should get 403
        resp = client.get("/api/v1/audit-logs", headers=headers)
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "FORBIDDEN"
