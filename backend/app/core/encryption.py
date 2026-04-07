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
