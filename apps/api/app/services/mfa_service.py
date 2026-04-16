"""Service MFA/TOTP.

Enrôlement :
  1. GET /auth/mfa/setup → retourne secret + URL otpauth pour QR code
  2. POST /auth/mfa/enable body={code} → valide le code et active MFA
Vérification :
  - Sur login, si user.totp_enabled, requérir code via POST /auth/mfa/verify
  - Sinon, login classique comme avant
"""
from __future__ import annotations

from datetime import UTC, datetime

import pyotp
from sqlalchemy.orm import Session

from app.core.encryption import decrypt, encrypt
from app.core.exceptions import AuthenticationError, BusinessError
from app.core.logging import get_logger
from app.models.user import User

logger = get_logger("mfa")

ISSUER = "OptiFlow AI"


def generate_secret() -> str:
    """Genere un secret TOTP base32 random."""
    return pyotp.random_base32()


def provisioning_uri(email: str, secret: str) -> str:
    """URL otpauth:// pour QR code Google Authenticator / 1Password / Authy."""
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER)


def verify_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verifie un code TOTP. valid_window=1 accepte ±30s de drift."""
    if not code or not code.strip().isdigit() or len(code.strip()) != 6:
        return False
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=valid_window)


def start_enrollment(db: Session, user: User) -> dict:
    """Genere un nouveau secret pour l'user (n'active pas encore MFA)."""
    if user.totp_enabled:
        raise BusinessError("MFA deja active", code="MFA_ALREADY_ENABLED")
    secret = generate_secret()
    user.totp_secret_enc = encrypt(secret)
    db.commit()
    uri = provisioning_uri(user.email, secret)
    logger.info("mfa_enrollment_started", user_id=user.id)
    return {"secret": secret, "otpauth_uri": uri, "issuer": ISSUER}


def enable_mfa(db: Session, user: User, code: str) -> None:
    """Active MFA apres verification du premier code (preuve que l'user a bien scanne)."""
    if user.totp_enabled:
        raise BusinessError("MFA deja active", code="MFA_ALREADY_ENABLED")
    if not user.totp_secret_enc:
        raise BusinessError("Aucun enrolement en cours. Appelez /mfa/setup d'abord.", code="MFA_NOT_ENROLLED")
    secret = decrypt(user.totp_secret_enc)
    if not verify_code(secret, code):
        raise AuthenticationError("Code TOTP invalide")
    user.totp_enabled = True
    user.totp_last_used_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    logger.info("mfa_enabled", user_id=user.id)


def disable_mfa(db: Session, user: User, password_verified: bool) -> None:
    """Desactive MFA (necessite verification password cote caller)."""
    if not password_verified:
        raise AuthenticationError("Mot de passe requis pour desactiver MFA")
    user.totp_enabled = False
    user.totp_secret_enc = None
    user.totp_last_used_at = None
    db.commit()
    logger.info("mfa_disabled", user_id=user.id)


def verify_login_code(user: User, code: str) -> bool:
    """Verifie un code TOTP pendant le flow de login."""
    if not user.totp_enabled or not user.totp_secret_enc:
        return True  # MFA desactive → pas de check
    try:
        secret = decrypt(user.totp_secret_enc)
    except Exception as exc:
        logger.error("mfa_secret_decrypt_failed", user_id=user.id, error=str(exc))
        return False
    return verify_code(secret, code)
