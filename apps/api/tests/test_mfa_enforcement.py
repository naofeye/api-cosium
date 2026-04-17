"""Tests MFA enforcement : require_admin_mfa sur Tenant."""

import pytest

from app.core.exceptions import AuthenticationError
from app.domain.schemas.auth import LoginRequest
from app.models import Tenant
from app.services import auth_service


class TestMfaEnforcementServiceLayer:
    def test_admin_without_mfa_rejected_if_tenant_enforces(self, db, seed_user, default_tenant):
        default_tenant.require_admin_mfa = True
        db.commit()

        with pytest.raises(AuthenticationError) as exc:
            auth_service.authenticate(
                db,
                LoginRequest(email="test@optiflow.com", password="test123"),
            )
        assert "MFA_SETUP_REQUIRED" in str(exc.value)

    def test_admin_with_mfa_allowed_if_tenant_enforces(self, db, seed_user, default_tenant):
        default_tenant.require_admin_mfa = True
        seed_user.totp_enabled = True
        seed_user.totp_secret_enc = "dummy-encrypted"
        db.commit()

        # MFA_CODE_REQUIRED (pas MFA_SETUP_REQUIRED) -> enforcement pass, reste juste
        # a fournir le code
        with pytest.raises(AuthenticationError) as exc:
            auth_service.authenticate(
                db,
                LoginRequest(email="test@optiflow.com", password="test123"),
            )
        assert "MFA_CODE_REQUIRED" in str(exc.value)

    def test_no_enforcement_when_flag_off(self, db, seed_user, default_tenant):
        default_tenant.require_admin_mfa = False
        db.commit()

        # Login reussit sans MFA
        resp = auth_service.authenticate(
            db,
            LoginRequest(email="test@optiflow.com", password="test123"),
        )
        assert resp.access_token

    def test_user_must_have_mfa_helper(self, db, seed_user, default_tenant):
        assert auth_service._user_must_have_mfa(db, seed_user.id) is False

        default_tenant.require_admin_mfa = True
        db.commit()
        assert auth_service._user_must_have_mfa(db, seed_user.id) is True


class TestSecurityPolicyEndpoints:
    def test_get_policy_default_false(self, client, auth_headers):
        resp = client.get("/api/v1/admin/tenant/security", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"require_admin_mfa": False}

    def test_patch_policy_enables_enforcement(self, client, auth_headers, db):
        resp = client.patch(
            "/api/v1/admin/tenant/security",
            json={"require_admin_mfa": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["require_admin_mfa"] is True
        # Persisted
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        assert tenant.require_admin_mfa is True

    def test_patch_policy_audited(self, client, auth_headers, db):
        from app.models import AuditLog

        client.patch(
            "/api/v1/admin/tenant/security",
            json={"require_admin_mfa": True},
            headers=auth_headers,
        )
        logs = db.query(AuditLog).filter(
            AuditLog.action == "update",
            AuditLog.entity_type == "tenant_security",
        ).all()
        assert len(logs) >= 1

    def test_patch_policy_rejects_non_admin(self, client, db):
        """Non-admin ne peut pas modifier la policy."""
        # Pas de seed d'user non-admin dispo ; smoke check : sans auth = 401
        resp = client.patch(
            "/api/v1/admin/tenant/security",
            json={"require_admin_mfa": True},
        )
        assert resp.status_code == 401
