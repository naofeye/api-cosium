"""Endpoints de synchronisation des données de référence Cosium."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.cosium_reference import ReferenceSyncAllResult
from app.services import cosium_reference_sync

router = APIRouter(prefix="/api/v1/cosium", tags=["cosium-reference"])


@router.post(
    "/sync-reference",
    response_model=ReferenceSyncAllResult,
    summary="Synchroniser toutes les donnees de reference",
)
def sync_reference(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> ReferenceSyncAllResult:
    result = cosium_reference_sync.sync_all_reference(
        db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id
    )
    return ReferenceSyncAllResult(**result)


@router.post("/sync-customer-tags", summary="Synchroniser les tags par client")
def sync_customer_tags_endpoint(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> dict:
    return cosium_reference_sync.sync_customer_tags(
        db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id
    )
