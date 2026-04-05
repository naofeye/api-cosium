from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.services import export_service

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])


@router.get(
    "/{entity_type}",
    summary="Exporter des donnees",
    description="Exporte les donnees d'une entite au format CSV ou XLSX.",
)
def export_data(
    entity_type: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    if format == "xlsx":
        data = export_service.export_to_xlsx(
            db,
            tenant_id=tenant_ctx.tenant_id,
            entity_type=entity_type,
            date_from=date_from,
            date_to=date_to,
        )
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={entity_type}.xlsx"},
        )
    data = export_service.export_to_csv(
        db,
        tenant_id=tenant_ctx.tenant_id,
        entity_type=entity_type,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={entity_type}.csv"},
    )
