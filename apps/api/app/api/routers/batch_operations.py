"""API router for batch PEC operations (Groupes marketing)."""

from datetime import date

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
    description=(
        "Retourne tous les tags Cosium avec le nombre de clients associes. "
        "Filtrage optionnel par date (derniere facture ou creation client)."
    ),
)
def list_marketing_codes(
    date_from: date | None = Query(
        None, description="Date debut (filtre derniere facture ou creation client)"
    ),
    date_to: date | None = Query(
        None, description="Date fin (filtre derniere facture ou creation client)"
    ),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[MarketingCodeResponse]:
    return batch_operation_service.get_available_marketing_codes(
        db,
        tenant_id=tenant_ctx.tenant_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post(
    "/create",
    response_model=BatchOperationResponse,
    status_code=201,
    summary="Creer une operation batch",
    description=(
        "Cree une operation batch pour tous les clients lies a un code marketing. "
        "Filtrage optionnel par date pour restreindre aux clients actifs sur une periode."
    ),
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
        date_from=payload.date_from,
        date_to=payload.date_to,
    )


@router.post(
    "/{batch_id}/process",
    response_model=BatchOperationResponse,
    summary="Traiter un batch (consolidation + pre-controle)",
    description=(
        "Lance la consolidation et le pre-controle pour chaque client du batch. "
        "Si async=true et que le batch depasse 50 clients, le traitement est lance "
        "en arriere-plan via Celery et le batch est retourne avec status='en_cours'."
    ),
)
def process_batch(
    batch_id: int,
    use_async: bool = Query(
        False, alias="async", description="Lancer en arriere-plan pour les gros batches"
    ),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BatchOperationResponse:
    batch = batch_operation_service.get_batch_by_id(
        db, tenant_ctx.tenant_id, batch_id
    )

    if use_async and batch.total_clients > 50:
        from app.tasks.batch_tasks import process_batch_async

        process_batch_async.delay(
            tenant_ctx.tenant_id, batch_id, tenant_ctx.user_id
        )
        return batch

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
    enriched = batch_operation_service.get_batch_summary_enriched(
        db, tenant_id=tenant_ctx.tenant_id, batch_id=batch_id
    )

    try:
        import openpyxl  # noqa: F401
    except ImportError:
        from app.services.batch_export_service import export_batch_csv
        return export_batch_csv(enriched)

    from app.services.batch_export_service import export_batch_excel
    return export_batch_excel(enriched)


    # Export logic extracted to batch_export_service
