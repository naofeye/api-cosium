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


@router.get(
    "/export.csv",
    summary="Export CSV des logs d'audit",
    description="Genere un CSV avec les memes filtres que la liste, max 10000 lignes (RGPD : audit log access).",
)
def export_audit_logs_csv(
    action: str | None = Query(None),
    entity_type: str | None = Query(None),
    entity_id: int | None = Query(None),
    user_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
):
    """Export CSV streaming. Audit log de l'acces enregistre."""
    import csv
    from io import StringIO

    from fastapi.responses import StreamingResponse

    result = audit_service.search_logs(
        db,
        tenant_id=tenant_ctx.tenant_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        page=1,
        page_size=10000,
    )

    # Audit la generation de l'export (RGPD : trace les exports d'audit logs)
    audit_service.log_action(
        db,
        tenant_ctx.tenant_id,
        tenant_ctx.user_id,
        "export_audit",
        "audit_log",
        0,
        new_value={"filters": {"action": action, "entity_type": entity_type, "date_from": date_from, "date_to": date_to}, "count": result.total},
    )
    db.commit()

    def generate():
        buffer = StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(["id", "created_at", "user_email", "action", "entity_type", "entity_id", "old_value", "new_value"])
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        for entry in result.items:
            writer.writerow([
                entry.id,
                entry.created_at.isoformat() if entry.created_at else "",
                entry.user_email or "",
                entry.action,
                entry.entity_type,
                entry.entity_id,
                (entry.old_value or "")[:500],
                (entry.new_value or "")[:500],
            ])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()

    from datetime import datetime
    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

