"""Endpoints listing entités référentielles simples (mutuelles, doctors, brands, etc.)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.cosium_reference import (
    BrandResponse,
    DoctorResponse,
    MutuelleResponse,
    PaginatedDoctors,
    PaginatedMutuelles,
    SiteResponse,
    SupplierResponse,
    TagResponse,
)
from app.models.cosium_reference import (
    CosiumBank,
    CosiumBrand,
    CosiumCompany,
    CosiumDoctor,
    CosiumEquipmentType,
    CosiumFrameMaterial,
    CosiumMutuelle,
    CosiumSite,
    CosiumSupplier,
    CosiumTag,
    CosiumUser,
)
from app.services.cosium_reference_query_service import (
    ilike_filter,
    list_all,
    multi_ilike_filter,
    paginated_query,
)

router = APIRouter(prefix="/api/v1/cosium", tags=["cosium-reference"])


@router.get("/mutuelles", response_model=PaginatedMutuelles, summary="Lister les mutuelles")
def list_mutuelles(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, max_length=100, description="Recherche par nom"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedMutuelles:
    filters = [ilike_filter(CosiumMutuelle.name, search)] if search else []
    data = paginated_query(
        db,
        CosiumMutuelle,
        tenant_ctx.tenant_id,
        page,
        page_size,
        order_by=[CosiumMutuelle.name],
        filters=filters,
        response_schema=MutuelleResponse,
    )
    return PaginatedMutuelles(**data)


@router.get("/doctors", response_model=PaginatedDoctors, summary="Lister les medecins")
def list_doctors(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, max_length=100, description="Recherche par nom"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedDoctors:
    filters = (
        [multi_ilike_filter([CosiumDoctor.lastname, CosiumDoctor.firstname], search)]
        if search
        else []
    )
    data = paginated_query(
        db,
        CosiumDoctor,
        tenant_ctx.tenant_id,
        page,
        page_size,
        order_by=[CosiumDoctor.lastname, CosiumDoctor.firstname],
        filters=filters,
        response_schema=DoctorResponse,
    )
    return PaginatedDoctors(**data)


@router.get("/brands", response_model=list[BrandResponse], summary="Lister les marques")
def list_brands(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[BrandResponse]:
    return list_all(
        db,
        CosiumBrand,
        tenant_ctx.tenant_id,
        order_by=[CosiumBrand.name],
        response_schema=BrandResponse,
    )


@router.get(
    "/suppliers", response_model=list[SupplierResponse], summary="Lister les fournisseurs"
)
def list_suppliers(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SupplierResponse]:
    return list_all(
        db,
        CosiumSupplier,
        tenant_ctx.tenant_id,
        order_by=[CosiumSupplier.name],
        response_schema=SupplierResponse,
    )


@router.get("/tags", response_model=list[TagResponse], summary="Lister les tags")
def list_tags(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[TagResponse]:
    return list_all(
        db,
        CosiumTag,
        tenant_ctx.tenant_id,
        order_by=[CosiumTag.code],
        response_schema=TagResponse,
    )


@router.get("/sites", response_model=list[SiteResponse], summary="Lister les sites")
def list_sites(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SiteResponse]:
    return list_all(
        db,
        CosiumSite,
        tenant_ctx.tenant_id,
        order_by=[CosiumSite.name],
        response_schema=SiteResponse,
    )


@router.get("/banks", summary="Lister les banques")
def list_banks(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = list_all(db, CosiumBank, tenant_ctx.tenant_id, order_by=[CosiumBank.name])
    return [
        {
            "id": i.id,
            "name": i.name,
            "address": i.address,
            "city": i.city,
            "post_code": i.post_code,
        }
        for i in items
    ]


@router.get("/companies", summary="Lister les societes")
def list_companies(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = list_all(db, CosiumCompany, tenant_ctx.tenant_id, order_by=[CosiumCompany.name])
    return [
        {
            "id": i.id,
            "name": i.name,
            "siret": i.siret,
            "ape_code": i.ape_code,
            "address": i.address,
            "city": i.city,
            "post_code": i.post_code,
            "phone": i.phone,
            "email": i.email,
        }
        for i in items
    ]


@router.get("/users", summary="Lister les employes Cosium")
def list_cosium_users(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = list_all(
        db,
        CosiumUser,
        tenant_ctx.tenant_id,
        order_by=[CosiumUser.lastname, CosiumUser.firstname],
    )
    return [
        {
            "id": i.id,
            "cosium_id": i.cosium_id,
            "alias": i.alias,
            "firstname": i.firstname,
            "lastname": i.lastname,
            "title": i.title,
            "bot": i.bot,
        }
        for i in items
    ]


@router.get("/equipment-types", summary="Lister les types d'equipement")
def list_equipment_types(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = list_all(
        db, CosiumEquipmentType, tenant_ctx.tenant_id, order_by=[CosiumEquipmentType.label]
    )
    return [{"id": i.id, "label": i.label, "label_code": i.label_code} for i in items]


@router.get("/frame-materials", summary="Lister les materiaux de monture")
def list_frame_materials(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = list_all(
        db, CosiumFrameMaterial, tenant_ctx.tenant_id, order_by=[CosiumFrameMaterial.code]
    )
    return [{"id": i.id, "code": i.code, "description": i.description} for i in items]
