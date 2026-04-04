from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.documents import DocumentResponse
from app.services import document_service

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get("/cases/{case_id}/documents", response_model=list[DocumentResponse])
def list_documents(
    case_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[DocumentResponse]:
    return document_service.list_documents(db, tenant_id=tenant_ctx.tenant_id, case_id=case_id)


@router.post("/cases/{case_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    case_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DocumentResponse:
    return document_service.upload_document(
        db, tenant_id=tenant_ctx.tenant_id, case_id=case_id, file=file, user_id=tenant_ctx.user_id
    )


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> RedirectResponse:
    url = document_service.get_download_url(db, tenant_id=tenant_ctx.tenant_id, document_id=document_id)
    return RedirectResponse(url=url)
