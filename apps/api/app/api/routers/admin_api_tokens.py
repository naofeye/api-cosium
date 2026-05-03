"""Admin CRUD API tokens. Role admin/manager requis."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.api_token import (
    ALLOWED_SCOPES,
    AllowedScopesResponse,
    ApiTokenCreate,
    ApiTokenCreatedResponse,
    ApiTokenResponse,
    ApiTokenUpdate,
)
from app.repositories import api_token_repo
from app.services.api_token_service import (
    display_prefix,
    generate_raw_token,
    hash_token,
)

router = APIRouter(prefix="/api/v1/admin/api-tokens", tags=["admin-api-tokens"])


@router.get(
    "/scopes",
    response_model=AllowedScopesResponse,
    summary="Liste les scopes disponibles",
)
def list_allowed_scopes() -> AllowedScopesResponse:
    return AllowedScopesResponse(scopes=sorted(ALLOWED_SCOPES))


@router.get(
    "",
    response_model=list[ApiTokenResponse],
    summary="Liste les tokens API du tenant",
)
def list_tokens(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[ApiTokenResponse]:
    rows = api_token_repo.list_tokens(db, ctx.tenant_id)
    return [ApiTokenResponse.model_validate(r) for r in rows]


@router.post(
    "",
    response_model=ApiTokenCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cree un token API (retourne le secret une seule fois)",
    dependencies=[Depends(require_role("admin", "manager"))],
)
def create_token(
    payload: ApiTokenCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> ApiTokenCreatedResponse:
    raw = generate_raw_token()
    token = api_token_repo.create_token(
        db,
        tenant_id=ctx.tenant_id,
        name=payload.name,
        prefix=display_prefix(raw),
        hashed_token=hash_token(raw),
        scopes=payload.scopes,
        description=payload.description,
        expires_at=payload.expires_at,
        created_by_user_id=ctx.user_id,
    )
    db.commit()
    base = ApiTokenResponse.model_validate(token).model_dump()
    return ApiTokenCreatedResponse(**base, token=raw)


@router.get(
    "/{token_id}",
    response_model=ApiTokenResponse,
    summary="Detail token (sans le secret)",
)
def get_token(
    token_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> ApiTokenResponse:
    token = api_token_repo.get_token(db, ctx.tenant_id, token_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Token introuvable")
    return ApiTokenResponse.model_validate(token)


@router.patch(
    "/{token_id}",
    response_model=ApiTokenResponse,
    summary="Modifie un token (revoke, rename, scopes)",
    dependencies=[Depends(require_role("admin", "manager"))],
)
def update_token(
    token_id: int,
    payload: ApiTokenUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> ApiTokenResponse:
    token = api_token_repo.get_token(db, ctx.tenant_id, token_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Token introuvable")
    fields = payload.model_dump(exclude_none=True)
    token = api_token_repo.update_token(db, token, fields)
    db.commit()
    return ApiTokenResponse.model_validate(token)


@router.delete(
    "/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Supprime un token (action irreversible)",
    dependencies=[Depends(require_role("admin", "manager"))],
)
def delete_token(
    token_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    token = api_token_repo.get_token(db, ctx.tenant_id, token_id)
    if token is None:
        raise HTTPException(status_code=404, detail="Token introuvable")
    api_token_repo.delete_token(db, token)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
