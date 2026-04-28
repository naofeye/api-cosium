from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_permission
from app.core.exceptions import ValidationError
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.documents import DocumentResponse
from app.services import document_service

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get(
    "/cases/{case_id}/documents",
    response_model=list[DocumentResponse],
    summary="Lister les documents d'un dossier",
    description="Retourne tous les documents rattaches a un dossier.",
)
def list_documents(
    case_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[DocumentResponse]:
    return document_service.list_documents(db, tenant_id=tenant_ctx.tenant_id, case_id=case_id)


_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB


@router.post(
    "/cases/{case_id}/documents",
    response_model=DocumentResponse,
    status_code=201,
    summary="Telecharger un document",
    description="Televerse un fichier et le rattache au dossier.",
)
async def upload_document(
    case_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("create", "document")),
) -> DocumentResponse:
    max_size = settings.max_upload_size_mb * 1024 * 1024

    # Pre-check Content-Length pour rejeter sans rien lire les requetes evidemment trop grosses.
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > max_size + _UPLOAD_CHUNK_SIZE:
        raise ValidationError("file", f"Fichier trop volumineux (max {settings.max_upload_size_mb} MB)")

    # Lecture par chunks avec arret anticipe : evite de charger un multipart enorme en RAM
    # avant de constater qu'il depasse la limite (vecteur de DoS memoire avant ce fix).
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise ValidationError("file", f"Fichier trop volumineux (max {settings.max_upload_size_mb} MB)")
        chunks.append(chunk)
    file_data = b"".join(chunks)

    return document_service.upload_document(
        db,
        tenant_id=tenant_ctx.tenant_id,
        case_id=case_id,
        file_data=file_data,
        filename=file.filename or "unknown",
        content_type=file.content_type,
        user_id=tenant_ctx.user_id,
    )


@router.get(
    "/documents/{document_id}/download",
    summary="Telecharger ou previsualiser un document",
    description="Retourne une URL presignee. Ajouter ?inline=true pour affichage en ligne.",
)
def download_document(
    document_id: int,
    inline: bool = Query(False, description="Afficher en ligne au lieu de telecharger"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> RedirectResponse:
    url = document_service.get_download_url(
        db,
        tenant_id=tenant_ctx.tenant_id,
        document_id=document_id,
        inline=inline,
    )
    return RedirectResponse(url=url)
