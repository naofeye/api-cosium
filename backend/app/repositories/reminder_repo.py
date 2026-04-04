from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Case,
    Customer,
    PayerOrganization,
    Payment,
    PecRequest,
    Reminder,
    ReminderPlan,
    ReminderTemplate,
)

# --- Plans ---


def list_plans(db: Session, tenant_id: int) -> list[ReminderPlan]:
    return list(
        db.scalars(select(ReminderPlan).where(ReminderPlan.tenant_id == tenant_id).order_by(ReminderPlan.id)).all()
    )


def get_plan(db: Session, plan_id: int, tenant_id: int) -> ReminderPlan | None:
    return db.scalars(
        select(ReminderPlan).where(
            ReminderPlan.id == plan_id,
            ReminderPlan.tenant_id == tenant_id,
        )
    ).first()


def create_plan(
    db: Session,
    tenant_id: int,
    name: str,
    payer_type: str,
    rules_json: str,
    channel_sequence: str,
    interval_days: int,
    is_active: bool,
) -> ReminderPlan:
    plan = ReminderPlan(
        tenant_id=tenant_id,
        name=name,
        payer_type=payer_type,
        rules_json=rules_json,
        channel_sequence=channel_sequence,
        interval_days=interval_days,
        is_active=is_active,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def toggle_plan(db: Session, plan: ReminderPlan, is_active: bool) -> None:
    plan.is_active = is_active
    db.commit()


# --- Reminders ---


def create_reminder(
    db: Session,
    tenant_id: int,
    plan_id: int | None,
    target_type: str,
    target_id: int,
    facture_id: int | None,
    pec_request_id: int | None,
    channel: str,
    content: str | None,
    template_used: str | None,
    scheduled_at: datetime | None,
    created_by: int | None,
) -> Reminder:
    r = Reminder(
        tenant_id=tenant_id,
        plan_id=plan_id,
        target_type=target_type,
        target_id=target_id,
        facture_id=facture_id,
        pec_request_id=pec_request_id,
        channel=channel,
        content=content,
        template_used=template_used,
        scheduled_at=scheduled_at,
        created_by=created_by,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def list_reminders(
    db: Session, tenant_id: int, status: str | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[Reminder], int]:
    q = select(Reminder).where(Reminder.tenant_id == tenant_id)
    if status:
        q = q.where(Reminder.status == status)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Reminder.created_at.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def update_status(db: Session, reminder: Reminder, status: str) -> None:
    reminder.status = status
    if status == "sent":
        reminder.sent_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()


def get_reminder(db: Session, reminder_id: int, tenant_id: int) -> Reminder | None:
    return db.scalars(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.tenant_id == tenant_id,
        )
    ).first()


def count_reminders_for_target(
    db: Session, tenant_id: int, target_type: str, target_id: int, facture_id: int | None
) -> int:
    q = (
        select(func.count())
        .select_from(Reminder)
        .where(
            Reminder.tenant_id == tenant_id,
            Reminder.target_type == target_type,
            Reminder.target_id == target_id,
        )
    )
    if facture_id:
        q = q.where(Reminder.facture_id == facture_id)
    return db.scalar(q) or 0


# --- Templates ---


def list_templates(db: Session, tenant_id: int) -> list[ReminderTemplate]:
    return list(
        db.scalars(
            select(ReminderTemplate).where(ReminderTemplate.tenant_id == tenant_id).order_by(ReminderTemplate.id)
        ).all()
    )


def get_template(db: Session, template_id: int, tenant_id: int) -> ReminderTemplate | None:
    return db.scalars(
        select(ReminderTemplate).where(
            ReminderTemplate.id == template_id,
            ReminderTemplate.tenant_id == tenant_id,
        )
    ).first()


def get_default_template(db: Session, tenant_id: int, channel: str, payer_type: str) -> ReminderTemplate | None:
    return db.scalars(
        select(ReminderTemplate).where(
            ReminderTemplate.tenant_id == tenant_id,
            ReminderTemplate.channel == channel,
            ReminderTemplate.payer_type == payer_type,
            ReminderTemplate.is_default.is_(True),
        )
    ).first()


def create_template(
    db: Session,
    tenant_id: int,
    name: str,
    channel: str,
    payer_type: str,
    subject: str | None,
    body: str,
    is_default: bool,
) -> ReminderTemplate:
    t = ReminderTemplate(
        tenant_id=tenant_id,
        name=name,
        channel=channel,
        payer_type=payer_type,
        subject=subject,
        body=body,
        is_default=is_default,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# --- Overdue queries ---


def get_overdue_payments(db: Session, tenant_id: int, min_days: int = 7) -> list[dict]:
    rows = db.execute(
        select(
            Payment.id,
            Payment.case_id,
            Payment.facture_id,
            Payment.payer_type,
            Payment.amount_due,
            Payment.amount_paid,
            Payment.created_at,
            Customer.first_name,
            Customer.last_name,
            Customer.email.label("customer_email"),
        )
        .join(Case, Case.id == Payment.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .where(
            Payment.tenant_id == tenant_id,
            Payment.status.in_(["pending", "partial"]),
            Payment.amount_paid < Payment.amount_due,
        )
        .order_by(Payment.created_at)
    ).all()

    now = datetime.now(UTC).replace(tzinfo=None)
    results = []
    for r in rows:
        days = (now - r.created_at).days if r.created_at else 0
        if days >= min_days:
            results.append(
                {
                    "entity_type": "payment",
                    "entity_id": r.id,
                    "case_id": r.case_id,
                    "facture_id": r.facture_id,
                    "customer_name": f"{r.first_name} {r.last_name}",
                    "customer_email": r.customer_email,
                    "payer_type": r.payer_type,
                    "amount": float(r.amount_due) - float(r.amount_paid),
                    "days_overdue": days,
                }
            )
    return results


def get_overdue_pec(db: Session, tenant_id: int, min_days: int = 7) -> list[dict]:
    rows = db.execute(
        select(
            PecRequest.id,
            PecRequest.case_id,
            PecRequest.organization_id,
            PecRequest.montant_demande,
            PecRequest.montant_accorde,
            PecRequest.status,
            PecRequest.created_at,
            Customer.first_name,
            Customer.last_name,
            PayerOrganization.name.label("org_name"),
            PayerOrganization.contact_email.label("org_email"),
            PayerOrganization.type.label("org_type"),
        )
        .join(Case, Case.id == PecRequest.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .join(PayerOrganization, PayerOrganization.id == PecRequest.organization_id)
        .where(
            PecRequest.tenant_id == tenant_id,
            PecRequest.status.in_(["soumise", "en_attente"]),
        )
        .order_by(PecRequest.created_at)
    ).all()

    now = datetime.now(UTC).replace(tzinfo=None)
    results = []
    for r in rows:
        days = (now - r.created_at).days if r.created_at else 0
        if days >= min_days:
            results.append(
                {
                    "entity_type": "pec_request",
                    "entity_id": r.id,
                    "case_id": r.case_id,
                    "facture_id": None,
                    "pec_request_id": r.id,
                    "customer_name": f"{r.first_name} {r.last_name}",
                    "customer_email": r.org_email,
                    "payer_type": r.org_type,
                    "org_name": r.org_name,
                    "amount": float(r.montant_demande),
                    "days_overdue": days,
                }
            )
    return results


def get_all_overdue(db: Session, tenant_id: int, min_days: int = 7) -> list[dict]:
    return get_overdue_payments(db, tenant_id, min_days) + get_overdue_pec(db, tenant_id, min_days)


# --- Stats ---


def get_stats(db: Session, tenant_id: int) -> dict:
    total_sent = (
        db.scalar(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.status == "sent",
            )
        )
        or 0
    )
    total_responded = (
        db.scalar(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.tenant_id == tenant_id,
                Reminder.status == "responded",
            )
        )
        or 0
    )

    overdue = get_overdue_payments(db, tenant_id, min_days=0)
    total_amount = sum(item["amount"] for item in overdue)

    age_buckets: dict[str, float] = {"0-30j": 0, "30-60j": 0, "60-90j": 0, "90j+": 0}
    for item in overdue:
        d = item["days_overdue"]
        if d < 30:
            age_buckets["0-30j"] += item["amount"]
        elif d < 60:
            age_buckets["30-60j"] += item["amount"]
        elif d < 90:
            age_buckets["60-90j"] += item["amount"]
        else:
            age_buckets["90j+"] += item["amount"]

    return {
        "total_overdue_amount": round(total_amount, 2),
        "total_reminders_sent": total_sent,
        "total_responded": total_responded,
        "recovery_rate": round(total_responded / total_sent * 100, 1) if total_sent > 0 else 0,
        "overdue_by_age": {k: round(v, 2) for k, v in age_buckets.items()},
    }
