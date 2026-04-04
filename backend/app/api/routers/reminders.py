from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.reminders import (
    AutoGenerateResponse,
    OverdueItem,
    ReminderCreate,
    ReminderListResponse,
    ReminderPlanCreate,
    ReminderPlanResponse,
    ReminderResponse,
    ReminderStats,
    ReminderTemplateCreate,
    ReminderTemplateResponse,
)
from app.services import reminder_service

router = APIRouter(prefix="/api/v1/reminders", tags=["reminders"])


# --- Overdue ---


@router.get("/overdue", response_model=list[OverdueItem])
def get_overdue(
    min_days: int = Query(7, ge=0),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[OverdueItem]:
    return reminder_service.get_overdue(db, tenant_id=tenant_ctx.tenant_id, min_days=min_days)


# --- Stats ---


@router.get("/stats", response_model=ReminderStats)
def get_stats(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ReminderStats:
    return reminder_service.get_stats(db, tenant_id=tenant_ctx.tenant_id)


# --- Plans ---


@router.get("/plans", response_model=list[ReminderPlanResponse])
def list_plans(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[ReminderPlanResponse]:
    return reminder_service.list_plans(db, tenant_id=tenant_ctx.tenant_id)


@router.post("/plans", response_model=ReminderPlanResponse, status_code=201)
def create_plan(
    payload: ReminderPlanCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ReminderPlanResponse:
    return reminder_service.create_plan(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.post("/plans/{plan_id}/execute", response_model=list[ReminderResponse])
def execute_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[ReminderResponse]:
    return reminder_service.execute_plan(
        db,
        tenant_id=tenant_ctx.tenant_id,
        plan_id=plan_id,
        user_id=tenant_ctx.user_id,
    )


@router.patch("/plans/{plan_id}/toggle", response_model=ReminderPlanResponse)
def toggle_plan(
    plan_id: int,
    is_active: bool = Query(...),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ReminderPlanResponse:
    return reminder_service.toggle_plan(
        db,
        tenant_id=tenant_ctx.tenant_id,
        plan_id=plan_id,
        is_active=is_active,
    )


# --- Reminders ---


@router.get("", response_model=ReminderListResponse)
def list_reminders(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ReminderListResponse:
    items, total = reminder_service.list_reminders(
        db,
        tenant_id=tenant_ctx.tenant_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return ReminderListResponse(items=items, total=total)


@router.post("", response_model=ReminderResponse, status_code=201)
def create_reminder(
    payload: ReminderCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ReminderResponse:
    return reminder_service.create_reminder(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.post("/{reminder_id}/send", response_model=ReminderResponse)
def send_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ReminderResponse:
    return reminder_service.send_reminder(
        db,
        tenant_id=tenant_ctx.tenant_id,
        reminder_id=reminder_id,
        user_id=tenant_ctx.user_id,
    )


@router.post("/auto-generate", response_model=AutoGenerateResponse)
def auto_generate(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> AutoGenerateResponse:
    from app.tasks.reminder_tasks import auto_generate_reminders

    results = auto_generate_reminders()
    return AutoGenerateResponse(status="ok", plans=results)


# --- Templates ---


@router.get("/templates", response_model=list[ReminderTemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[ReminderTemplateResponse]:
    return reminder_service.list_templates(db, tenant_id=tenant_ctx.tenant_id)


@router.post("/templates", response_model=ReminderTemplateResponse, status_code=201)
def create_template(
    payload: ReminderTemplateCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ReminderTemplateResponse:
    return reminder_service.create_template(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )
