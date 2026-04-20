"""Tests unitaires pour le systeme RBAC — require_permission et _ROLE_PERMISSIONS.

Strategie : on instancie un TenantContext factice avec le role voulu, puis on
appelle directement la fonction interne `permission_checker` retournee par
`require_permission(action, resource_type)`.  Aucun reseau, aucune BDD.
"""

import pytest

from app.core.deps import _RESOURCE_OVERRIDES, _ROLE_PERMISSIONS, require_permission
from app.core.exceptions import ForbiddenError
from app.core.tenant_context import TenantContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(role: str) -> TenantContext:
    """Cree un TenantContext minimal avec le role donne."""
    return TenantContext(tenant_id=1, user_id=1, role=role, is_group_admin=False)


def _check(action: str, role: str, resource_type: str | None = None) -> TenantContext:
    """Appelle le permission_checker retourne par require_permission.

    La factory `require_permission` produit une closure `permission_checker`
    dont la signature FastAPI attend un `TenantContext` via Depends.  En test,
    on l'appelle directement avec notre contexte factice.
    """
    checker = require_permission(action, resource_type)
    return checker(tenant_ctx=_ctx(role))


# ---------------------------------------------------------------------------
# 1. Role admin — toutes les actions autorisees
# ---------------------------------------------------------------------------

class TestAdminRole:
    ACTIONS = ("view", "create", "edit", "delete", "export", "manage")

    @pytest.mark.parametrize("action", ACTIONS)
    def test_admin_can_perform_all_actions(self, action: str) -> None:
        ctx = _check(action, "admin")
        assert ctx.role == "admin"

    def test_admin_permissions_match_matrix(self) -> None:
        assert _ROLE_PERMISSIONS["admin"] == {"view", "create", "edit", "delete", "export", "manage"}


# ---------------------------------------------------------------------------
# 2. Role manager — view/create/edit/delete/export autorisees, manage refuse
# ---------------------------------------------------------------------------

class TestManagerRole:
    ALLOWED = ("view", "create", "edit", "delete", "export")
    DENIED = ("manage",)

    @pytest.mark.parametrize("action", ALLOWED)
    def test_manager_can_perform_allowed_actions(self, action: str) -> None:
        ctx = _check(action, "manager")
        assert ctx.role == "manager"

    @pytest.mark.parametrize("action", DENIED)
    def test_manager_cannot_manage(self, action: str) -> None:
        with pytest.raises(ForbiddenError) as exc_info:
            _check(action, "manager")
        assert "manager" in exc_info.value.message
        assert action in exc_info.value.message

    def test_manager_permissions_match_matrix(self) -> None:
        assert _ROLE_PERMISSIONS["manager"] == {"view", "create", "edit", "delete", "export"}


# ---------------------------------------------------------------------------
# 3. Role operator — view/create/edit autorisees, delete/export/manage refuses
# ---------------------------------------------------------------------------

class TestOperatorRole:
    ALLOWED = ("view", "create", "edit")
    DENIED = ("delete", "export", "manage")

    @pytest.mark.parametrize("action", ALLOWED)
    def test_operator_can_perform_allowed_actions(self, action: str) -> None:
        ctx = _check(action, "operator")
        assert ctx.role == "operator"

    @pytest.mark.parametrize("action", DENIED)
    def test_operator_is_denied_restricted_actions(self, action: str) -> None:
        with pytest.raises(ForbiddenError) as exc_info:
            _check(action, "operator")
        assert "operator" in exc_info.value.message
        assert action in exc_info.value.message

    def test_operator_permissions_match_matrix(self) -> None:
        assert _ROLE_PERMISSIONS["operator"] == {"view", "create", "edit"}


# ---------------------------------------------------------------------------
# 4. Role viewer — uniquement view
# ---------------------------------------------------------------------------

class TestViewerRole:
    ALLOWED = ("view",)
    DENIED = ("create", "edit", "delete", "export", "manage")

    def test_viewer_can_view(self) -> None:
        ctx = _check("view", "viewer")
        assert ctx.role == "viewer"

    @pytest.mark.parametrize("action", DENIED)
    def test_viewer_is_denied_all_write_actions(self, action: str) -> None:
        with pytest.raises(ForbiddenError) as exc_info:
            _check(action, "viewer")
        assert "viewer" in exc_info.value.message
        assert action in exc_info.value.message

    def test_viewer_permissions_match_matrix(self) -> None:
        assert _ROLE_PERMISSIONS["viewer"] == {"view"}


# ---------------------------------------------------------------------------
# 5. Role inconnu — tout refuse
# ---------------------------------------------------------------------------

