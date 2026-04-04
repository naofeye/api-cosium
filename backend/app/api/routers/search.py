from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.search import SearchResponse
from app.services import search_service

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def global_search(
    q: str = Query("", min_length=0, max_length=200),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> SearchResponse:
    return search_service.global_search(db, tenant_id=tenant_ctx.tenant_id, query=q)
