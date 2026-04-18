"""Endpoints listing données paginées avec recherche (prescriptions, payments, products)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.cosium_reference import (
    CosiumProductResponse,
    PaginatedPayments,
    PaginatedPrescriptions,
    PaginatedProducts,
)
from app.domain.schemas.cosium_sync import (
    CosiumPaymentResponse,
    CosiumPrescriptionResponse,
)
from app.models.cosium_data import CosiumPayment, CosiumPrescription, CosiumProduct
from app.services.cosium_reference_query_service import (
    ilike_filter,
    multi_ilike_filter,
    paginated_query,
)

router = APIRouter(prefix="/api/v1/cosium", tags=["cosium-reference"])


@router.get(
    "/prescriptions", response_model=PaginatedPrescriptions, summary="Lister les ordonnances"
)
def list_prescriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(
        None, max_length=100, description="Recherche par nom prescripteur"
    ),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedPrescriptions:
    filters = [ilike_filter(CosiumPrescription.prescriber_name, search)] if search else []
    data = paginated_query(
        db,
        CosiumPrescription,
        tenant_ctx.tenant_id,
        page,
        page_size,
        order_by=[CosiumPrescription.file_date.desc().nullslast()],
        filters=filters,
        response_schema=CosiumPrescriptionResponse,
    )
    return PaginatedPrescriptions(**data)


@router.get(
    "/payments", response_model=PaginatedPayments, summary="Lister les paiements Cosium"
)
def list_cosium_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(
        None, max_length=100, description="Recherche par nom emetteur ou numero"
    ),
    date_from: str | None = Query(None, description="Date debut (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Date fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedPayments:
    filters = []
    if search:
        filters.append(
            multi_ilike_filter([CosiumPayment.issuer_name, CosiumPayment.payment_number], search)
        )
    if date_from:
        filters.append(CosiumPayment.due_date >= date_from)
    if date_to:
        filters.append(CosiumPayment.due_date <= date_to)
    data = paginated_query(
        db,
        CosiumPayment,
        tenant_ctx.tenant_id,
        page,
        page_size,
        order_by=[CosiumPayment.due_date.desc().nullslast()],
        filters=filters,
        response_schema=CosiumPaymentResponse,
    )
    return PaginatedPayments(**data)


@router.get("/products", response_model=PaginatedProducts, summary="Lister les produits")
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(
        None, max_length=100, description="Recherche par libelle, code ou EAN"
    ),
    family: str | None = Query(None, description="Filtrer par famille de produit"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedProducts:
    filters = []
    if search:
        filters.append(
            multi_ilike_filter(
                [CosiumProduct.label, CosiumProduct.code, CosiumProduct.ean_code], search
            )
        )
    if family:
        filters.append(ilike_filter(CosiumProduct.family_type, family))
    data = paginated_query(
        db,
        CosiumProduct,
        tenant_ctx.tenant_id,
        page,
        page_size,
        order_by=[CosiumProduct.label],
        filters=filters,
        response_schema=CosiumProductResponse,
    )
    return PaginatedProducts(**data)
