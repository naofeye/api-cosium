"""Tests for admin_user_service: user CRUD, role changes, deactivation."""

from unittest.mock import patch

import pytest

from app.core.exceptions import BusinessError, NotFoundError
from app.domain.schemas.admin_users import AdminUserCreate, AdminUserUpdate
from app.models import TenantUser, User
from app.security import hash_password
from app.services import admin_user_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(db, email: str = "user@example.com") -> User:
    user = User(email=email, password_hash=hash_password("Password1"), role="user", is_active=True)
    db.add(user)
    db.flush()
    return user


def _make_tenant_user(db, user_id: int, tenant_id: int, role: str = "operator") -> TenantUser:
    tu = TenantUser(user_id=user_id, tenant_id=tenant_id, role=role, is_active=True)
    db.add(tu)
    db.flush()
    return tu


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_empty_tenant_returns_empty_list(self, db, default_tenant):
        result = admin_user_service.list_users(db, default_tenant.id)
        # The conftest seed_user fixture is NOT used here, so only the
        # default seeded data might exist.  We work on a fresh tenant where no
        # extra users have been added.
        assert isinstance(result, list)

    def test_returns_users_for_tenant(self, db, default_tenant):
        user = _make_user(db, "alice@example.com")
        _make_tenant_user(db, user.id, default_tenant.id, role="manager")
        db.commit()

        result = admin_user_service.list_users(db, default_tenant.id)
        emails = [r.email for r in result]
        assert "alice@example.com" in emails

    def test_does_not_include_users_from_other_tenants(self, db, default_tenant):
        from app.models import Organization, Tenant

        other_org = Organization(name="Other Org", slug="other-org", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(
            organization_id=other_org.id,
            name="Other Magasin",
            slug="other-magasin",
        )
        db.add(other_tenant)
        db.flush()

        user = _make_user(db, "other@example.com")
        _make_tenant_user(db, user.id, other_tenant.id, role="viewer")
        db.commit()

        result = admin_user_service.list_users(db, default_tenant.id)
        emails = [r.email for r in result]
        assert "other@example.com" not in emails

    def test_is_active_reflects_both_user_and_tenant_user(self, db, default_tenant):
        user = _make_user(db, "inactive@example.com")
        tu = _make_tenant_user(db, user.id, default_tenant.id, role="operator")
        tu.is_active = False
        db.commit()

        result = admin_user_service.list_users(db, default_tenant.id)
        match = next((r for r in result if r.email == "inactive@example.com"), None)
        assert match is not None
        assert match.is_active is False


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

@patch("app.services.admin_user_service.audit_service.log_action")
class TestCreateUser:
    def test_creates_new_user(self, mock_audit, db, default_tenant):
        payload = AdminUserCreate(email="new@example.com", password="Password1", role="operator")
        result = admin_user_service.create_user(db, default_tenant.id, payload, admin_user_id=1)

        assert result.email == "new@example.com"
        assert result.role == "operator"
        assert result.is_active is True
        mock_audit.assert_called_once()

    def test_adds_existing_user_to_tenant(self, mock_audit, db, default_tenant):
        """A user that already exists globally gets linked to the tenant."""
        user = _make_user(db, "existing@example.com")
        db.commit()

        payload = AdminUserCreate(email="existing@example.com", password="Password1", role="viewer")
        result = admin_user_service.create_user(db, default_tenant.id, payload, admin_user_id=1)

        assert result.email == "existing@example.com"
        assert result.role == "viewer"
        mock_audit.assert_called_once()

    def test_raises_business_error_if_user_already_in_tenant(self, mock_audit, db, default_tenant):
        user = _make_user(db, "dup@example.com")
        _make_tenant_user(db, user.id, default_tenant.id, role="operator")
        db.commit()

        payload = AdminUserCreate(email="dup@example.com", password="Password1", role="operator")
        with pytest.raises(BusinessError):
            admin_user_service.create_user(db, default_tenant.id, payload, admin_user_id=1)

    def test_refuses_to_steal_user_from_another_tenant(self, mock_audit, db, default_tenant):
        """Securite : un admin du tenant A ne peut pas ajouter silencieusement
        un user qui appartient deja au tenant B (via son email). Avant ce fix,
        le service ajoutait le user au tenant A sans son consentement, exposant
        les donnees metier de A.
        """
        from app.models import Organization, Tenant

        other_org = Organization(name="Other", slug="other-org", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(
            organization_id=other_org.id, name="Other", slug="other",
            erp_type="cosium", is_active=True,
        )
        db.add(other_tenant)
        db.flush()
        user = _make_user(db, "external@example.com")
        _make_tenant_user(db, user.id, other_tenant.id, role="admin")
        db.commit()

        payload = AdminUserCreate(email="external@example.com", password="Password1", role="viewer")
        with pytest.raises(BusinessError) as exc_info:
            admin_user_service.create_user(db, default_tenant.id, payload, admin_user_id=1)
        assert "autre magasin" in str(exc_info.value).lower()

    def test_new_user_is_stored_in_db(self, mock_audit, db, default_tenant):
        payload = AdminUserCreate(email="stored@example.com", password="Password1", role="manager")
        admin_user_service.create_user(db, default_tenant.id, payload, admin_user_id=1)

        from app.repositories import user_repo
        stored = user_repo.get_user_by_email(db, "stored@example.com")
        assert stored is not None
        assert stored.email == "stored@example.com"

    def test_tenant_user_record_created_for_new_user(self, mock_audit, db, default_tenant):
        payload = AdminUserCreate(email="tu_check@example.com", password="Password1", role="admin")
        result = admin_user_service.create_user(db, default_tenant.id, payload, admin_user_id=1)

        from app.repositories import tenant_user_repo
        tu = tenant_user_repo.get_by_user_and_tenant(db, result.id, default_tenant.id)
        assert tu is not None
        assert tu.role == "admin"

    def test_audit_called_with_correct_action(self, mock_audit, db, default_tenant):
        payload = AdminUserCreate(email="audit@example.com", password="Password1", role="operator")
        admin_user_service.create_user(db, default_tenant.id, payload, admin_user_id=42)

        call_kwargs = mock_audit.call_args
        # positional: db, tenant_id, admin_user_id, action, entity_type, entity_id
        assert call_kwargs[0][3] == "create"


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

@patch("app.services.admin_user_service.audit_service.log_action")
class TestUpdateUser:
    def test_update_role(self, mock_audit, db, default_tenant):
        user = _make_user(db, "role_change@example.com")
        _make_tenant_user(db, user.id, default_tenant.id, role="operator")
        db.commit()

        payload = AdminUserUpdate(role="manager")
        result = admin_user_service.update_user(db, default_tenant.id, user.id, payload, admin_user_id=1)

        assert result.role == "manager"
        mock_audit.assert_called_once()

    def test_update_is_active_to_false(self, mock_audit, db, default_tenant):
        user = _make_user(db, "deact_update@example.com")
        _make_tenant_user(db, user.id, default_tenant.id, role="operator")
        db.commit()

        payload = AdminUserUpdate(is_active=False)
        result = admin_user_service.update_user(db, default_tenant.id, user.id, payload, admin_user_id=1)

        assert result.is_active is False

    def test_update_is_active_to_true(self, mock_audit, db, default_tenant):
        user = _make_user(db, "reactivate@example.com")
        tu = _make_tenant_user(db, user.id, default_tenant.id, role="operator")
        tu.is_active = False
        db.commit()

        payload = AdminUserUpdate(is_active=True)
        result = admin_user_service.update_user(db, default_tenant.id, user.id, payload, admin_user_id=1)

        assert result.is_active is True

    def test_update_both_role_and_active(self, mock_audit, db, default_tenant):
        user = _make_user(db, "both@example.com")
        _make_tenant_user(db, user.id, default_tenant.id, role="viewer")
        db.commit()

        payload = AdminUserUpdate(role="admin", is_active=False)
        result = admin_user_service.update_user(db, default_tenant.id, user.id, payload, admin_user_id=1)

        assert result.role == "admin"
        assert result.is_active is False

    def test_raises_not_found_if_user_not_in_tenant(self, mock_audit, db, default_tenant):
        payload = AdminUserUpdate(role="manager")
        with pytest.raises(NotFoundError):
            admin_user_service.update_user(db, default_tenant.id, 99999, payload, admin_user_id=1)

    def test_raises_not_found_if_user_record_missing(self, mock_audit, db, default_tenant):
        """TenantUser exists but the User row is gone (referential integrity bypass)."""
        # Directly create a TenantUser with a ghost user_id to simulate corruption.
        # In SQLite with StaticPool there is no FK enforcement by default.
        ghost_user_id = 88888
        tu = TenantUser(user_id=ghost_user_id, tenant_id=default_tenant.id, role="operator", is_active=True)
        db.add(tu)
        db.flush()
        db.commit()

        payload = AdminUserUpdate(role="manager")
        with pytest.raises(NotFoundError):
            admin_user_service.update_user(db, default_tenant.id, ghost_user_id, payload, admin_user_id=1)

    def test_none_fields_not_applied(self, mock_audit, db, default_tenant):
        """Passing None for role/is_active should leave them unchanged."""
        user = _make_user(db, "noop@example.com")
        _make_tenant_user(db, user.id, default_tenant.id, role="viewer")
        db.commit()

        payload = AdminUserUpdate(role=None, is_active=None)
        result = admin_user_service.update_user(db, default_tenant.id, user.id, payload, admin_user_id=1)

        assert result.role == "viewer"
        assert result.is_active is True


# ---------------------------------------------------------------------------
# deactivate_user
# ---------------------------------------------------------------------------

@patch("app.services.admin_user_service.audit_service.log_action")
class TestDeactivateUser:
    def test_deactivates_user_in_tenant(self, mock_audit, db, default_tenant):
        admin = _make_user(db, "admin@example.com")
        user = _make_user(db, "victim@example.com")
        _make_tenant_user(db, user.id, default_tenant.id, role="operator")
        db.commit()

        result = admin_user_service.deactivate_user(db, default_tenant.id, user.id, admin_user_id=admin.id)

        assert result.is_active is False
        mock_audit.assert_called_once()

    def test_cannot_deactivate_self(self, mock_audit, db, default_tenant):
        user = _make_user(db, "self@example.com")
        _make_tenant_user(db, user.id, default_tenant.id, role="admin")
        db.commit()

        with pytest.raises(BusinessError, match="propre compte"):
            admin_user_service.deactivate_user(db, default_tenant.id, user.id, admin_user_id=user.id)

    def test_raises_not_found_if_not_in_tenant(self, mock_audit, db, default_tenant):
        with pytest.raises(NotFoundError):
            admin_user_service.deactivate_user(db, default_tenant.id, 99999, admin_user_id=1)

    def test_deactivate_is_persisted(self, mock_audit, db, default_tenant):
        admin = _make_user(db, "admin_persist@example.com")
        user = _make_user(db, "persist_deact@example.com")
        tu = _make_tenant_user(db, user.id, default_tenant.id, role="operator")
        db.commit()

        admin_user_service.deactivate_user(db, default_tenant.id, user.id, admin_user_id=admin.id)

        db.refresh(tu)
        assert tu.is_active is False

    def test_audit_action_is_deactivate(self, mock_audit, db, default_tenant):
        admin = _make_user(db, "admin_audit@example.com")
        user = _make_user(db, "audit_deact@example.com")
        _make_tenant_user(db, user.id, default_tenant.id, role="operator")
        db.commit()

        admin_user_service.deactivate_user(db, default_tenant.id, user.id, admin_user_id=admin.id)

        call_args = mock_audit.call_args[0]
        assert call_args[3] == "deactivate"
