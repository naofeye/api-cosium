"""API router for PEC preparation — documents, audit, precontrol, PDF export."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.http import content_disposition
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.pec_preparation import (
    DocumentAttach,
    PecPreparationDocumentResponse,
    PrecontrolResponse,
)
from app.services import pec_preparation_service
from app.services.export_pdf import export_pec_preparation_pdf

router = APIRouter(prefix="/api/v1", tags=["pec-preparation"])


@router.get(
    "/pec-preparations/{preparation_id}/documents",
    response_model=list[PecPreparationDocumentResponse],
    summary="Documents de la preparation",
    description="Liste les documents justificatifs lies a la preparation PEC.",
)
def list_documents(
    preparation_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[PecPreparationDocumentResponse]:
    return pec_preparation_service.list_documents(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
    )


@router.post(
    "/pec-preparations/{preparation_id}/documents",
    response_model=PecPreparationDocumentResponse,
    status_code=201,
    summary="Attacher un document",
    description="Lie un document a la preparation PEC.",
)
def attach_document(
    preparation_id: int,
    payload: DocumentAttach,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PecPreparationDocumentResponse:
    return pec_preparation_service.add_document(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
        document_id=payload.document_id,
        cosium_document_id=payload.cosium_document_id,
        document_role=payload.document_role,
        extraction_id=payload.extraction_id,
        user_id=tenant_ctx.user_id,
    )


@router.get(
    "/pec-preparations/{preparation_id}/audit",
    summary="Historique d'audit PEC",
    description="Retourne le journal d'audit structure de toutes les actions sur cette preparation.",
)
def get_audit_trail(
    preparation_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    offset = (page - 1) * page_size
    return pec_preparation_service.get_audit_trail(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
        limit=page_size,
        offset=offset,
    )


@router.get(
    "/pec-preparations/{preparation_id}/precontrol",
    response_model=PrecontrolResponse,
    summary="Pre-controle PEC",
    description="Execute un pre-controle complet avant soumission : documents, champs, coherence.",
)
def run_precontrol(
    preparation_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PrecontrolResponse:
    data = pec_preparation_service.run_precontrol_for_preparation(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
    )
    return PrecontrolResponse(**data)


@router.get(
    "/pec-preparations/{preparation_id}/export-pdf",
    summary="Exporter la fiche PEC en PDF",
    description="Genere un PDF professionnel de la fiche d'assistance PEC.",
)
def export_preparation_pdf(
    preparation_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    pdf_bytes = export_pec_preparation_pdf(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition(f"pec_preparation_{preparation_id}.pdf"),
        },
    )
