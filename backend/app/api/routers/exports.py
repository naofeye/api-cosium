from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.services import export_service

router = APIRouter(prefix="/api/v1/exports", tags=["exports"])


@router.get(
    "/balance-clients",
    summary="Export Balance Clients (Excel)",
    description="Genere un rapport Excel des soldes clients impayes.",
)
def export_balance_clients(
    date_from: date | None = Query(None, description="Date de debut (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Date de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> StreamingResponse:
    data = export_service.export_balance_clients_xlsx(
        db, tenant_id=tenant_ctx.tenant_id, date_from=date_from, date_to=date_to,
    )
    filename = f"balance_clients_{datetime.now(UTC).strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/balance-clients-pdf",
    summary="Export Balance Clients (PDF)",
    description="Genere un rapport PDF des soldes clients impayes.",
)
def export_balance_clients_pdf(
    date_from: date | None = Query(None, description="Date de debut (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Date de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> StreamingResponse:
    data = export_service.export_balance_clients_pdf(
        db, tenant_id=tenant_ctx.tenant_id, date_from=date_from, date_to=date_to,
    )
    filename = f"balance_clients_{datetime.now(UTC).strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        iter([data]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/dashboard-pdf",
    summary="Export Dashboard PDF",
    description="Genere un rapport PDF du tableau de bord avec tous les KPIs.",
)
def export_dashboard_pdf(
    date_from: datetime | None = Query(None, description="Date de debut"),
    date_to: datetime | None = Query(None, description="Date de fin"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> StreamingResponse:
    data = export_service.export_dashboard_pdf(
        db, tenant_id=tenant_ctx.tenant_id, date_from=date_from, date_to=date_to,
    )
    filename = f"dashboard_optiflow_{datetime.now(UTC).strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        iter([data]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/monthly-report",
    summary="Export Rapport Mensuel (PDF)",
    description="Genere un rapport PDF mensuel complet avec KPIs, activite, top clients, balance agee et stats opticiens.",
)
def export_monthly_report(
    month: str = Query(
        ...,
        description="Mois au format YYYY-MM (ex: 2026-03)",
        pattern=r"^\d{4}-\d{2}$",
    ),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> StreamingResponse:
    parts = month.split("-")
    year = int(parts[0])
    month_num = int(parts[1])
    if month_num < 1 or month_num > 12:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Mois invalide (1-12)")
    data = export_service.export_monthly_report_pdf(
        db, tenant_id=tenant_ctx.tenant_id, year=year, month=month_num,
    )
    filename = f"rapport_mensuel_{month}.pdf"
    return StreamingResponse(
        iter([data]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/fec",
    summary="Export FEC (Fichier des Ecritures Comptables)",
    description="Genere un fichier FEC conforme a la reglementation fiscale francaise.",
)
def export_fec(
    date_from: date = Query(..., description="Date de debut (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Date de fin (YYYY-MM-DD)"),
    siren: str = Query("000000000", description="Numero SIREN de l'entreprise"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> StreamingResponse:
    data = export_service.generate_fec(
        db,
        tenant_id=tenant_ctx.tenant_id,
        date_from=date_from,
        date_to=date_to,
        siren=siren,
    )
    date_cloture = date_to.strftime("%Y%m%d")
    filename = f"FEC_{siren}_{date_cloture}.txt"
    return StreamingResponse(
        iter([data]),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/clients-complet",
    summary="Export Clients Complet (Excel)",
    description="Genere un fichier Excel avec toutes les donnees clients.",
)
def export_clients_complet(
    date_from: date | None = Query(None, description="Date de debut (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Date de fin (YYYY-MM-DD)"),
    has_email: bool | None = Query(None, description="Filtrer par presence d'email"),
    has_cosium_id: bool | None = Query(None, description="Filtrer par presence d'ID Cosium"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> StreamingResponse:
    data = export_service.export_clients_complet_xlsx(
        db,
        tenant_id=tenant_ctx.tenant_id,
        date_from=date_from,
        date_to=date_to,
        has_email=has_email,
        has_cosium_id=has_cosium_id,
    )
    filename = f"clients_complet_{datetime.now(UTC).strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
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
