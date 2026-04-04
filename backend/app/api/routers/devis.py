from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.devis import (
    DevisCreate,
    DevisDetail,
    DevisResponse,
    DevisStatusUpdate,
    DevisUpdate,
)
from app.services import devis_service, pdf_service

router = APIRouter(prefix="/api/v1", tags=["devis"])


@router.post("/devis", response_model=DevisResponse, status_code=201)
def create_devis(
    payload: DevisCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DevisResponse:
    return devis_service.create_devis(db, tenant_id=tenant_ctx.tenant_id, payload=payload, user_id=tenant_ctx.user_id)


@router.get("/devis", response_model=list[DevisResponse])
def list_devis(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[DevisResponse]:
    return devis_service.list_devis(db, tenant_id=tenant_ctx.tenant_id, limit=limit, offset=offset)


@router.get("/devis/{devis_id}", response_model=DevisDetail)
def get_devis(
    devis_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DevisDetail:
    return devis_service.get_devis_detail(db, tenant_id=tenant_ctx.tenant_id, devis_id=devis_id)


@router.put("/devis/{devis_id}", response_model=DevisResponse)
def update_devis(
    devis_id: int,
    payload: DevisUpdate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DevisResponse:
    return devis_service.update_devis(
        db, tenant_id=tenant_ctx.tenant_id, devis_id=devis_id, payload=payload, user_id=tenant_ctx.user_id
    )


@router.patch("/devis/{devis_id}/status", response_model=DevisResponse)
def change_status(
    devis_id: int,
    payload: DevisStatusUpdate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DevisResponse:
    return devis_service.change_status(
        db, tenant_id=tenant_ctx.tenant_id, devis_id=devis_id, new_status=payload.status, user_id=tenant_ctx.user_id
    )


@router.get("/devis/{devis_id}/pdf")
def download_devis_pdf(
    devis_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    pdf_bytes = pdf_service.generate_devis_pdf(db, devis_id=devis_id, tenant_id=tenant_ctx.tenant_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="devis_{devis_id}.pdf"'},
    )
