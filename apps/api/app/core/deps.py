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

    # Verifier le token_version : permet de revoquer en bloc les JWT
    # d'un utilisateur (logout-everywhere, password change, compromise).
    token_version = payload.get("tv", 0)
    if token_version != getattr(user, "token_version", 0):
        raise AuthenticationError("Session revoquee. Reconnectez-vous.")

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
        if resource_type and resource_type in _RESOURCE_OVERRIDES and role in _RESOURCE_OVERRIDES[resource_type]:
            allowed = _RESOURCE_OVERRIDES[resource_type][role]
        else:
            allowed = _ROLE_PERMISSIONS.get(role, set())
        if action not in allowed:
            raise ForbiddenError(
                f"Acces refuse : le role '{role}' ne peut pas effectuer '{action}'"
                + (f" sur '{resource_type}'" if resource_type else "")
            )
        return tenant_ctx

    return permission_checker


# ---------------------------------------------------------------------------
# Resource ownership : defense en profondeur
# ---------------------------------------------------------------------------
# Map "resource_type" -> (model class, query pattern). Permet de verifier
# explicitement au niveau du router que la ressource demandee appartient
# bien au tenant courant. C'est redondant avec les filtres tenant_id dans
# les repos (qui restent la source de verite), mais ca offre une 2eme ligne
# de defense contre les bugs de developpement futurs (ex: un repo qui
# oublierait le filtre tenant_id).

def assert_resource_owned(
    db: Session,
    resource_type: str,
    resource_id: int,
    tenant_id: int,
) -> None:
    """Leve ForbiddenError si la ressource n'appartient pas au tenant courant.

    A appeler au DEBUT de tout router qui modifie une ressource sensible.
    Pas de SELECT * : seul l'id et tenant_id sont charges via une requete legere.

    Resources supportees : client, case, devis, facture, pec, payment, document,
    interaction, segment, campaign.
    """
    from sqlalchemy import select

    from app.models import (
        Campaign,
        Case,
        Customer,
        Devis,
        Document,
        Facture,
        Interaction,
        Payment,
        PecRequest,
        Segment,
    )

    model_map = {
        "client": Customer,
        "customer": Customer,
        "case": Case,
        "devis": Devis,
        "facture": Facture,
        "pec": PecRequest,
        "payment": Payment,
        "document": Document,
        "interaction": Interaction,
        "segment": Segment,
        "campaign": Campaign,
    }
    model = model_map.get(resource_type)
    if model is None:
        # Pas de garde-fou pour ce type — laisser passer (les repos filtreront).
        # On ne crash pas pour ne pas casser les routes legitimes non listees.
        return

    found = db.scalar(
        select(model.id).where(model.id == resource_id, model.tenant_id == tenant_id)
    )
    if found is None:
        raise ForbiddenError(
            f"Acces refuse : {resource_type} #{resource_id} introuvable ou n'appartient pas a ce magasin."
        )


def require_resource_ownership(resource_type: str, action: str) -> Callable:
    """FastAPI dependency : check role permission AND resource ownership.

    L'id de la ressource est lu depuis les path params en suivant la convention
    `{resource_type}_id` ou `id`.

    Usage :
        @router.delete(
            "/clients/{client_id}",
            dependencies=[Depends(require_resource_ownership("client", "delete"))],
        )
    """
    from app.core.tenant_context import TenantContext, get_tenant_context

    def checker(
        request: Request,
        db: Session = Depends(get_db),
        tenant_ctx: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        # Etape 1 : permission RBAC
        role = tenant_ctx.role
        if resource_type in _RESOURCE_OVERRIDES and role in _RESOURCE_OVERRIDES[resource_type]:
            allowed = _RESOURCE_OVERRIDES[resource_type][role]
        else:
            allowed = _ROLE_PERMISSIONS.get(role, set())
        if action not in allowed:
            raise ForbiddenError(
                f"Acces refuse : le role '{role}' ne peut pas effectuer '{action}' sur '{resource_type}'"
            )

        # Etape 2 : resource ownership
        path = request.path_params
        resource_id_raw = path.get(f"{resource_type}_id") or path.get("id")
        if resource_id_raw is None:
            return tenant_ctx
        try:
            resource_id = int(resource_id_raw)
        except (TypeError, ValueError) as exc:
            raise ForbiddenError(
                f"Identifiant {resource_type} invalide : {resource_id_raw}"
            ) from exc
        assert_resource_owned(db, resource_type, resource_id, tenant_ctx.tenant_id)
        return tenant_ctx

    return checker
