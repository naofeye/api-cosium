"""Router for Cosium document access — local (MinIO) and proxied.

Documents are downloaded from Cosium (GET only) and cached in MinIO.
The frontend checks local storage first, then falls back to Cosium proxy.
All document content is proxied through the backend — the frontend
NEVER calls Cosium directly (CORS disabled on Cosium side).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_
from sqlalchemy import select as sa_select
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
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services.erp_sync_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("cosium_documents_router")

router = APIRouter(prefix="/api/v1/cosium-documents", tags=["cosium-documents"])


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
    from app.models.client import Customer
    from app.models.cosium_data import CosiumDocument
    from app.models.document_extraction import DocumentExtraction

    # Base query: left join with customer and extraction
    query = (
        sa_select(
            CosiumDocument,
            Customer.first_name,
            Customer.last_name,
            DocumentExtraction.document_type,
            DocumentExtraction.classification_confidence,
        )
        .outerjoin(Customer, (Customer.id == CosiumDocument.customer_id) & (Customer.tenant_id == tenant_ctx.tenant_id))
        .outerjoin(
            DocumentExtraction,
            (DocumentExtraction.cosium_document_id == CosiumDocument.cosium_document_id)
            & (DocumentExtraction.tenant_id == tenant_ctx.tenant_id),
        )
        .where(CosiumDocument.tenant_id == tenant_ctx.tenant_id)
    )

    count_base = sa_select(func.count(CosiumDocument.id)).where(
        CosiumDocument.tenant_id == tenant_ctx.tenant_id
    )

    if search:
        pattern = f"%{search}%"
        search_filter = or_(
            CosiumDocument.name.ilike(pattern),
            (Customer.first_name + " " + Customer.last_name).ilike(pattern),
            (Customer.last_name + " " + Customer.first_name).ilike(pattern),
        )
        query = query.where(search_filter)
        # For count with search, need the join too
        count_base = (
            sa_select(func.count(CosiumDocument.id))
            .outerjoin(Customer, (Customer.id == CosiumDocument.customer_id) & (Customer.tenant_id == tenant_ctx.tenant_id))
            .where(CosiumDocument.tenant_id == tenant_ctx.tenant_id)
            .where(search_filter)
        )

    if doc_type:
        query = query.where(DocumentExtraction.document_type == doc_type)
        count_base = (
            sa_select(func.count(CosiumDocument.id))
            .outerjoin(
                DocumentExtraction,
                (DocumentExtraction.cosium_document_id == CosiumDocument.cosium_document_id)
                & (DocumentExtraction.tenant_id == tenant_ctx.tenant_id),
            )
            .where(CosiumDocument.tenant_id == tenant_ctx.tenant_id)
            .where(DocumentExtraction.document_type == doc_type)
        )

    total = db.scalar(count_base) or 0

    # Total size
    size_q = sa_select(func.coalesce(func.sum(CosiumDocument.size_bytes), 0)).where(
        CosiumDocument.tenant_id == tenant_ctx.tenant_id
    )
    total_size = db.scalar(size_q) or 0

    # Type counts
    type_count_q = (
        sa_select(DocumentExtraction.document_type, func.count(DocumentExtraction.id))
        .join(
            CosiumDocument,
            (DocumentExtraction.cosium_document_id == CosiumDocument.cosium_document_id)
            & (DocumentExtraction.tenant_id == CosiumDocument.tenant_id),
        )
        .where(DocumentExtraction.tenant_id == tenant_ctx.tenant_id)
        .where(DocumentExtraction.document_type.isnot(None))
        .group_by(DocumentExtraction.document_type)
    )
    type_counts_raw = db.execute(type_count_q).all()
    type_counts = {str(row[0]): int(row[1]) for row in type_counts_raw if row[0]}

    # Paginate
    query = query.order_by(CosiumDocument.synced_at.desc())
    offset = (page - 1) * page_size
    rows = db.execute(query.offset(offset).limit(page_size)).all()

    items = []
    for row in rows:
        doc = row[0]
        first_name = row[1] or ""
        last_name = row[2] or ""
        d_type = row[3]
        d_confidence = row[4]
        customer_name = f"{first_name} {last_name}".strip() or None
        items.append(
            AllDocumentItem(
                id=doc.id,
                customer_cosium_id=doc.customer_cosium_id,
                customer_id=doc.customer_id,
                customer_name=customer_name,
                cosium_document_id=doc.cosium_document_id,
                name=doc.name,
                content_type=doc.content_type,
                size_bytes=doc.size_bytes,
                document_type=d_type,
                classification_confidence=d_confidence,
                synced_at=doc.synced_at.isoformat() if doc.synced_at else None,
            )
        )

    return AllDocumentsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_size_bytes=int(total_size),
        type_counts=type_counts,
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
    from app.integrations.storage import storage
    from app.models.cosium_data import CosiumDocument
    from app.services.cosium_document_sync import BUCKET

    doc = (
        db.query(CosiumDocument)
        .filter(CosiumDocument.id == document_id, CosiumDocument.tenant_id == tenant_ctx.tenant_id)
        .first()
    )
    if not doc or not doc.minio_key:
        raise HTTPException(status_code=404, detail="Document introuvable localement.")

    try:
        content = storage.download_file(BUCKET, doc.minio_key)
    except Exception as e:
        logger.error("local_doc_download_failed", document_id=document_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors du telechargement du document.") from e

    safe_name = doc.name or f"document_{doc.cosium_document_id}"
    return Response(
        content=content,
        media_type=doc.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
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
    from app.models.cosium_data import CosiumDocument
    from app.repositories import document_extraction_repo

    # Get all local document IDs for this customer
    cosium_doc_ids = [
        row[0]
        for row in db.execute(
            sa_select(CosiumDocument.cosium_document_id).where(
                CosiumDocument.tenant_id == tenant_ctx.tenant_id,
                CosiumDocument.customer_cosium_id == customer_cosium_id,
            )
        ).all()
    ]

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
    connector, tenant = _get_connector_for_tenant(db, tenant_ctx.tenant_id)
    _authenticate_connector(connector, tenant)

    if not isinstance(connector, CosiumConnector):
        raise HTTPException(status_code=400, detail="Le connecteur ERP ne supporte pas les documents Cosium.")

    try:
        docs = connector.get_customer_documents(customer_cosium_id)
    except Exception as e:
        logger.error("cosium_documents_fetch_failed", customer_id=customer_cosium_id, error=str(e))
        raise HTTPException(status_code=502, detail="Impossible de recuperer les documents depuis Cosium.") from e

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
    # Check local cache first
    from app.models.cosium_data import CosiumDocument

    local_doc = (
        db.query(CosiumDocument)
        .filter(
            CosiumDocument.tenant_id == tenant_ctx.tenant_id,
            CosiumDocument.customer_cosium_id == customer_cosium_id,
            CosiumDocument.cosium_document_id == document_id,
        )
        .first()
    )

    if local_doc and local_doc.minio_key:
        # Serve from MinIO
        try:
            from app.integrations.storage import storage
            from app.services.cosium_document_sync import BUCKET

            content = storage.download_file(BUCKET, local_doc.minio_key)
            safe_name = local_doc.name or f"cosium_doc_{document_id}.pdf"
            return Response(
                content=content,
                media_type=local_doc.content_type or "application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
            )
        except Exception:
            logger.warning("local_doc_fallback_to_cosium", document_id=document_id)
            # Fall through to Cosium proxy

    # Proxy from Cosium
    connector, tenant = _get_connector_for_tenant(db, tenant_ctx.tenant_id)
    _authenticate_connector(connector, tenant)

    if not isinstance(connector, CosiumConnector):
        raise HTTPException(status_code=400, detail="Le connecteur ERP ne supporte pas les documents Cosium.")

    try:
        content = connector.get_document_content(customer_cosium_id, document_id)
    except Exception as e:
        logger.error(
            "cosium_document_download_failed",
            customer_id=customer_cosium_id,
            document_id=document_id,
            error=str(e),
        )
        raise HTTPException(status_code=502, detail="Impossible de telecharger le document depuis Cosium.") from e

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=cosium_doc_{document_id}.pdf"},
    )
