from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.http import content_disposition
from app.core.idempotency import IdempotencyContext, idempotency
from app.core.deps import require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.factures import (
    FactureCreate,
    FactureDetail,
    FactureResponse,
)
from app.services import facture_service, pdf_service

router = APIRouter(prefix="/api/v1", tags=["factures"])


@router.post(
    "/factures",
    response_model=FactureResponse,
    status_code=201,
    summary="Creer une facture",
    description="Genere une facture a partir d'un devis signe.",
)
def create_facture(
    payload: FactureCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("create", "facture")),
    idem: IdempotencyContext = Depends(idempotency("facture:create")),
) -> FactureResponse:
    if idem.cached:
        return FactureResponse(**idem.cached)
    result = facture_service.create_from_devis(
        db, tenant_id=tenant_ctx.tenant_id, devis_id=payload.devis_id, user_id=tenant_ctx.user_id
    )
    idem.store(result.model_dump(mode="json"))
    return result


@router.get(
    "/factures",
    response_model=list[FactureResponse],
    summary="Lister les factures",
    description="Retourne la liste paginee des factures du magasin.",
)
def list_factures(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[FactureResponse]:
    offset = (page - 1) * page_size
    return facture_service.list_factures(db, tenant_id=tenant_ctx.tenant_id, limit=page_size, offset=offset)


@router.get(
    "/factures/{facture_id}",
    response_model=FactureDetail,
    summary="Detail d'une facture",
    description="Retourne le detail complet d'une facture avec ses lignes.",
)
def get_facture(
    facture_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> FactureDetail:
    return facture_service.get_facture_detail(db, tenant_id=tenant_ctx.tenant_id, facture_id=facture_id)


@router.get(
    "/factures/{facture_id}/pdf",
    summary="Telecharger le PDF d'une facture",
    description="Genere et retourne le fichier PDF d'une facture.",
)
def download_facture_pdf(
    facture_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    pdf_bytes = pdf_service.generate_facture_pdf(db, facture_id=facture_id, tenant_id=tenant_ctx.tenant_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": content_disposition(f"facture_{facture_id}.pdf")},
    )
