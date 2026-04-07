"""Router for Cosium document access — local (MinIO) and proxied.

Documents are downloaded from Cosium (GET only) and cached in MinIO.
The frontend checks local storage first, then falls back to Cosium proxy.
All document content is proxied through the backend — the frontend
NEVER calls Cosium directly (CORS disabled on Cosium side).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
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
