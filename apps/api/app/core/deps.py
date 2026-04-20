from collections.abc import Callable

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ForbiddenError
from app.db.session import get_db
from app.models import TenantUser, User
from app.repositories import user_repo
from app.security import decode_access_token, is_token_blacklisted

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def _extract_token_payload(request: Request, token: str | None) -> dict:
    """Extrait et valide le payload JWT depuis le header ou le cookie."""
    if not token:
        token = request.cookies.get("optiflow_token")
    if not token:
        raise AuthenticationError("Token manquant")
    try:
        return decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expiré") from None
    except jwt.InvalidTokenError:
        raise AuthenticationError("Token invalide") from None


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Authentifie l'utilisateur et verifie son acces au tenant du token."""
    # Recuperer le token brut pour la blacklist
    raw_token = token or request.cookies.get("optiflow_token")
    if raw_token and is_token_blacklisted(raw_token):
        raise AuthenticationError("Token revoque")

    payload = _extract_token_payload(request, token)

    email: str | None = payload.get("sub")
    if email is None:
        raise AuthenticationError("Token invalide")

    user = user_repo.get_user_by_email(db, email)
    if user is None or not user.is_active:
        raise AuthenticationError("Utilisateur introuvable ou désactivé")

    # Verifier que l'utilisateur a acces au tenant du token
    tenant_id: int | None = payload.get("tenant_id")
    if tenant_id is not None:
        tenant_user = (
            db.query(TenantUser)
            .filter(
                TenantUser.user_id == user.id,
                TenantUser.tenant_id == tenant_id,
                TenantUser.is_active.is_(True),
            )
            .first()
        )
        if tenant_user is None:
            raise AuthenticationError("Accès refusé : pas d'accès à ce magasin")

    return user


def require_role(*roles: str) -> Callable:
    """Verifie le role au niveau du tenant (pas le role global)."""
    from app.core.tenant_context import TenantContext, get_tenant_context

    def role_checker(tenant_ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if tenant_ctx.role not in roles:
            raise ForbiddenError("Acces refuse : role insuffisant")
        return tenant_ctx

    return role_checker


def require_tenant_role(*roles: str) -> Callable:
    from app.core.tenant_context import TenantContext, get_tenant_context

    def role_checker(tenant_ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if tenant_ctx.role not in roles:
            raise ForbiddenError("Acces refuse : role insuffisant pour ce magasin")
        return tenant_ctx

    return role_checker


# ---------------------------------------------------------------------------
# Permission-based access control (resource-level RBAC)
# ---------------------------------------------------------------------------

# Default permission matrix: role → set of allowed actions.
# Extend per-resource by overriding in the `overrides` dict below.
_ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"view", "create", "edit", "delete", "export", "manage"},
    "manager": {"view", "create", "edit", "delete", "export"},
    "operator": {"view", "create", "edit"},
    "viewer": {"view"},
}

# Per-resource overrides: resource_type → role → set of actions.
# Example: a viewer can export clients but not cases.
_RESOURCE_OVERRIDES: dict[str, dict[str, set[str]]] = {}


def require_permission(action: str, resource_type: str | None = None) -> Callable:
    """Check that the current tenant role has permission to perform `action`.

    If `resource_type` is given and has overrides in _RESOURCE_OVERRIDES,
    those are used instead of the default matrix.

    Usage in routers:
        @router.delete("/clients/{id}", dependencies=[Depends(require_permission("delete", "client"))])
    """
    from app.core.tenant_context import TenantContext, get_tenant_context

    def permission_checker(tenant_ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        role = tenant_ctx.role
        if resource_type and resource_type in _RESOURCE_OVERRIDES:
            allowed = _RESOURCE_OVERRIDES[resource_type].get(role, set())
        else:
            allowed = _ROLE_PERMISSIONS.get(role, set())
        if action not in allowed:
            raise ForbiddenError(
                f"Acces refuse : le role '{role}' ne peut pas effectuer '{action}'"
                + (f" sur '{resource_type}'" if resource_type else "")
            )
        return tenant_ctx

    return permission_checker
