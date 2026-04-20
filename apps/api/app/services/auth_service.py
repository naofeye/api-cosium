import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.auth import LoginRequest, TokenResponse
from app.models import PasswordResetToken, Tenant, User
from app.repositories import refresh_token_repo, tenant_user_repo, user_repo
from app.security import (
    create_access_token,
    generate_refresh_token,
    get_refresh_token_expiry,
    hash_password,
    verify_password,
)
from app.services import audit_service
from app.services.auth_lockout import (
    check_account_lockout as _check_account_lockout,
    clear_login_attempts as _clear_login_attempts,
    record_failed_login as _record_failed_login,
)

logger = get_logger("auth_service")


def _get_user_tenants(db: Session, user_id: int) -> list[dict]:
    """Retourne tous les tenants actifs auxquels l'user a acces.

    Optimisation N+1 : un seul JOIN TenantUser x Tenant au lieu de N queries.
    """
    from sqlalchemy import select

    from app.models import TenantUser

    rows = db.execute(
        select(Tenant.id, Tenant.name, Tenant.slug, TenantUser.role)
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(
            TenantUser.user_id == user_id,
            TenantUser.is_active.is_(True),
            Tenant.is_active.is_(True),
        )
    ).all()
    return [{"id": r.id, "name": r.name, "slug": r.slug, "role": r.role} for r in rows]


def _is_group_admin(db: Session, user_id: int) -> bool:
    rows = tenant_user_repo.list_admin_active_by_user(db, user_id)
    return len(rows) > 1


def _user_must_have_mfa(db: Session, user_id: int) -> bool:
    """True si l'user est admin dans au moins un tenant avec require_admin_mfa=True.

    Implique que l'user doit avoir MFA active pour se connecter.
    """
    from sqlalchemy import select as sa_select

    from app.models import Tenant, TenantUser

    rows = db.execute(
        sa_select(Tenant.require_admin_mfa)
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(
            TenantUser.user_id == user_id,
            TenantUser.is_active.is_(True),
            TenantUser.role == "admin",
            Tenant.require_admin_mfa.is_(True),
        )
        .limit(1)
    ).first()
    return rows is not None


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
    if not user.totp_enabled and _user_must_have_mfa(db, user.id):
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

    tenants = _get_user_tenants(db, user.id)
    if not tenants:
        raise AuthenticationError("Aucun magasin accessible pour cet utilisateur")

    default_tenant = tenants[0]
    is_admin = _is_group_admin(db, user.id)

    # Revoquer les anciens refresh tokens avant d'en creer un nouveau
    refresh_token_repo.revoke_all_for_user(db, user.id)

    tenant_role = default_tenant["role"]
    access_token = create_access_token(
        user.email,
        tenant_role,
        tenant_id=default_tenant["id"],
        is_group_admin=is_admin,
    )
    refresh_token = generate_refresh_token()
    refresh_token_repo.create(db, refresh_token, user.id, get_refresh_token_expiry())
    db.commit()
    _clear_login_attempts(payload.email)
    logger.info("authentication_success", user_id=user.id, email=user.email, tenant_id=default_tenant["id"])
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

    tenants = _get_user_tenants(db, user.id)
    default_tenant = tenants[0] if tenants else None
    is_admin = _is_group_admin(db, user.id)

    refresh_token_repo.revoke(db, token)
    tenant_role = default_tenant["role"] if default_tenant else user.role
    new_access = create_access_token(
        user.email,
        tenant_role,
        tenant_id=default_tenant["id"] if default_tenant else None,
        is_group_admin=is_admin,
    )
    new_refresh = generate_refresh_token()
    refresh_token_repo.create(db, new_refresh, user.id, get_refresh_token_expiry())
    db.commit()
    logger.info("token_refreshed", user_id=user.id)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        role=tenant_role,
        tenant_id=default_tenant["id"] if default_tenant else None,
        tenant_name=default_tenant["name"] if default_tenant else None,
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

    tenants = _get_user_tenants(db, user.id)
    is_admin = _is_group_admin(db, user.id)

    # Revoquer les anciens refresh tokens lors du switch tenant
    refresh_token_repo.revoke_all_for_user(db, user.id)

    access_token = create_access_token(
        user.email,
        tenant_user.role,
        tenant_id=tenant.id,
        is_group_admin=is_admin,
    )
    refresh_token = generate_refresh_token()
    refresh_token_repo.create(db, refresh_token, user.id, get_refresh_token_expiry())
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


def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> None:
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("user", user_id)
    if not verify_password(old_password, user.password_hash):
        raise AuthenticationError("Ancien mot de passe incorrect")
    user.password_hash = hash_password(new_password)
    # Revoke all refresh tokens
    refresh_token_repo.revoke_all_for_user(db, user_id)
    db.commit()
    tu = tenant_user_repo.get_first_active_by_user(db, user_id)
    if tu:
        audit_service.log_action(db, tu.tenant_id, user_id, "update", "user", user_id)
    logger.info("password_changed", user_id=user_id)


def logout(db: Session, token: str) -> None:
    refresh_token_repo.revoke(db, token)
    db.commit()
    logger.info("user_logged_out")


def request_password_reset(db: Session, email: str) -> None:
    """Always returns None (don't reveal if email exists)."""
    user = user_repo.get_user_by_email(db, email)
    if not user:
        return

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)

    reset = PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
    db.add(reset)
    db.commit()

    from app.integrations.email_templates import render_email
    from app.tasks.email_tasks import send_email_async

    frontend_origin = settings.cors_origins.split(",")[0].strip()
    reset_url = f"{frontend_origin}/reset-password?token={raw_token}"
    body_html = render_email("password_reset.html", reset_url=reset_url)
    send_email_async.delay(
        to=user.email,
        subject="OptiFlow — Reinitialisation de votre mot de passe",
        body_html=body_html,
    )
    logger.info("password_reset_requested", user_id=user.id)


def reset_password(db: Session, token: str, new_password: str) -> None:
    from sqlalchemy import update

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(UTC).replace(tzinfo=None)

    # UPDATE atomique : marque used=True uniquement si encore unused ET non expire.
    # Sur PostgreSQL/SQLite, l'execute renvoie le rowcount. Si 0 → deja utilise ou expire.
    result = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used.is_(False),
            PasswordResetToken.expires_at >= now,
        )
        .values(used=True)
    )
    if result.rowcount == 0:
        raise AuthenticationError("Lien de reinitialisation invalide ou expire")

    reset = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    if not reset:
        raise AuthenticationError("Lien de reinitialisation invalide")

    user = user_repo.get_user_by_id(db, reset.user_id)
    if not user:
        raise AuthenticationError("Utilisateur introuvable")

    user.password_hash = hash_password(new_password)
    refresh_token_repo.revoke_all_for_user(db, user.id)
    db.commit()

    tu = tenant_user_repo.get_first_active_by_user(db, user.id)
    if tu:
        audit_service.log_action(db, tu.tenant_id, user.id, "update", "password_reset", user.id)
    logger.info("password_reset_completed", user_id=user.id)
