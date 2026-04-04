from cryptography.fernet import Fernet

from app.core.config import settings


def get_fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        # Dev fallback — generate a stable key from JWT_SECRET
        import base64
        import hashlib

        key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest()).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> str:
    return get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return get_fernet().decrypt(ciphertext.encode()).decode()
