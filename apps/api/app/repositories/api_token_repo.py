"""Repository API tokens : queries SQL."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api_token import ApiToken

_TOKEN_WRITABLE = frozenset({"name", "description", "scopes", "expires_at", "revoked"})


def list_tokens(db: Session, tenant_id: int) -> list[ApiToken]:
    return list(
        db.scalars(
            select(ApiToken)
            .where(ApiToken.tenant_id == tenant_id)
            .order_by(ApiToken.created_at.desc())
        ).all()
    )


def get_token(db: Session, tenant_id: int, token_id: int) -> ApiToken | None:
    return db.scalars(
        select(ApiToken).where(
            ApiToken.id == token_id, ApiToken.tenant_id == tenant_id
        )
    ).first()


def create_token(
    db: Session,
    *,
    tenant_id: int,
    name: str,
    prefix: str,
    hashed_token: str,
    scopes: list[str],
    description: str | None,
    expires_at: Any | None,
    created_by_user_id: int | None,
) -> ApiToken:
    token = ApiToken(
        tenant_id=tenant_id,
        name=name,
        prefix=prefix,
        hashed_token=hashed_token,
        scopes=scopes,
        description=description,
        expires_at=expires_at,
        created_by_user_id=created_by_user_id,
    )
    db.add(token)
    db.flush()
    db.refresh(token)
    return token


def update_token(
    db: Session, token: ApiToken, fields: dict[str, Any]
) -> ApiToken:
    for key, value in fields.items():
        if key in _TOKEN_WRITABLE and value is not None:
            setattr(token, key, value)
    db.flush()
    db.refresh(token)
    return token


def delete_token(db: Session, token: ApiToken) -> None:
    db.delete(token)
    db.flush()
