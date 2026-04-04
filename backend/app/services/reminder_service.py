import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.reminders import (
    OverdueItem,
    ReminderCreate,
    ReminderPlanCreate,
    ReminderPlanResponse,
    ReminderResponse,
    ReminderStats,
    ReminderTemplateCreate,
    ReminderTemplateResponse,
)
from app.repositories import reminder_repo
from app.services import audit_service, event_service
from app.services.collection_prioritizer import prioritize_overdue

logger = get_logger("reminder_service")


# --- Plans ---


def list_plans(db: Session, tenant_id: int) -> list[ReminderPlanResponse]:
    plans = reminder_repo.list_plans(db, tenant_id)
    return [ReminderPlanResponse.model_validate(p) for p in plans]


def create_plan(db: Session, tenant_id: int, payload: ReminderPlanCreate, user_id: int) -> ReminderPlanResponse:
    plan = reminder_repo.create_plan(
        db,
        tenant_id,
        payload.name,
        payload.payer_type,
        json.dumps(payload.rules_json),
        json.dumps(payload.channel_sequence),
        payload.interval_days,
        payload.is_active,
    )
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "reminder_plan", plan.id)
    logger.info("plan_created", tenant_id=tenant_id, plan_id=plan.id, name=payload.name)
    return ReminderPlanResponse.model_validate(plan)


def toggle_plan(db: Session, tenant_id: int, plan_id: int, is_active: bool) -> ReminderPlanResponse:
    plan = reminder_repo.get_plan(db, plan_id=plan_id, tenant_id=tenant_id)
    if not plan:
        raise NotFoundError("reminder_plan", plan_id)
    reminder_repo.toggle_plan(db, plan, is_active)
    return ReminderPlanResponse.model_validate(plan)


# --- Overdue + Prioritization ---


def get_overdue(db: Session, tenant_id: int, min_days: int = 7) -> list[OverdueItem]:
    return prioritize_overdue(db, tenant_id, min_days)


# --- Execute plan ---


def execute_plan(db: Session, tenant_id: int, plan_id: int, user_id: int) -> list[ReminderResponse]:
    plan = reminder_repo.get_plan(db, plan_id=plan_id, tenant_id=tenant_id)
    if not plan:
        raise NotFoundError("reminder_plan", plan_id)

    rules = json.loads(plan.rules_json)
    channels = json.loads(plan.channel_sequence)
    if not channels:
        channels = ["email"]
    min_days = rules.get("min_days_overdue", 7)
    max_reminders = rules.get("max_reminders", 3)
    min_amount = rules.get("min_amount", 0)

    overdue = reminder_repo.get_all_overdue(db, tenant_id, min_days)
    created = []

    for item in overdue:
        if item["payer_type"] != plan.payer_type:
            continue
        if item["amount"] < min_amount:
            continue

        existing_count = reminder_repo.count_reminders_for_target(
            db,
            tenant_id,
            "client" if item["payer_type"] == "client" else "payer_organization",
            item["entity_id"],
            item.get("facture_id"),
        )
        if existing_count >= max_reminders:
            continue

        channel_idx = min(existing_count, len(channels) - 1)
        channel = channels[channel_idx]

        template = reminder_repo.get_default_template(db, tenant_id, channel, plan.payer_type)
        content = template.body if template else f"Relance pour {item['customer_name']}"
        if template:
            content = content.replace("{{client_name}}", item["customer_name"])
            content = content.replace("{{montant}}", f"{item['amount']:.2f}")
            content = content.replace("{{jours_retard}}", str(item["days_overdue"]))

        target_type = "client" if plan.payer_type == "client" else "payer_organization"
        reminder = reminder_repo.create_reminder(
            db,
            tenant_id,
            plan.id,
            target_type,
            item["entity_id"],
            item.get("facture_id"),
            item.get("pec_request_id"),
            channel,
            content,
            template.name if template else None,
            datetime.now(UTC).replace(tzinfo=None),
            user_id,
        )
        created.append(ReminderResponse.model_validate(reminder))

    if user_id and created:
        event_service.emit_event(db, tenant_id, "RelanceEnvoyee", "reminder_plan", plan_id, user_id)

    logger.info("plan_executed", tenant_id=tenant_id, plan_id=plan_id, reminders_created=len(created))
    return created


