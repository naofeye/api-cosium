"""Auth service : authentification (login, refresh, switch tenant, logout) + mots de passe.

Helpers internes :
- `_auth.queries`  : queries tenants/role admin/MFA enforcement
- `_auth.password` : change/request-reset/reset password
"""

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger
from app.domain.schemas.auth import LoginRequest, TokenResponse
from app.models import Tenant, User
from app.repositories import refresh_token_repo, tenant_user_repo, user_repo
from app.security import (
    create_access_token,
    generate_refresh_token,
    get_refresh_token_expiry,
    verify_password,
)
from app.services._auth.password import (
    change_password,
    request_password_reset,
    reset_password,
)
from app.services._auth.queries import (
    get_user_tenants,
    is_group_admin,
    user_must_have_mfa,
)
from app.services.auth_lockout import (
    check_account_lockout as _check_account_lockout,
)
from app.services.auth_lockout import (
    clear_login_attempts as _clear_login_attempts,
)
from app.services.auth_lockout import (
    record_failed_login as _record_failed_login,
)

logger = get_logger("auth_service")

__all__ = [
    "authenticate",
    "change_password",
    "logout",
    "refresh",
    "request_password_reset",
    "reset_password",
    "switch_tenant",
]

# Compat tests : noms prives historiques re-exportes
_get_user_tenants = get_user_tenants
_is_group_admin = is_group_admin
_user_must_have_mfa = user_must_have_mfa


def authenticate(db: Session, payload: LoginRequest) -> TokenResponse:
    _check_account_lockout(payload.email)

    user = user_repo.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        _record_failed_login(payload.email)
        email_hash = hashlib.sha256(payload.email.lower().encode()).hexdigest()[:12]
        logger.warning("authentication_failed", email_hash=email_hash)
        raise AuthenticationError()

    # MFA enforcement : user admin dans un tenant avec require_admin_mfa=True
    # DOIT avoir MFA active. Refus login si non setup.
    if not user.totp_enabled and user_must_have_mfa(db, user.id):
        email_hash = hashlib.sha256(payload.email.lower().encode()).hexdigest()[:12]
        logger.warning("authentication_mfa_enforcement_missing", email_hash=email_hash, user_id=user.id)
        raise AuthenticationError("MFA_SETUP_REQUIRED")

    # MFA check si active sur le compte
    if user.totp_enabled:
        from app.services import mfa_service

        if not payload.totp_code:
            raise AuthenticationError("MFA_CODE_REQUIRED")
        if not mfa_service.verify_login_code(user, payload.totp_code):
            _record_failed_login(payload.email)
            email_hash = hashlib.sha256(payload.email.lower().encode()).hexdigest()[:12]
            logger.warning("authentication_mfa_failed", email_hash=email_hash)
            raise AuthenticationError("Code MFA invalide")
        user.totp_last_used_at = datetime.now(UTC).replace(tzinfo=None)

    tenants = get_user_tenants(db, user.id)
    if not tenants:
        raise AuthenticationError("Aucun magasin accessible pour cet utilisateur")

    default_tenant = tenants[0]
    is_admin = is_group_admin(db, user.id)

    refresh_token_repo.revoke_all_for_user(db, user.id)

    tenant_role = default_tenant["role"]
    access_token = create_access_token(
        user.email,
        tenant_role,
        tenant_id=default_tenant["id"],
        is_group_admin=is_admin,
    )
    refresh_token = generate_refresh_token()
    refresh_token_repo.create(
        db,
        refresh_token,
        user.id,
        get_refresh_token_expiry(),
        tenant_id=default_tenant["id"],
    )
    db.commit()
    _clear_login_attempts(payload.email)
    logger.info("authentication_success", user_id=user.id, tenant_id=default_tenant["id"])
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=tenant_role,
        tenant_id=default_tenant["id"],
        tenant_name=default_tenant["name"],
        available_tenants=tenants,
    )


def refresh(db: Session, token: str) -> TokenResponse:
    rt = refresh_token_repo.get_by_token(db, token)
    if not rt or not refresh_token_repo.is_valid(rt):
        logger.warning("refresh_token_invalid")
        raise AuthenticationError("Refresh token invalide ou expiré")
    user: User | None = user_repo.get_user_by_id(db, rt.user_id)
    if not user or not user.is_active:
        raise AuthenticationError("Utilisateur introuvable ou désactivé")

    tenants = get_user_tenants(db, user.id)
    is_admin = is_group_admin(db, user.id)

    # M2 fix : preserver le tenant courant (celui choisi via switch_tenant ou login)
    # plutot que de retomber sur tenants[0]. Si le token est anterieur a la migration
    # a4b5c6d7e8f9 (rt.tenant_id IS NULL) ou si le user n'a plus acces au tenant
    # initial, on retombe sur tenants[0] pour ne pas casser la session.
    current_tenant: dict | None = None
    if rt.tenant_id is not None:
        current_tenant = next((t for t in tenants if t["id"] == rt.tenant_id), None)
    if current_tenant is None:
        current_tenant = tenants[0] if tenants else None

    refresh_token_repo.revoke(db, token)
    tenant_role = current_tenant["role"] if current_tenant else user.role
    new_access = create_access_token(
        user.email,
        tenant_role,
        tenant_id=current_tenant["id"] if current_tenant else None,
        is_group_admin=is_admin,
    )
    new_refresh = generate_refresh_token()
    refresh_token_repo.create(
        db,
        new_refresh,
        user.id,
        get_refresh_token_expiry(),
        tenant_id=current_tenant["id"] if current_tenant else None,
    )
    db.commit()
    logger.info("token_refreshed", user_id=user.id, tenant_id=current_tenant["id"] if current_tenant else None)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        role=tenant_role,
        tenant_id=current_tenant["id"] if current_tenant else None,
        tenant_name=current_tenant["name"] if current_tenant else None,
        available_tenants=tenants,
    )


def switch_tenant(db: Session, user_id: int, new_tenant_id: int) -> TokenResponse:
    user = user_repo.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise AuthenticationError("Utilisateur introuvable ou désactivé")

    tenant_user = tenant_user_repo.get_active_by_user_and_tenant(db, user_id, new_tenant_id)
    if not tenant_user:
        raise AuthenticationError("Accès refusé : pas d'accès à ce magasin")

    tenant = db.query(Tenant).filter(Tenant.id == new_tenant_id, Tenant.is_active).first()
    if not tenant:
        raise AuthenticationError("Magasin introuvable ou désactivé")

    tenants = get_user_tenants(db, user.id)
    is_admin = is_group_admin(db, user.id)

    refresh_token_repo.revoke_all_for_user(db, user.id)

    access_token = create_access_token(
        user.email,
        tenant_user.role,
        tenant_id=tenant.id,
        is_group_admin=is_admin,
    )
    refresh_token = generate_refresh_token()
    refresh_token_repo.create(
        db,
        refresh_token,
        user.id,
        get_refresh_token_expiry(),
        tenant_id=tenant.id,
    )
    db.commit()
    logger.info("tenant_switched", user_id=user.id, tenant_id=tenant.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=tenant_user.role,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        available_tenants=tenants,
    )


def logout(db: Session, token: str) -> None:
    refresh_token_repo.revoke(db, token)
    db.commit()
    logger.info("user_logged_out")