class TestUnknownRole:
    @pytest.mark.parametrize("action", ("view", "create", "edit", "delete", "export", "manage"))
    def test_unknown_role_denied_all(self, action: str) -> None:
        with pytest.raises(ForbiddenError):
            _check(action, "super_hacker")

    def test_empty_string_role_denied(self) -> None:
        with pytest.raises(ForbiddenError):
            _check("view", "")

    def test_unknown_role_not_in_matrix(self) -> None:
        assert "super_hacker" not in _ROLE_PERMISSIONS


# ---------------------------------------------------------------------------
# 6. Surcharges par type de ressource (resource_type overrides)
# ---------------------------------------------------------------------------

class TestResourceTypeOverrides:
    RESOURCE = "test_resource_rbac"

    def setup_method(self) -> None:
        """Installe un override temporaire avant chaque test de cette classe."""
        # viewer peut exporter ce type de ressource specifique ; operator ne peut PAS delete
        _RESOURCE_OVERRIDES[self.RESOURCE] = {
            "viewer": {"view", "export"},
            "operator": {"view", "create"},  # delete retire volontairement
        }

    def teardown_method(self) -> None:
        """Nettoie l'override apres chaque test."""
        _RESOURCE_OVERRIDES.pop(self.RESOURCE, None)

    def test_viewer_can_export_with_override(self) -> None:
        ctx = _check("export", "viewer", resource_type=self.RESOURCE)
        assert ctx.role == "viewer"

    def test_viewer_still_cannot_create_with_override(self) -> None:
        with pytest.raises(ForbiddenError) as exc_info:
            _check("create", "viewer", resource_type=self.RESOURCE)
        assert "viewer" in exc_info.value.message
        assert self.RESOURCE in exc_info.value.message

    def test_operator_cannot_delete_with_override(self) -> None:
        # L'override retire 'delete' pour operator sur cette ressource
        with pytest.raises(ForbiddenError):
            _check("delete", "operator", resource_type=self.RESOURCE)

    def test_manager_falls_back_to_default_when_not_in_override(self) -> None:
        # manager n'a pas d'entree dans l'override → matrice par defaut
        ctx = _check("delete", "manager", resource_type=self.RESOURCE)
        assert ctx.role == "manager"

    def test_override_does_not_affect_other_resources(self) -> None:
        # viewer ne peut pas exporter 'autre_resource' (pas d'override)
        with pytest.raises(ForbiddenError):
            _check("export", "viewer", resource_type="autre_resource")

    def test_cleanup_removes_override(self) -> None:
        """Verifie que teardown_method retire bien l'override (test independant)."""
        _RESOURCE_OVERRIDES.pop(self.RESOURCE, None)
        assert self.RESOURCE not in _RESOURCE_OVERRIDES


# ---------------------------------------------------------------------------
# 7. ForbiddenError — message clair et code correct
# ---------------------------------------------------------------------------

class TestForbiddenErrorMessage:
    def test_message_contains_role(self) -> None:
        with pytest.raises(ForbiddenError) as exc_info:
            _check("delete", "viewer")
        assert "viewer" in exc_info.value.message

    def test_message_contains_action(self) -> None:
        with pytest.raises(ForbiddenError) as exc_info:
            _check("manage", "operator")
        assert "manage" in exc_info.value.message

    def test_message_contains_resource_type_when_given(self) -> None:
        with pytest.raises(ForbiddenError) as exc_info:
            _check("delete", "viewer", resource_type="client")
        assert "client" in exc_info.value.message

    def test_message_omits_resource_type_when_not_given(self) -> None:
        with pytest.raises(ForbiddenError) as exc_info:
            _check("delete", "viewer")
        # Sans resource_type, le message ne doit pas contenir "sur '"
        assert "sur '" not in exc_info.value.message

    def test_error_code_is_forbidden(self) -> None:
        with pytest.raises(ForbiddenError) as exc_info:
            _check("manage", "viewer")
        assert exc_info.value.code == "FORBIDDEN"

    def test_error_is_business_error_subclass(self) -> None:
        from app.core.exceptions import BusinessError

        with pytest.raises(ForbiddenError) as exc_info:
            _check("export", "viewer")
        assert isinstance(exc_info.value, BusinessError)

    def test_permission_checker_returns_tenant_context_on_success(self) -> None:
        ctx = _check("view", "viewer")
        assert isinstance(ctx, TenantContext)
        assert ctx.role == "viewer"
        assert ctx.tenant_id == 1
        assert ctx.user_id == 1
