"""Endpoint d'orchestration multi-domaine : POST /sync/all.

Délègue à `erp_sync_service.sync_all()` qui orchestre customers + invoices +
payments + prescriptions + reference avec isolation d'erreurs par domaine.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.redis_cache import release_lock
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.sync import SyncAllResult
from app.services import erp_sync_service

from ._helpers import acquire_sync_lock, invalidate_tenant_caches

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.post(
    "/all",
    response_model=SyncAllResult,
    summary="Synchroniser tout (incremental)",
    description=(
        "Lance une synchronisation incrementale de toutes les donnees ERP. "
        "Seules les nouvelles donnees sont telechargees. "
        "Passer full=true pour forcer un re-telechargement complet."
    ),
)
def sync_all(
    full: bool = False,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
):
    lock_key = f"sync:all:{tenant_ctx.tenant_id}"
    acquire_sync_lock(
        lock_key,
        "Une synchronisation complete est deja en cours. Veuillez patienter.",
        ttl=1200,
    )
    try:
        results = erp_sync_service.sync_all(
            db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id, full=full,
        )
        invalidate_tenant_caches(tenant_ctx.tenant_id)
        has_errors = bool(results.pop("has_errors", False))
        result = SyncAllResult(**results, has_errors=has_errors)
        if has_errors:
            return JSONResponse(
                status_code=207,
                content=result.model_dump(mode="json"),
            )
        return result
    finally:
        release_lock(lock_key)
