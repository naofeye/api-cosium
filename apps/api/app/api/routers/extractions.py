from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.ocr import DocumentExtractionResponse, ExtractionRequest
from app.services import extraction_service

router = APIRouter(prefix="/api/v1", tags=["extractions"])


@router.post(
    "/documents/{document_id}/extract",
    response_model=DocumentExtractionResponse,
    status_code=200,
    summary="Extraire le texte d'un document",
    description="Lance l'OCR et la classification sur un document stocke dans MinIO.",
)
def extract_document(
    document_id: int,
    payload: ExtractionRequest | None = None,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DocumentExtractionResponse:
    force = payload.force if payload else False
    use_ai = payload.use_ai if payload else False
    return extraction_service.extract_document(
        db,
        tenant_id=tenant_ctx.tenant_id,
        document_id=document_id,
        force=force,
        use_ai=use_ai,
    )
