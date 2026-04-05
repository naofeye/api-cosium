"""Routes pour les donnees de reference Cosium (calendrier, mutuelles, medecins, etc.).

Endpoints de lecture depuis la base locale + declenchement de synchronisation.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.cosium_reference import (
    BrandResponse,
    CalendarEventResponse,
    DoctorResponse,
    MutuelleResponse,
    PaginatedCalendarEvents,
    PaginatedDoctors,
    PaginatedMutuelles,
    ReferenceSyncAllResult,
    SiteResponse,
    SupplierResponse,
    TagResponse,
)
from app.models.cosium_reference import (
    CosiumBank,
    CosiumBrand,
    CosiumCalendarCategory,
    CosiumCalendarEvent,
    CosiumCompany,
    CosiumCustomerTag,
    CosiumDoctor,
    CosiumEquipmentType,
    CosiumFrameMaterial,
    CosiumLensFocusCategory,
    CosiumLensFocusType,
    CosiumLensMaterial,
    CosiumMutuelle,
    CosiumSite,
    CosiumSupplier,
    CosiumTag,
    CosiumUser,
)
from app.services import cosium_reference_sync

router = APIRouter(prefix="/api/v1/cosium", tags=["cosium-reference"])


@router.post(
    "/sync-reference",
    response_model=ReferenceSyncAllResult,
    summary="Synchroniser toutes les donnees de reference",
    description="Lance la synchronisation des donnees de reference depuis Cosium (calendrier, mutuelles, medecins, marques, fournisseurs, tags, sites).",
)
def sync_reference(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> ReferenceSyncAllResult:
    result = cosium_reference_sync.sync_all_reference(
        db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id
    )
    return ReferenceSyncAllResult(**result)


# --- Calendar Events ---

@router.get(
    "/calendar-events",
    response_model=PaginatedCalendarEvents,
    summary="Lister les evenements calendrier",
    description="Liste paginee des evenements calendrier synchronises depuis Cosium.",
)
def list_calendar_events(
    page: int = Query(0, ge=0, description="Numero de page (commence a 0)"),
    page_size: int = Query(25, ge=1, le=100, description="Nombre d'elements par page"),
    status: str | None = Query(None, description="Filtrer par statut (ex: CONFIRMED)"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedCalendarEvents:
    query = select(CosiumCalendarEvent).where(CosiumCalendarEvent.tenant_id == tenant_ctx.tenant_id)
    count_query = select(func.count(CosiumCalendarEvent.id)).where(
        CosiumCalendarEvent.tenant_id == tenant_ctx.tenant_id
    )

    if status:
        query = query.where(CosiumCalendarEvent.status == status)
        count_query = count_query.where(CosiumCalendarEvent.status == status)

    query = query.order_by(CosiumCalendarEvent.start_date.desc())
    total = db.scalar(count_query) or 0
    items = db.scalars(query.offset(page * page_size).limit(page_size)).all()

    return PaginatedCalendarEvents(
        items=[CalendarEventResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- Mutuelles ---

@router.get(
    "/mutuelles",
    response_model=PaginatedMutuelles,
    summary="Lister les mutuelles",
    description="Liste paginee des mutuelles synchronisees depuis Cosium.",
)
def list_mutuelles(
    page: int = Query(0, ge=0),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche par nom"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedMutuelles:
    query = select(CosiumMutuelle).where(CosiumMutuelle.tenant_id == tenant_ctx.tenant_id)
    count_query = select(func.count(CosiumMutuelle.id)).where(
        CosiumMutuelle.tenant_id == tenant_ctx.tenant_id
    )

    if search:
        pattern = f"%{search}%"
        query = query.where(CosiumMutuelle.name.ilike(pattern))
        count_query = count_query.where(CosiumMutuelle.name.ilike(pattern))

    query = query.order_by(CosiumMutuelle.name)
    total = db.scalar(count_query) or 0
    items = db.scalars(query.offset(page * page_size).limit(page_size)).all()

    return PaginatedMutuelles(
        items=[MutuelleResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- Doctors ---

@router.get(
    "/doctors",
    response_model=PaginatedDoctors,
    summary="Lister les medecins",
    description="Liste paginee des medecins/prescripteurs synchronises depuis Cosium.",
)
def list_doctors(
    page: int = Query(0, ge=0),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche par nom"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedDoctors:
    query = select(CosiumDoctor).where(CosiumDoctor.tenant_id == tenant_ctx.tenant_id)
    count_query = select(func.count(CosiumDoctor.id)).where(
        CosiumDoctor.tenant_id == tenant_ctx.tenant_id
    )

    if search:
        pattern = f"%{search}%"
        query = query.where(
            (CosiumDoctor.lastname.ilike(pattern)) | (CosiumDoctor.firstname.ilike(pattern))
        )
        count_query = count_query.where(
            (CosiumDoctor.lastname.ilike(pattern)) | (CosiumDoctor.firstname.ilike(pattern))
        )

    query = query.order_by(CosiumDoctor.lastname, CosiumDoctor.firstname)
    total = db.scalar(count_query) or 0
    items = db.scalars(query.offset(page * page_size).limit(page_size)).all()

    return PaginatedDoctors(
        items=[DoctorResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# --- Brands ---

@router.get(
    "/brands",
    response_model=list[BrandResponse],
    summary="Lister les marques",
    description="Liste de toutes les marques synchronisees depuis Cosium.",
)
def list_brands(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[BrandResponse]:
    items = db.scalars(
        select(CosiumBrand)
        .where(CosiumBrand.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumBrand.name)
    ).all()
    return [BrandResponse.model_validate(i) for i in items]


# --- Suppliers ---

@router.get(
    "/suppliers",
    response_model=list[SupplierResponse],
    summary="Lister les fournisseurs",
    description="Liste de tous les fournisseurs synchronises depuis Cosium.",
)
def list_suppliers(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SupplierResponse]:
    items = db.scalars(
        select(CosiumSupplier)
        .where(CosiumSupplier.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumSupplier.name)
    ).all()
    return [SupplierResponse.model_validate(i) for i in items]


# --- Tags ---

@router.get(
    "/tags",
    response_model=list[TagResponse],
    summary="Lister les tags",
    description="Liste de tous les tags synchronises depuis Cosium.",
)
def list_tags(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[TagResponse]:
    items = db.scalars(
        select(CosiumTag)
        .where(CosiumTag.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumTag.code)
    ).all()
    return [TagResponse.model_validate(i) for i in items]


# --- Sites ---

@router.get(
    "/sites",
    response_model=list[SiteResponse],
    summary="Lister les sites",
    description="Liste de tous les sites/magasins synchronises depuis Cosium.",
)
def list_sites(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SiteResponse]:
    items = db.scalars(
        select(CosiumSite)
        .where(CosiumSite.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumSite.name)
    ).all()
    return [SiteResponse.model_validate(i) for i in items]


# --- Banks ---

@router.get(
    "/banks",
    summary="Lister les banques",
    description="Liste de toutes les banques synchronisees depuis Cosium.",
)
def list_banks(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = db.scalars(
        select(CosiumBank)
        .where(CosiumBank.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumBank.name)
    ).all()
    return [
        {"id": i.id, "name": i.name, "address": i.address, "city": i.city, "post_code": i.post_code}
        for i in items
    ]


# --- Companies ---

@router.get(
    "/companies",
    summary="Lister les societes",
    description="Liste des societes synchronisees depuis Cosium.",
)
def list_companies(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = db.scalars(
        select(CosiumCompany)
        .where(CosiumCompany.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumCompany.name)
    ).all()
    return [
        {
            "id": i.id, "name": i.name, "siret": i.siret, "ape_code": i.ape_code,
            "address": i.address, "city": i.city, "post_code": i.post_code,
            "phone": i.phone, "email": i.email,
        }
        for i in items
    ]


# --- Users/Employees ---

@router.get(
    "/users",
    summary="Lister les employes Cosium",
    description="Liste des employes/utilisateurs synchronises depuis Cosium.",
)
def list_cosium_users(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = db.scalars(
        select(CosiumUser)
        .where(CosiumUser.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumUser.lastname, CosiumUser.firstname)
    ).all()
    return [
        {
            "id": i.id, "cosium_id": i.cosium_id, "alias": i.alias,
            "firstname": i.firstname, "lastname": i.lastname,
            "title": i.title, "bot": i.bot,
        }
        for i in items
    ]


# --- Equipment types ---

@router.get(
    "/equipment-types",
    summary="Lister les types d'equipement",
    description="Liste des types de famille d'equipement synchronises depuis Cosium.",
)
def list_equipment_types(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = db.scalars(
        select(CosiumEquipmentType)
        .where(CosiumEquipmentType.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumEquipmentType.label)
    ).all()
    return [{"id": i.id, "label": i.label, "label_code": i.label_code} for i in items]


# --- Frame materials ---

@router.get(
    "/frame-materials",
    summary="Lister les materiaux de monture",
    description="Liste des materiaux de monture synchronises depuis Cosium.",
)
def list_frame_materials(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = db.scalars(
        select(CosiumFrameMaterial)
        .where(CosiumFrameMaterial.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumFrameMaterial.code)
    ).all()
    return [{"id": i.id, "code": i.code, "description": i.description} for i in items]


# --- Sync customer tags (separate endpoint — slow operation) ---

@router.post(
    "/sync-customer-tags",
    summary="Synchroniser les tags par client",
    description="Itere tous les clients et recupere leurs tags depuis Cosium. Operation lente (~0.3s/client).",
)
def sync_customer_tags_endpoint(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> dict:
    return cosium_reference_sync.sync_customer_tags(
        db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id
    )
