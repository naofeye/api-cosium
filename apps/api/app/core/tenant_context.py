from dataclasses import dataclass

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import oauth2_scheme
from app.core.exceptions import AuthenticationError
from app.db.session import get_db
from app.models import TenantUser
from app.repositories import user_repo
from app.security import decode_access_token, is_token_blacklisted


@dataclass
class TenantContext:
    tenant_id: int
    user_id: int
    role: str
    is_group_admin: bool


def get_tenant_context(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> TenantContext:
    raw_token = token or request.cookies.get("optiflow_token")
    if not raw_token:
        raise AuthenticationError("Token manquant")
    if is_token_blacklisted(raw_token):
        raise AuthenticationError("Token revoque")
    try:
        payload = decode_access_token(raw_token)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expiré") from None
    except jwt.InvalidTokenError:
        raise AuthenticationError("Token invalide") from None

    email: str | None = payload.get("sub")
    tenant_id: int | None = payload.get("tenant_id")
    if email is None or tenant_id is None:
        raise AuthenticationError("Token invalide : informations manquantes")

    user = user_repo.get_user_by_email(db, email)
    if user is None or not user.is_active:
        raise AuthenticationError("Utilisateur introuvable ou désactivé")

    tenant_user = (
        db.query(TenantUser)
        .filter(
            TenantUser.user_id == user.id,
            TenantUser.tenant_id == tenant_id,
            TenantUser.is_active.is_(True),
        )
        .first()
    )
    if tenant_user is None:
        raise AuthenticationError("Accès refusé : pas d'accès à ce magasin")

    is_group_admin = payload.get("is_group_admin", False)

    return TenantContext(
        tenant_id=tenant_id,
        user_id=user.id,
        role=tenant_user.role,
        is_group_admin=is_group_admin,
    )
