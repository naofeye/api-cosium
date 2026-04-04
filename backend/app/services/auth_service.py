import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.auth import LoginRequest, TokenResponse
from app.models import PasswordResetToken, RefreshToken, TenantUser, User
from app.repositories import refresh_token_repo, user_repo
from app.security import (
    create_access_token,
    generate_refresh_token,
    get_refresh_token_expiry,
    hash_password,
    verify_password,
)
from app.services import audit_service

logger = get_logger("auth_service")


def _get_user_tenants(db: Session, user_id: int) -> list[dict]:
    rows = db.query(TenantUser).filter(TenantUser.user_id == user_id, TenantUser.is_active).all()
    from app.models import Tenant

    result = []
    for tu in rows:
        t = db.query(Tenant).filter(Tenant.id == tu.tenant_id, Tenant.is_active).first()
        if t:
            result.append({"id": t.id, "name": t.name, "slug": t.slug, "role": tu.role})
    return result


def _is_group_admin(db: Session, user_id: int) -> bool:
    rows = (
        db.query(TenantUser)
        .filter(TenantUser.user_id == user_id, TenantUser.role == "admin", TenantUser.is_active)
        .all()
    )
    return len(rows) > 1


def authenticate(db: Session, payload: LoginRequest) -> TokenResponse:
    user = user_repo.get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        logger.warning("authentication_failed", email=payload.email)
        raise AuthenticationError()

    tenants = _get_user_tenants(db, user.id)
    if not tenants:
        raise AuthenticationError("Aucun magasin accessible pour cet utilisateur")

    default_tenant = tenants[0]
    is_admin = _is_group_admin(db, user.id)

    access_token = create_access_token(
        user.email,
        user.role,
        tenant_id=default_tenant["id"],
        is_group_admin=is_admin,
    )
    refresh_token = generate_refresh_token()
    refresh_token_repo.create(db, refresh_token, user.id, get_refresh_token_expiry())
    logger.info("authentication_success", user_id=user.id, email=user.email, tenant_id=default_tenant["id"])
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
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
    new_access = create_access_token(
        user.email,
        user.role,
        tenant_id=default_tenant["id"] if default_tenant else None,
        is_group_admin=is_admin,
    )
    new_refresh = generate_refresh_token()
    refresh_token_repo.create(db, new_refresh, user.id, get_refresh_token_expiry())
    logger.info("token_refreshed", user_id=user.id)
    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        role=user.role,
        tenant_id=default_tenant["id"] if default_tenant else None,
        tenant_name=default_tenant["name"] if default_tenant else None,
        available_tenants=tenants,
    )


def switch_tenant(db: Session, user_id: int, new_tenant_id: int) -> TokenResponse:
    user = user_repo.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise AuthenticationError("Utilisateur introuvable ou désactivé")

    tenant_user = (
        db.query(TenantUser)
        .filter(TenantUser.user_id == user_id, TenantUser.tenant_id == new_tenant_id, TenantUser.is_active)
        .first()
    )
    if not tenant_user:
        raise AuthenticationError("Accès refusé : pas d'accès à ce magasin")

    from app.models import Tenant

    tenant = db.query(Tenant).filter(Tenant.id == new_tenant_id, Tenant.is_active).first()
    if not tenant:
        raise AuthenticationError("Magasin introuvable ou désactivé")

    tenants = _get_user_tenants(db, user.id)
    is_admin = _is_group_admin(db, user.id)

    access_token = create_access_token(
        user.email,
        user.role,
        tenant_id=tenant.id,
        is_group_admin=is_admin,
    )
    refresh_token = generate_refresh_token()
    refresh_token_repo.create(db, refresh_token, user.id, get_refresh_token_expiry())
    logger.info("tenant_switched", user_id=user.id, tenant_id=tenant.id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        available_tenants=tenants,
    )


def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("user", user_id)
    if not verify_password(old_password, user.password_hash):
        raise AuthenticationError("Ancien mot de passe incorrect")
    user.password_hash = hash_password(new_password)
    # Revoke all refresh tokens
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update({"revoked": True})
    db.commit()
    tu = db.query(TenantUser).filter(TenantUser.user_id == user_id, TenantUser.is_active).first()
    tenant_id = tu.tenant_id if tu else 1
    audit_service.log_action(db, tenant_id, user_id, "update", "user", user_id)
    logger.info("password_changed", user_id=user_id)


def logout(db: Session, token: str) -> None:
    refresh_token_repo.revoke(db, token)
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

    from app.integrations.email_sender import email_sender

    frontend_origin = settings.cors_origins.split(",")[0].strip()
    reset_url = f"{frontend_origin}/reset-password?token={raw_token}"
    email_sender.send_email(
        to=user.email,
        subject="OptiFlow — Reinitialisation de votre mot de passe",
        body_html=(
            "<p>Bonjour,</p>"
            "<p>Cliquez sur le lien ci-dessous pour reinitialiser votre mot de passe :</p>"
            f"<p><a href='{reset_url}'>{reset_url}</a></p>"
            "<p>Ce lien expire dans 1 heure.</p>"
            "<p>Si vous n'avez pas demande cette reinitialisation, ignorez cet email.</p>"
        ),
    )
    logger.info("password_reset_requested", user_id=user.id)


def reset_password(db: Session, token: str, new_password: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    reset = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used.is_(False),
        )
        .first()
    )

    if not reset:
        raise AuthenticationError("Lien de reinitialisation invalide ou expire")
    if reset.expires_at < datetime.now(UTC).replace(tzinfo=None):
        raise AuthenticationError("Lien de reinitialisation expire")

    user = db.query(User).filter(User.id == reset.user_id).first()
    if not user:
        raise AuthenticationError("Utilisateur introuvable")

    user.password_hash = hash_password(new_password)
    reset.used = True
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({"revoked": True})
    db.commit()

    tu = db.query(TenantUser).filter(TenantUser.user_id == user.id, TenantUser.is_active).first()
    tenant_id = tu.tenant_id if tu else 1
    audit_service.log_action(db, tenant_id, user.id, "update", "password_reset", user.id)
    logger.info("password_reset_completed", user_id=user.id)
