"""API router for PEC preparation (assistance PEC)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.pec_preparation import (
    DocumentAttach,
    FieldCorrection,
    FieldValidation,
    PecPreparationCreate,
    PecPreparationDocumentResponse,
    PecPreparationResponse,
    PecPreparationSummary,
)
from app.services import pec_preparation_service

router = APIRouter(prefix="/api/v1", tags=["pec-preparation"])


@router.post(
    "/clients/{customer_id}/pec-preparation",
    response_model=PecPreparationResponse,
    status_code=201,
    summary="Preparer une fiche PEC",
    description="Lance la consolidation multi-sources et cree une fiche d'assistance PEC pour un client.",
)
def create_preparation(
    customer_id: int,
    payload: PecPreparationCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PecPreparationResponse:
    return pec_preparation_service.prepare_pec(
        db,
        tenant_id=tenant_ctx.tenant_id,
        customer_id=customer_id,
        devis_id=payload.devis_id,
        user_id=tenant_ctx.user_id,
    )


@router.get(
    "/clients/{customer_id}/pec-preparations",
    response_model=list[PecPreparationSummary],
    summary="Lister les preparations PEC d'un client",
    description="Retourne la liste des fiches d'assistance PEC pour un client.",
)
def list_preparations(
    customer_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[PecPreparationSummary]:
    offset = (page - 1) * page_size
    return pec_preparation_service.list_preparations_for_customer(
        db,
        tenant_id=tenant_ctx.tenant_id,
        customer_id=customer_id,
        limit=page_size,
        offset=offset,
    )


@router.get(
    "/clients/{customer_id}/pec-preparation/{preparation_id}",
    response_model=PecPreparationResponse,
    summary="Detail d'une preparation PEC",
    description="Retourne le detail complet d'une fiche d'assistance PEC.",
)
def get_preparation(
    customer_id: int,
    preparation_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PecPreparationResponse:
    return pec_preparation_service.get_preparation(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
    )


@router.post(
    "/pec-preparations/{preparation_id}/validate-field",
    response_model=PecPreparationResponse,
    summary="Valider un champ",
    description="Marque un champ comme valide par l'utilisateur.",
)
def validate_field(
    preparation_id: int,
    payload: FieldValidation,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PecPreparationResponse:
    return pec_preparation_service.validate_field(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
        field_name=payload.field_name,
        validated_by=tenant_ctx.user_id,
    )


@router.post(
    "/pec-preparations/{preparation_id}/correct-field",
    response_model=PecPreparationResponse,
    summary="Corriger un champ",
    description="Corrige la valeur d'un champ et recalcule les alertes.",
)
def correct_field(
    preparation_id: int,
    payload: FieldCorrection,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PecPreparationResponse:
    return pec_preparation_service.correct_field(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
        field_name=payload.field_name,
        new_value=payload.new_value,
        corrected_by=tenant_ctx.user_id,
    )


@router.post(
    "/pec-preparations/{preparation_id}/refresh",
    response_model=PecPreparationResponse,
    summary="Rafraichir la preparation",
    description="Relance la consolidation et la detection d'incoherences.",
)
def refresh_preparation(
    preparation_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PecPreparationResponse:
    return pec_preparation_service.refresh_preparation(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
    )


@router.post(
    "/pec-preparations/{preparation_id}/submit",
    summary="Soumettre la PEC",
    description="Cree une demande de PEC depuis la preparation validee.",
)
def submit_preparation(
    preparation_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    return pec_preparation_service.create_pec_from_preparation(
        db,
        tenant_id=tenant_ctx.tenant_id,
        preparation_id=preparation_id,
        user_id=tenant_ctx.user_id,
    )


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
    )
