"""Routes de lecture des donnees de reference Cosium."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.cosium_reference import (
    BrandResponse,
    CalendarEventResponse,
    CosiumProductResponse,
    DoctorResponse,
    MutuelleResponse,
    PaginatedCalendarEvents,
    PaginatedDoctors,
    PaginatedMutuelles,
    PaginatedPayments,
    PaginatedPrescriptions,
    PaginatedProducts,
    ReferenceSyncAllResult,
    SiteResponse,
    SupplierResponse,
    TagResponse,
)
from app.domain.schemas.cosium_sync import (
    CosiumPaymentResponse,
    CosiumPrescriptionResponse,
)
from app.models.cosium_data import CosiumPayment, CosiumPrescription, CosiumProduct
from app.models.cosium_reference import (
    CosiumBank,
    CosiumBrand,
    CosiumCalendarCategory,
    CosiumCalendarEvent,
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
from app.services import cosium_reference_sync
from app.services.cosium_reference_query_service import (
    ilike_filter,
    list_all,
    multi_ilike_filter,
    paginated_query,
)

router = APIRouter(prefix="/api/v1/cosium", tags=["cosium-reference"])


@router.post(
    "/sync-reference",
    response_model=ReferenceSyncAllResult,
    summary="Synchroniser toutes les donnees de reference",
)
def sync_reference(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> ReferenceSyncAllResult:
    result = cosium_reference_sync.sync_all_reference(
        db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id
    )
    return ReferenceSyncAllResult(**result)


@router.get("/calendar-events", response_model=PaginatedCalendarEvents, summary="Lister les evenements calendrier")
def list_calendar_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str | None = Query(None, description="Filtrer par statut"),
    from_start_date: str | None = Query(None, description="ISO 8601 date de debut min (yyyy-mm-dd ou yyyy-mm-ddTHH:MM:SS)"),
    to_start_date: str | None = Query(None, description="ISO 8601 date de debut max"),
    date_from: str | None = Query(None, description="Alias front-end de from_start_date"),
    date_to: str | None = Query(None, description="Alias front-end de to_start_date"),
    customer_number: str | None = Query(None, description="Filtrer par numero client"),
    site_name: str | None = Query(None, description="Filtrer par site"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedCalendarEvents:
    from datetime import datetime
    # Aliases : date_from/date_to ont priorite si fournis
    from_start_date = date_from or from_start_date
    to_start_date = date_to or to_start_date
    filters = []
    if status:
        filters.append(CosiumCalendarEvent.status == status)
    if customer_number:
        filters.append(CosiumCalendarEvent.customer_number == customer_number)
    if site_name:
        filters.append(CosiumCalendarEvent.site_name == site_name)
    if from_start_date:
        try:
            filters.append(CosiumCalendarEvent.start_date >= datetime.fromisoformat(from_start_date.replace("Z", "+00:00")))
        except ValueError:
            from app.core.exceptions import ValidationError as VE
            raise VE("from_start_date doit etre au format ISO 8601")
    if to_start_date:
        try:
            filters.append(CosiumCalendarEvent.start_date <= datetime.fromisoformat(to_start_date.replace("Z", "+00:00")))
        except ValueError:
            from app.core.exceptions import ValidationError as VE
            raise VE("to_start_date doit etre au format ISO 8601")
    data = paginated_query(
        db, CosiumCalendarEvent, tenant_ctx.tenant_id, page, page_size,
        order_by=[CosiumCalendarEvent.start_date.desc()],
        filters=filters,
        response_schema=CalendarEventResponse,
    )
    return PaginatedCalendarEvents(**data)


@router.get(
    "/calendar-events/upcoming",
    response_model=list[CalendarEventResponse],
    summary="Prochains rendez-vous",
    description="Retourne les N prochains evenements (a partir de maintenant), pour widget dashboard.",
)
def list_upcoming_calendar_events(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[CalendarEventResponse]:
    from datetime import UTC, datetime
    from sqlalchemy import select
    now = datetime.now(UTC).replace(tzinfo=None)
    rows = db.scalars(
        select(CosiumCalendarEvent)
        .where(
            CosiumCalendarEvent.tenant_id == tenant_ctx.tenant_id,
            CosiumCalendarEvent.start_date >= now,
            CosiumCalendarEvent.canceled.is_(False),
        )
        .order_by(CosiumCalendarEvent.start_date.asc())
        .limit(limit)
    ).all()
    return [CalendarEventResponse.model_validate(r, from_attributes=True) for r in rows]


@router.get(
    "/calendar-events/{event_id}",
    response_model=CalendarEventResponse,
    summary="Detail d'un evenement calendrier",
)
def get_calendar_event(
    event_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CalendarEventResponse:
    from sqlalchemy import select
    from app.core.exceptions import NotFoundError
    row = db.scalars(
        select(CosiumCalendarEvent).where(
            CosiumCalendarEvent.id == event_id,
            CosiumCalendarEvent.tenant_id == tenant_ctx.tenant_id,
        )
    ).first()
    if not row:
        raise NotFoundError("Evenement", event_id)
    return CalendarEventResponse.model_validate(row, from_attributes=True)


@router.get(
    "/calendar-event-categories",
    summary="Lister les categories d'evenements",
    description="Retourne la liste des categories d'evenements (types de RDV).",
)
def list_calendar_categories(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    from sqlalchemy import select
    rows = db.scalars(
        select(CosiumCalendarCategory)
        .where(CosiumCalendarCategory.tenant_id == tenant_ctx.tenant_id)
        .order_by(CosiumCalendarCategory.name)
    ).all()
    return [
        {
            "id": r.id,
            "cosium_id": r.cosium_id,
            "name": r.name,
            "color": r.color,
            "family_name": r.family_name,
        }
        for r in rows
    ]


@router.get("/mutuelles", response_model=PaginatedMutuelles, summary="Lister les mutuelles")
def list_mutuelles(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche par nom"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedMutuelles:
    filters = [ilike_filter(CosiumMutuelle.name, search)] if search else []
    data = paginated_query(
        db, CosiumMutuelle, tenant_ctx.tenant_id, page, page_size,
        order_by=[CosiumMutuelle.name],
        filters=filters,
        response_schema=MutuelleResponse,
    )
    return PaginatedMutuelles(**data)


@router.get("/doctors", response_model=PaginatedDoctors, summary="Lister les medecins")
def list_doctors(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche par nom"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedDoctors:
    filters = [multi_ilike_filter([CosiumDoctor.lastname, CosiumDoctor.firstname], search)] if search else []
    data = paginated_query(
        db, CosiumDoctor, tenant_ctx.tenant_id, page, page_size,
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
    return list_all(db, CosiumBrand, tenant_ctx.tenant_id, order_by=[CosiumBrand.name], response_schema=BrandResponse)


@router.get("/suppliers", response_model=list[SupplierResponse], summary="Lister les fournisseurs")
def list_suppliers(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SupplierResponse]:
    return list_all(db, CosiumSupplier, tenant_ctx.tenant_id, order_by=[CosiumSupplier.name], response_schema=SupplierResponse)


@router.get("/tags", response_model=list[TagResponse], summary="Lister les tags")
def list_tags(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[TagResponse]:
    return list_all(db, CosiumTag, tenant_ctx.tenant_id, order_by=[CosiumTag.code], response_schema=TagResponse)


@router.get("/sites", response_model=list[SiteResponse], summary="Lister les sites")
def list_sites(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SiteResponse]:
    return list_all(db, CosiumSite, tenant_ctx.tenant_id, order_by=[CosiumSite.name], response_schema=SiteResponse)


@router.get("/banks", summary="Lister les banques")
def list_banks(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = list_all(db, CosiumBank, tenant_ctx.tenant_id, order_by=[CosiumBank.name])
    return [
        {"id": i.id, "name": i.name, "address": i.address, "city": i.city, "post_code": i.post_code}
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
            "id": i.id, "name": i.name, "siret": i.siret, "ape_code": i.ape_code,
            "address": i.address, "city": i.city, "post_code": i.post_code,
            "phone": i.phone, "email": i.email,
        }
        for i in items
    ]


@router.get("/users", summary="Lister les employes Cosium")
def list_cosium_users(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = list_all(db, CosiumUser, tenant_ctx.tenant_id, order_by=[CosiumUser.lastname, CosiumUser.firstname])
    return [
        {
            "id": i.id, "cosium_id": i.cosium_id, "alias": i.alias,
            "firstname": i.firstname, "lastname": i.lastname,
            "title": i.title, "bot": i.bot,
        }
        for i in items
    ]


@router.get("/equipment-types", summary="Lister les types d'equipement")
def list_equipment_types(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = list_all(db, CosiumEquipmentType, tenant_ctx.tenant_id, order_by=[CosiumEquipmentType.label])
    return [{"id": i.id, "label": i.label, "label_code": i.label_code} for i in items]


@router.get("/frame-materials", summary="Lister les materiaux de monture")
def list_frame_materials(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[dict]:
    items = list_all(db, CosiumFrameMaterial, tenant_ctx.tenant_id, order_by=[CosiumFrameMaterial.code])
    return [{"id": i.id, "code": i.code, "description": i.description} for i in items]


@router.get("/prescriptions", response_model=PaginatedPrescriptions, summary="Lister les ordonnances")
def list_prescriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche par nom prescripteur"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedPrescriptions:
    filters = [ilike_filter(CosiumPrescription.prescriber_name, search)] if search else []
    data = paginated_query(
        db, CosiumPrescription, tenant_ctx.tenant_id, page, page_size,
        order_by=[CosiumPrescription.file_date.desc().nullslast()],
        filters=filters,
        response_schema=CosiumPrescriptionResponse,
    )
    return PaginatedPrescriptions(**data)


@router.get("/payments", response_model=PaginatedPayments, summary="Lister les paiements Cosium")
def list_cosium_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche par nom emetteur ou numero"),
    date_from: str | None = Query(None, description="Date debut (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Date fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedPayments:
    filters = []
    if search:
        filters.append(multi_ilike_filter([CosiumPayment.issuer_name, CosiumPayment.payment_number], search))
    if date_from:
        filters.append(CosiumPayment.due_date >= date_from)
    if date_to:
        filters.append(CosiumPayment.due_date <= date_to)
    data = paginated_query(
        db, CosiumPayment, tenant_ctx.tenant_id, page, page_size,
        order_by=[CosiumPayment.due_date.desc().nullslast()],
        filters=filters,
        response_schema=CosiumPaymentResponse,
    )
    return PaginatedPayments(**data)


@router.get("/products", response_model=PaginatedProducts, summary="Lister les produits")
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, description="Recherche par libelle, code ou EAN"),
    family: str | None = Query(None, description="Filtrer par famille de produit"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedProducts:
    filters = []
    if search:
        filters.append(multi_ilike_filter([CosiumProduct.label, CosiumProduct.code, CosiumProduct.ean_code], search))
    if family:
        filters.append(ilike_filter(CosiumProduct.family_type, family))
    data = paginated_query(
        db, CosiumProduct, tenant_ctx.tenant_id, page, page_size,
        order_by=[CosiumProduct.label],
        filters=filters,
        response_schema=CosiumProductResponse,
    )
    return PaginatedProducts(**data)


@router.post("/sync-customer-tags", summary="Synchroniser les tags par client")
def sync_customer_tags_endpoint(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> dict:
    return cosium_reference_sync.sync_customer_tags(
        db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id
    )
