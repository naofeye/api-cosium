import logging

from cryptography.fernet import Fernet

from app.core.config import settings

logger = logging.getLogger("encryption")


def get_fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        if settings.app_env in ("production", "staging"):
            raise RuntimeError(
                "ENCRYPTION_KEY est obligatoire en production/staging. "
                "Generer avec : python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        # Dev fallback — cle derivee stable pour le dev local uniquement
        import base64
        import hashlib

        logger.warning("ENCRYPTION_KEY non defini — fallback dev actif (NE PAS UTILISER EN PRODUCTION)")
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest()).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return get_fernet().decrypt(ciphertext.encode()).decode()


# ---------------------------------------------------------------------------
# SQLAlchemy TypeDecorator — transparent column encryption
# ---------------------------------------------------------------------------

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


class EncryptedString(TypeDecorator):
    """Transparent Fernet encryption for SQLAlchemy string columns.

    Data is encrypted on write and decrypted on read. NULL values pass through.
    The database column stores base64-encoded ciphertext (~2-3x plaintext size).
    """

    impl = String
    cache_ok = True

    def __init__(self, length: int = 500, **kwargs):
        super().__init__(length=length, **kwargs)

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return encrypt(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        try:
            return decrypt(value)
        except Exception as exc:
            # En prod/staging, ne pas masquer une valeur en clair : forcer la
            # remediation. En dev/test, fallback historique pour les fixtures
            # non chiffrees (migration period).
            if settings.app_env in ("production", "staging"):
                logger.error(
                    "encrypted_string_decrypt_failed",
                    extra={"value_prefix": value[:8], "error": str(exc)},
                )
                raise
            logger.warning(
                "encrypted_string_decrypt_failed_fallback_plaintext",
                extra={"value_prefix": value[:8], "error": str(exc)},
            )
            return value
