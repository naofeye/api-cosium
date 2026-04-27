"""API router for OCAM operators."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.ocam_operator import (
    OcamOperatorCreate,
    OcamOperatorResponse,
)
from app.services import ocam_operator_service

router = APIRouter(prefix="/api/v1", tags=["ocam-operators"])


@router.get(
    "/ocam-operators",
    response_model=list[OcamOperatorResponse],
    summary="Lister les operateurs OCAM",
    description="Retourne la liste des operateurs OCAM (mutuelles/complementaires) configures pour le tenant.",
)
def list_operators(
    active_only: bool = Query(True, description="Filtrer uniquement les actifs"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[OcamOperatorResponse]:
    return ocam_operator_service.list_operators(
        db,
        tenant_id=tenant_ctx.tenant_id,
        active_only=active_only,
    )


@router.post(
    "/ocam-operators",
    response_model=OcamOperatorResponse,
    status_code=201,
    summary="Creer un operateur OCAM",
    description="Cree un nouvel operateur OCAM avec ses regles specifiques.",
    dependencies=[Depends(require_permission("create", "ocam_operator"))],
)
def create_operator(
    payload: OcamOperatorCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> OcamOperatorResponse:
    return ocam_operator_service.create_operator(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
    )
