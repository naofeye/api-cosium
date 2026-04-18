"""Endpoints lecture événements calendrier + catégories Cosium."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.cosium_reference import (
    CalendarEventResponse,
    PaginatedCalendarEvents,
)
from app.models.cosium_reference import CosiumCalendarCategory, CosiumCalendarEvent
from app.services.cosium_reference_query_service import paginated_query

router = APIRouter(prefix="/api/v1/cosium", tags=["cosium-reference"])


@router.get(
    "/calendar-events",
    response_model=PaginatedCalendarEvents,
    summary="Lister les evenements calendrier",
)
def list_calendar_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str | None = Query(None, description="Filtrer par statut"),
    from_start_date: str | None = Query(
        None, description="ISO 8601 date de debut min (yyyy-mm-dd ou yyyy-mm-ddTHH:MM:SS)"
    ),
    to_start_date: str | None = Query(None, description="ISO 8601 date de debut max"),
    date_from: str | None = Query(None, description="Alias front-end de from_start_date"),
    date_to: str | None = Query(None, description="Alias front-end de to_start_date"),
    customer_number: str | None = Query(None, description="Filtrer par numero client"),
    site_name: str | None = Query(None, description="Filtrer par site"),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PaginatedCalendarEvents:
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
            filters.append(
                CosiumCalendarEvent.start_date
                >= datetime.fromisoformat(from_start_date.replace("Z", "+00:00"))
            )
        except ValueError as exc:
            raise ValidationError("from_start_date doit etre au format ISO 8601") from exc
    if to_start_date:
        try:
            filters.append(
                CosiumCalendarEvent.start_date
                <= datetime.fromisoformat(to_start_date.replace("Z", "+00:00"))
            )
        except ValueError as exc:
            raise ValidationError("to_start_date doit etre au format ISO 8601") from exc
    data = paginated_query(
        db,
        CosiumCalendarEvent,
        tenant_ctx.tenant_id,
        page,
        page_size,
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
