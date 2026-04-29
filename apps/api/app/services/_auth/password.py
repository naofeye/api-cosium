"""Gestion des mots de passe : change_password, password reset (request + reset)."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.logging import get_logger
from app.models import PasswordResetToken
from app.repositories import refresh_token_repo, tenant_user_repo, user_repo
from app.security import hash_password, verify_password
from app.services import audit_service

logger = get_logger("auth_service")


def change_password(db: Session, user_id: int, old_password: str, new_password: str) -> None:
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError("user", user_id)
    if not verify_password(old_password, user.password_hash):
        raise AuthenticationError("Ancien mot de passe incorrect")
    user.password_hash = hash_password(new_password)
    refresh_token_repo.revoke_all_for_user(db, user_id)
    db.commit()
    tu = tenant_user_repo.get_first_active_by_user(db, user_id)
    if tu:
        audit_service.log_action(db, tu.tenant_id, user_id, "update", "user", user_id)
    logger.info("password_changed", user_id=user_id)


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

    # Utilise frontend_base_url si configure, sinon fallback sur le premier
    # cors_origins (utile en dev local).
    frontend_origin = (
        settings.frontend_base_url.strip()
        or settings.cors_origins.split(",")[0].strip()
    )
    reset_url = f"{frontend_origin}/reset-password?token={raw_token}"
    body_html = render_email("password_reset.html", reset_url=reset_url)
    send_email_async.delay(
        to=user.email,
        subject="OptiFlow — Reinitialisation de votre mot de passe",
        body_html=body_html,
    )
    logger.info("password_reset_requested", user_id=user.id)


def reset_password(db: Session, token: str, new_password: str) -> None:
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
