"""API router for batch PEC operations (OptiSante)."""

import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.batch_operation import (
    BatchCreateRequest,
    BatchOperationResponse,
    BatchPecResult,
    BatchSummaryResponse,
    MarketingCodeResponse,
)
from app.services import batch_operation_service

router = APIRouter(prefix="/api/v1/batch", tags=["batch"])


@router.get(
    "/marketing-codes",
    response_model=list[MarketingCodeResponse],
    summary="Lister les codes marketing disponibles",
    description="Retourne tous les tags Cosium avec le nombre de clients associes.",
)
def list_marketing_codes(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[MarketingCodeResponse]:
    return batch_operation_service.get_available_marketing_codes(
        db, tenant_id=tenant_ctx.tenant_id
    )


@router.post(
    "/create",
    response_model=BatchOperationResponse,
    status_code=201,
    summary="Creer une operation batch",
    description="Cree une operation batch pour tous les clients lies a un code marketing.",
)
def create_batch(
    payload: BatchCreateRequest,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BatchOperationResponse:
    return batch_operation_service.create_batch(
        db,
        tenant_id=tenant_ctx.tenant_id,
        marketing_code=payload.marketing_code,
        label=payload.label,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/{batch_id}/process",
    response_model=BatchOperationResponse,
    summary="Traiter un batch (consolidation + pre-controle)",
    description="Lance la consolidation et le pre-controle pour chaque client du batch.",
)
def process_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BatchOperationResponse:
    return batch_operation_service.process_batch(
        db,
        tenant_id=tenant_ctx.tenant_id,
        batch_id=batch_id,
        user_id=tenant_ctx.user_id,
    )


@router.post(
    "/{batch_id}/prepare-pec",
    response_model=BatchPecResult,
    summary="Preparer les PEC pour les clients prets",
    description="Cree une preparation PEC pour chaque client avec le statut 'pret'.",
)
def prepare_batch_pec(
    batch_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BatchPecResult:
    return batch_operation_service.prepare_batch_pec(
        db,
        tenant_id=tenant_ctx.tenant_id,
        batch_id=batch_id,
        user_id=tenant_ctx.user_id,
    )


@router.get(
    "/{batch_id}",
    response_model=BatchSummaryResponse,
    summary="Detail d'un batch avec tous les items",
    description="Retourne le detail complet d'une operation batch avec le statut de chaque client.",
)
def get_batch_detail(
    batch_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BatchSummaryResponse:
    return batch_operation_service.get_batch_summary(
        db, tenant_id=tenant_ctx.tenant_id, batch_id=batch_id
    )


@router.get(
    "",
    summary="Lister les operations batch",
    description="Liste paginee de toutes les operations batch du tenant.",
)
def list_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    return batch_operation_service.list_batches(
        db,
        tenant_id=tenant_ctx.tenant_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{batch_id}/export",
    summary="Exporter le resume batch en Excel",
    description="Telecharge un fichier Excel avec le detail de l'operation batch.",
)
def export_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> StreamingResponse:
    summary = batch_operation_service.get_batch_summary(
        db, tenant_id=tenant_ctx.tenant_id, batch_id=batch_id
    )

    try:
        import openpyxl
    except ImportError:
        # Fallback to CSV if openpyxl not available
        return _export_csv(summary)

    return _export_excel(summary)


def _export_excel(summary: BatchSummaryResponse) -> StreamingResponse:
    """Generate Excel export of batch summary."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Batch PEC"

    # Header
    headers = [
        "ID", "Client", "Statut", "Score completude",
        "Erreurs", "Alertes", "PEC ID", "Message erreur", "Traite le",
    ]
    ws.append(headers)

    for item in summary.items:
        ws.append([
            item.id,
            item.customer_name or "",
            item.status,
            item.completude_score,
            item.errors_count,
            item.warnings_count,
            item.pec_preparation_id or "",
            item.error_message or "",
            item.processed_at.isoformat() if item.processed_at else "",
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"batch_{summary.batch.id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _export_csv(summary: BatchSummaryResponse) -> StreamingResponse:
    """Fallback CSV export."""
    import csv

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ID", "Client", "Statut", "Score", "Erreurs", "Alertes", "PEC ID", "Erreur",
    ])
    for item in summary.items:
        writer.writerow([
            item.id, item.customer_name or "", item.status,
            item.completude_score, item.errors_count, item.warnings_count,
            item.pec_preparation_id or "", item.error_message or "",
        ])

    content = buf.getvalue().encode("utf-8-sig")
    filename = f"batch_{summary.batch.id}_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
