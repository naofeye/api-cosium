"""Service MFA/TOTP.

Enrôlement :
  1. GET /auth/mfa/setup → retourne secret + URL otpauth pour QR code
  2. POST /auth/mfa/enable body={code} → valide le code et active MFA
Vérification :
  - Sur login, si user.totp_enabled, requérir code via POST /auth/mfa/verify
  - Sinon, login classique comme avant
"""
from __future__ import annotations

import json
import re
import secrets
from datetime import UTC, datetime

import pyotp
from sqlalchemy.orm import Session

from app.core.encryption import decrypt, encrypt
from app.core.exceptions import AuthenticationError, BusinessError
from app.core.logging import get_logger
from app.models.user import User
from app.security import hash_password, verify_password

logger = get_logger("mfa")

ISSUER = "OptiFlow AI"

# Backup codes : 10 codes, 8 hex chars chacun (format XXXX-XXXX affiche).
# Stocke en JSON list de bcrypt hashes. Un code = usage unique (retire du JSON apres consommation).
BACKUP_CODE_COUNT = 10
_BACKUP_CODE_DIGITS = re.compile(r"^[A-Z0-9]{8}$")


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
    """Verifie un code TOTP OU un backup code pendant le flow de login.

    TOTP = 6 digits (012345). Backup = 8 hex chars (ABCD1234).
    Une correspondance backup consomme le code (usage unique).
    """
    if not user.totp_enabled or not user.totp_secret_enc:
        return True  # MFA desactive → pas de check

    cleaned = (code or "").strip().upper().replace("-", "").replace(" ", "")

    # 1) Tentative TOTP standard (6 digits)
    if cleaned.isdigit() and len(cleaned) == 6:
        try:
            secret = decrypt(user.totp_secret_enc)
        except Exception as exc:  # noqa: BLE001 — failure decrypt = refuse le code
            logger.error("mfa_secret_decrypt_failed", user_id=user.id, error=str(exc))
            return False
        return verify_code(secret, cleaned)

    # 2) Fallback backup code (8 hex chars)
    if _BACKUP_CODE_DIGITS.match(cleaned):
        return _consume_backup_code_inplace(user, cleaned)

    return False


# ---------------------------------------------------------------------------
# Backup codes — gestion
# ---------------------------------------------------------------------------


def _generate_single_backup_code() -> str:
    """Genere un code de secours 8 hex chars upper. Ex: A3F2B1C8."""
    return secrets.token_hex(4).upper()


def generate_backup_codes(db: Session, user: User) -> list[str]:
    """Genere 10 codes de secours. Remplace les anciens. Retourne les codes en clair UNE SEULE FOIS.

    L'utilisateur doit les stocker immediatement. Les hashes bcrypt sont persistes
    en DB ; les codes clairs ne sont jamais relus.
    """
    if not user.totp_enabled:
        raise BusinessError("MFA non active. Activez TOTP d'abord.", code="MFA_NOT_ENABLED")

    codes = [_generate_single_backup_code() for _ in range(BACKUP_CODE_COUNT)]
    hashes = [hash_password(c) for c in codes]
    user.totp_backup_codes_hash_json = json.dumps(hashes)
    db.commit()
    logger.info("mfa_backup_codes_generated", user_id=user.id, count=BACKUP_CODE_COUNT)
    return codes


def count_remaining_backup_codes(user: User) -> int:
    """Retourne le nombre de codes de secours encore valides."""
    if not user.totp_backup_codes_hash_json:
        return 0
    try:
        return len(json.loads(user.totp_backup_codes_hash_json))
    except (json.JSONDecodeError, TypeError):
        return 0


def _consume_backup_code_inplace(user: User, cleaned_code: str) -> bool:
    """Verifie et consomme un backup code. Mute user.totp_backup_codes_hash_json si match.

    Le caller est responsable du commit (appele depuis verify_login_code dans un flow
    qui commit user.totp_last_used_at ensuite).
    """
    if not user.totp_backup_codes_hash_json:
        return False
    try:
        hashes: list[str] = json.loads(user.totp_backup_codes_hash_json)
    except (json.JSONDecodeError, TypeError):
        return False
    for h in hashes:
        if verify_password(cleaned_code, h):
            hashes.remove(h)
            user.totp_backup_codes_hash_json = json.dumps(hashes)
            logger.info("mfa_backup_code_consumed", user_id=user.id, remaining=len(hashes))
            return True
    return False
