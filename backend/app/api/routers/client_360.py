from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.client_360 import Client360Response
from app.domain.schemas.interactions import InteractionCreate, InteractionListResponse, InteractionResponse
from app.services import client_360_service, interaction_service, pdf_service

router = APIRouter(prefix="/api/v1", tags=["client-360"])


@router.get("/clients/{client_id}/360", response_model=Client360Response)
def get_client_360(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Client360Response:
    return client_360_service.get_client_360(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
    )


@router.get("/clients/{client_id}/360/pdf")
def download_client_360_pdf(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    pdf_bytes = pdf_service.generate_client_360_pdf(db, client_id, tenant_ctx.tenant_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=client_{client_id}_360.pdf"},
    )


@router.get("/clients/{client_id}/interactions", response_model=InteractionListResponse)
def list_interactions(
    client_id: int,
    type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> InteractionListResponse:
    items, total = interaction_service.get_client_timeline(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
        type=type,
        limit=limit,
    )
    return InteractionListResponse(items=items, total=total)


@router.post("/interactions", response_model=InteractionResponse, status_code=201)
def create_interaction(
    payload: InteractionCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> InteractionResponse:
    return interaction_service.add_interaction(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.delete("/interactions/{interaction_id}", status_code=204)
def delete_interaction(
    interaction_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> None:
    interaction_service.delete_interaction(
        db,
        tenant_id=tenant_ctx.tenant_id,
        interaction_id=interaction_id,
        user_id=tenant_ctx.user_id,
    )
