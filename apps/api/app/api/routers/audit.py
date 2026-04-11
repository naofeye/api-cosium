from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.audit import AuditLogListResponse, AuditLogResponse
from app.services import audit_service

router = APIRouter(prefix="/api/v1/audit-logs", tags=["audit"])


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="Consulter les logs d'audit",
    description="Retourne la liste paginee et filtrable des logs d'audit (admin uniquement).",
)
def list_audit_logs(
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: int | None = Query(None),
    user_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> AuditLogListResponse:
    return audit_service.search_logs(
        db,
        tenant_id=tenant_ctx.tenant_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/recent",
    response_model=list[AuditLogResponse],
    summary="Activite recente",
    description="Retourne les dernieres actions pour le fil d'activite.",
)
def recent_activity(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> list[AuditLogResponse]:
    return audit_service.get_recent_activity(db, tenant_ctx.tenant_id, limit)
