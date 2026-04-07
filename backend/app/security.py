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


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def get_refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
