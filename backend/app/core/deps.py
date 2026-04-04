from collections.abc import Callable

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ForbiddenError
from app.db.session import get_db
from app.models import User
from app.repositories import user_repo
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    # Prefer Authorization header, fallback to httpOnly cookie
    if not token:
        token = request.cookies.get("optiflow_token")
    if not token:
        raise AuthenticationError("Token manquant")
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expiré") from None
    except jwt.InvalidTokenError:
        raise AuthenticationError("Token invalide") from None

    email: str | None = payload.get("sub")
    if email is None:
        raise AuthenticationError("Token invalide")

    user = user_repo.get_user_by_email(db, email)
    if user is None or not user.is_active:
        raise AuthenticationError("Utilisateur introuvable ou désactivé")
    return user


def require_role(*roles: str) -> Callable:
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise ForbiddenError("Acces refuse : role insuffisant")
        return current_user

    return role_checker


def require_tenant_role(*roles: str) -> Callable:
    from app.core.tenant_context import TenantContext, get_tenant_context

    def role_checker(tenant_ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if tenant_ctx.role not in roles:
            raise ForbiddenError("Acces refuse : role insuffisant pour ce magasin")
        return tenant_ctx

    return role_checker
