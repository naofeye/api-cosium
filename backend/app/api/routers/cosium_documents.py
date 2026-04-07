"""Router for Cosium document access — local (MinIO) and proxied.

Documents are downloaded from Cosium (GET only) and cached in MinIO.
The frontend checks local storage first, then falls back to Cosium proxy.
All document content is proxied through the backend — the frontend
NEVER calls Cosium directly (CORS disabled on Cosium side).
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.logging import get_logger
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.domain.schemas.cosium_sync import (
    BulkSyncRequest,
    CosiumDocumentList,
    CosiumDocumentResponse,
    DocumentSyncStatusResponse,
    LocalCosiumDocumentList,
    LocalCosiumDocumentResponse,
)
from app.domain.schemas.ocr import DocumentExtractionResponse
from app.services.cosium_document_query_service import (
    download_document_with_fallback,
    get_customer_extraction_ids,
    get_local_document_content,
    list_all_documents_paginated,
    list_customer_documents_from_cosium,
)

logger = get_logger("cosium_documents_router")

router = APIRouter(prefix="/api/v1/cosium-documents", tags=["cosium-documents"])


# --- Pydantic models for /all endpoint ---


class AllDocumentItem(BaseModel):
    id: int
    customer_cosium_id: int
    customer_id: int | None = None
    customer_name: str | None = None
    cosium_document_id: int
    name: str | None = None
    content_type: str = "application/pdf"
    size_bytes: int = 0
    document_type: str | None = None
    classification_confidence: float | None = None
    synced_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AllDocumentsResponse(BaseModel):
    items: list[AllDocumentItem]
    total: int
    page: int
    page_size: int
    total_size_bytes: int = 0
    type_counts: dict[str, int] = {}


# --- Local document endpoints (MinIO-backed) ---


@router.post(
    "/sync-all",
    summary="Lancer le telechargement de tous les documents Cosium",
    description="Declenche le telechargement en arriere-plan de tous les documents clients depuis Cosium vers MinIO. Lent par design (~1 doc/sec).",
)
def trigger_bulk_sync(
    payload: BulkSyncRequest | None = None,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> dict:
    body = payload or BulkSyncRequest()
    try:
        from app.tasks.sync_tasks import bulk_download_cosium_documents

        task = bulk_download_cosium_documents.delay(
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
            max_customers=body.max_customers,
            delay_docs=body.delay_docs,
            delay_customers=body.delay_customers,
        )
        logger.info(
            "bulk_doc_sync_triggered",
            tenant_id=tenant_ctx.tenant_id,
            task_id=task.id,
            max_customers=body.max_customers,
        )
        return {"status": "started", "task_id": task.id, "message": "Telechargement en cours en arriere-plan"}
    except Exception as e:
        # Celery might not be available — run synchronously as fallback
        logger.warning("celery_unavailable_running_sync", error=str(e))
        from app.services.cosium_document_sync import sync_all_documents

        result = sync_all_documents(
            db=db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
            delay_between_customers=body.delay_customers,
            delay_between_docs=body.delay_docs,
            max_customers=body.max_customers,
        )
        return {"status": "completed", "result": result}


@router.get(
    "/sync-status",
    response_model=DocumentSyncStatusResponse,
    summary="Statut de la synchronisation des documents",
)
def get_sync_status(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> DocumentSyncStatusResponse:
    from app.services.cosium_document_sync import get_sync_status as _get_status

    status = _get_status(db, tenant_ctx.tenant_id)
    return DocumentSyncStatusResponse(**status)


@router.get(
    "/all",
    response_model=AllDocumentsResponse,
    summary="Tous les documents telechargees",
    description="Liste paginee de tous les documents Cosium telechargees localement, avec informations client et type OCR.",
)
def list_all_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche par nom de document ou client"),
    doc_type: str | None = Query(None, description="Filtrer par type de document (ex: ordonnance, devis)"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> AllDocumentsResponse:
    result = list_all_documents_paginated(
        db,
        tenant_ctx.tenant_id,
        page=page,
        page_size=page_size,
        search=search,
        doc_type=doc_type,
    )
    return AllDocumentsResponse(
        items=[AllDocumentItem(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_size_bytes=result["total_size_bytes"],
        type_counts=result["type_counts"],
    )


@router.get(
    "/{customer_cosium_id}/local",
    response_model=LocalCosiumDocumentList,
    summary="Documents locaux d'un client (depuis MinIO)",
)
def list_local_documents(
    customer_cosium_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> LocalCosiumDocumentList:
    from app.services.cosium_document_sync import get_local_documents

    docs = get_local_documents(db, tenant_ctx.tenant_id, customer_cosium_id)
    items = [LocalCosiumDocumentResponse.model_validate(d) for d in docs]
    return LocalCosiumDocumentList(items=items, total=len(items))


@router.get(
    "/local/{document_id}/download",
    summary="Telecharger un document depuis MinIO",
)
def download_local_document(
    document_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> Response:
    content, content_type, filename = get_local_document_content(
        db, tenant_ctx.tenant_id, document_id,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Extractions endpoint ---


@router.get(
    "/{customer_cosium_id}/extractions",
    response_model=list[DocumentExtractionResponse],
    summary="Extractions OCR des documents d'un client",
    description="Retourne les extractions de texte (OCR) et classifications pour les documents d'un client Cosium.",
)
def list_customer_extractions(
    customer_cosium_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> list[DocumentExtractionResponse]:
    from app.repositories import document_extraction_repo

    cosium_doc_ids = get_customer_extraction_ids(
        db, tenant_ctx.tenant_id, customer_cosium_id,
    )
    extractions = document_extraction_repo.list_by_customer_cosium_documents(
        db, cosium_doc_ids, tenant_ctx.tenant_id,
    )
    return [DocumentExtractionResponse.model_validate(e) for e in extractions]


# --- Cosium proxy endpoints (fallback when not cached locally) ---


@router.get(
    "/{customer_cosium_id}",
    response_model=CosiumDocumentList,
    summary="Liste des documents d'un client Cosium",
    description="Retourne la liste des documents disponibles pour un client dans Cosium.",
)
def list_customer_documents(
    customer_cosium_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> CosiumDocumentList:
    docs = list_customer_documents_from_cosium(db, tenant_ctx.tenant_id, customer_cosium_id)
    items = [CosiumDocumentResponse(**d) for d in docs]
    return CosiumDocumentList(items=items, total=len(items))


@router.get(
    "/{customer_cosium_id}/{document_id}/download",
    summary="Telecharger un document Cosium (proxy ou local)",
    description="Sert le document depuis MinIO s'il existe localement, sinon proxy depuis Cosium.",
)
def download_document(
    customer_cosium_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager", "operator")),
) -> Response:
    content, content_type, filename = download_document_with_fallback(
        db, tenant_ctx.tenant_id, customer_cosium_id, document_id,
    )
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
