import secrets
from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Durees de vie des tokens :
# - Access token : 30 min par defaut (configurable via ACCESS_TOKEN_EXPIRE_MINUTES)
# - Refresh token : 7 jours par defaut (configurable via REFRESH_TOKEN_EXPIRE_DAYS)
# - Les refresh tokens sont revoques au login, switch tenant, et change-password
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(
    subject: str,
    role: str,
    tenant_id: int | None = None,
    is_group_admin: bool = False,
) -> str:
    payload: dict = {
        "sub": subject,
        "role": role,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes),
        "iss": "optiflow",
        "aud": "optiflow-api",
    }
    if tenant_id is not None:
        payload["tenant_id"] = tenant_id
    if is_group_admin:
        payload["is_group_admin"] = True
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        issuer="optiflow",
        audience="optiflow-api",
    )


def _token_blacklist_key(token: str) -> str:
    """Genere une cle unique pour la blacklist a partir du hash SHA-256 du token."""
    import hashlib

    token_hash = hashlib.sha256(token.encode()).hexdigest()[:24]
    return f"blacklist:{token_hash}"


def blacklist_access_token(token: str) -> None:
    """Ajoute un access token a la blacklist Redis (TTL = duree restante du token)."""
    try:
        from app.core.redis_cache import get_redis_client

        r = get_redis_client()
        if r is None:
            return
        payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
        exp = payload.get("exp", 0)
        ttl = max(int(exp - datetime.now(UTC).timestamp()), 60)
        r.setex(_token_blacklist_key(token), ttl, "1")
    except Exception:
        pass


def is_token_blacklisted(token: str) -> bool:
    """Verifie si un access token est dans la blacklist Redis."""
    try:
        from app.core.redis_cache import get_redis_client

        r = get_redis_client()
        if r is None:
            return False
        return bool(r.exists(_token_blacklist_key(token)))
    except Exception:
        return False


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def get_refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