# --- Manual reminder ---


def create_reminder(db: Session, tenant_id: int, payload: ReminderCreate, user_id: int) -> ReminderResponse:
    reminder = reminder_repo.create_reminder(
        db,
        tenant_id,
        None,
        payload.target_type,
        payload.target_id,
        payload.facture_id,
        payload.pec_request_id,
        payload.channel,
        payload.content,
        None,
        datetime.now(UTC).replace(tzinfo=None),
        user_id,
    )
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "reminder", reminder.id)
    logger.info("reminder_created", tenant_id=tenant_id, reminder_id=reminder.id)
    return ReminderResponse.model_validate(reminder)


def _resolve_recipient_email(db: Session, reminder: "Reminder") -> str:  # noqa: F821
    """Resolve the actual email address from the reminder target."""
    from app.models import Case, Customer, PayerOrganization, Payment

    if reminder.target_type == "client":
        if reminder.facture_id:
            from app.models import Facture

            facture = db.get(Facture, reminder.facture_id)
            if facture:
                case = db.get(Case, facture.case_id)
                if case:
                    customer = db.get(Customer, case.customer_id)
                    if customer and customer.email:
                        return customer.email
        payment = db.get(Payment, reminder.target_id)
        if payment:
            case = db.get(Case, payment.case_id)
            if case:
                customer = db.get(Customer, case.customer_id)
                if customer and customer.email:
                    return customer.email
    elif reminder.target_type == "payer_organization":
        org = db.get(PayerOrganization, reminder.target_id)
        if org and org.contact_email:
            return org.contact_email
    return ""


def send_reminder(db: Session, tenant_id: int, reminder_id: int, user_id: int) -> ReminderResponse:
    reminder = reminder_repo.get_reminder(db, reminder_id=reminder_id, tenant_id=tenant_id)
    if not reminder:
        raise NotFoundError("reminder", reminder_id)

    if reminder.channel == "email" and reminder.content:
        recipient = _resolve_recipient_email(db, reminder)
        if not recipient:
            logger.warning("no_email_for_reminder", tenant_id=tenant_id, reminder_id=reminder_id)
            reminder_repo.update_status(db, reminder, "failed")
            return ReminderResponse.model_validate(reminder)

        from app.integrations.email_sender import email_sender

        success = email_sender.send_email(
            to=recipient,
            subject="Relance OptiFlow",
            body_html=f"<p>{reminder.content}</p>",
        )
        new_status = "sent" if success else "failed"
    else:
        new_status = "sent"

    reminder_repo.update_status(db, reminder, new_status)

    if user_id:
        event_name = "RelanceEnvoyee" if new_status == "sent" else "RelanceEchouee"
        event_service.emit_event(db, tenant_id, event_name, "reminder", reminder_id, user_id)

    logger.info("reminder_sent", tenant_id=tenant_id, reminder_id=reminder_id, status=new_status)
    return ReminderResponse.model_validate(reminder)


# --- List + Stats ---


def list_reminders(
    db: Session, tenant_id: int, status: str | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[ReminderResponse], int]:
    items, total = reminder_repo.list_reminders(db, tenant_id, status, limit, offset)
    return [ReminderResponse.model_validate(r) for r in items], total


def get_stats(db: Session, tenant_id: int) -> ReminderStats:
    data = reminder_repo.get_stats(db, tenant_id)
    return ReminderStats(**data)


# --- Templates ---


def list_templates(db: Session, tenant_id: int) -> list[ReminderTemplateResponse]:
    templates = reminder_repo.list_templates(db, tenant_id)
    return [ReminderTemplateResponse.model_validate(t) for t in templates]


def create_template(
    db: Session, tenant_id: int, payload: ReminderTemplateCreate, user_id: int
) -> ReminderTemplateResponse:
    t = reminder_repo.create_template(
        db,
        tenant_id,
        payload.name,
        payload.channel,
        payload.payer_type,
        payload.subject,
        payload.body,
        payload.is_default,
    )
    logger.info("template_created", tenant_id=tenant_id, template_id=t.id)
    return ReminderTemplateResponse.model_validate(t)
