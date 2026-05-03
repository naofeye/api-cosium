"""Service API tokens : generation, hash, verification, scope check."""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.api_token import ApiToken

logger = get_logger("api_token_service")

# Prefix lisible pour aider l'humain a identifier le token (ex: "opf_AbCd...")
TOKEN_PREFIX = "opf_"
PREFIX_DISPLAY_LEN = 12  # opf_ + 8 chars du raw


def generate_raw_token() -> str:
    """Genere un token URL-safe de ~43 caracteres precedes de 'opf_'."""
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """Hash SHA-256 hex (64 chars) pour stockage en BDD."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def display_prefix(raw: str) -> str:
    """4 premiers caracteres apres 'opf_' pour affichage UI."""
    return raw[:PREFIX_DISPLAY_LEN]


def verify_api_token(db: Session, raw_token: str) -> ApiToken | None:
    """Verifie un token brut et retourne l'ApiToken s'il est valide.

    Validations :
    - lookup par hash SHA-256
    - non-revoke
    - non-expire (si expires_at defini)

    Met a jour `last_used_at` (best-effort, non bloquant si echec).
    """
    if not raw_token:
        return None

    hashed = hash_token(raw_token)
    token = db.query(ApiToken).filter(ApiToken.hashed_token == hashed).first()
    if token is None:
        return None
    if token.revoked:
        return None
    if token.expires_at is not None and token.expires_at < datetime.now(UTC).replace(tzinfo=None):
        return None

    # Best-effort update last_used_at (pas critique si echec)
    try:
        token.last_used_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
    except Exception as exc:
        logger.warning(
            "api_token_last_used_update_failed",
            token_id=token.id,
            error=str(exc),
            error_type=type(exc).__name__,
        )

    return token


def has_scope(token: ApiToken, required: str) -> bool:
    """Verifie qu'un token possede le scope requis (match exact)."""
    return required in (token.scopes or [])
