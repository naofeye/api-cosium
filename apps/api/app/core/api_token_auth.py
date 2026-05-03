"""FastAPI dependency : auth via API token (Bearer).

Pattern : `Depends(require_api_scope("read:clients"))` sur les routes
publiques. Retourne `ApiTokenContext` (tenant_id, scopes, token_id).

Distinction avec l'auth utilisateur (cookies JWT) : les routes publiques
n'ont pas de session, pas de tenant switching. Le tenant est fixe par le
token, pas par cookie.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.services import api_token_service

logger = get_logger("api_token_auth")


@dataclass(frozen=True)
class ApiTokenContext:
    """Contexte d'execution pour une requete API publique authentifiee."""

    token_id: int
    tenant_id: int
    scopes: list[str]


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def require_api_scope(*required_scopes: str) -> Callable:
    """Construit une dependency qui valide le token + scope.

    Usage :
        @router.get("/clients", dependencies=[Depends(require_api_scope("read:clients"))])
        def list_clients_public(...): ...

    Pour acceder au contexte (tenant_id) :
        ctx: ApiTokenContext = Depends(require_api_scope("read:clients"))
    """

    def _check(
        authorization: str | None = Header(None),
        db: Session = Depends(get_db),
    ) -> ApiTokenContext:
        raw = _extract_bearer(authorization)
        if not raw:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token API manquant. Header: Authorization: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = api_token_service.verify_api_token(db, raw)
        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token API invalide, revoque ou expire",
                headers={"WWW-Authenticate": "Bearer"},
            )

        for required in required_scopes:
            if not api_token_service.has_scope(token, required):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Scope manquant : {required}",
                )

        return ApiTokenContext(
            token_id=token.id,
            tenant_id=token.tenant_id,
            scopes=list(token.scopes or []),
        )

    return _check
