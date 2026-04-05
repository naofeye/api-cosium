"""Router for Cosium invoices — read-only listing of synced Cosium data."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.cosium_invoices import CosiumInvoiceListResponse
from app.services import cosium_invoice_service

router = APIRouter(prefix="/api/v1", tags=["cosium-invoices"])


@router.get(
    "/cosium-invoices",
    response_model=CosiumInvoiceListResponse,
    summary="Lister les factures Cosium",
    description="Retourne la liste paginee des factures synchronisees depuis Cosium.",
)
def list_cosium_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    type_filter: str | None = Query(None, description="Filtrer par type : INVOICE, QUOTE, CREDIT_NOTE"),
    settled: bool | None = Query(None, description="Filtrer par statut de reglement"),
    search: str | None = Query(None, description="Recherche par numero ou nom client"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CosiumInvoiceListResponse:
    return cosium_invoice_service.list_invoices(
        db,
        tenant_id=tenant_ctx.tenant_id,
        page=page,
        page_size=page_size,
        type_filter=type_filter,
        settled=settled,
        search=search,
    )
