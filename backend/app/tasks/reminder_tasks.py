"""
Celery tasks for automated reminder generation.

Tasks:
    1. auto_generate_reminders — executes all active plans daily at 8 AM.
    2. check_overdue_invoices — checks for Cosium invoices overdue > 30 days
       and creates reminders + sends emails. Runs weekly on Mondays at 9 AM.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import Customer, Tenant
from app.models.cosium_data import CosiumInvoice
from app.repositories import reminder_repo
from app.services import reminder_service
from app.tasks import celery_app

logger = get_logger("reminder_tasks")


@celery_app.task(
    name="app.tasks.reminder_tasks.auto_generate_reminders",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def auto_generate_reminders(self) -> dict[str, int]:
    """Execute all active reminder plans against overdue items.

    Returns a summary of created reminders per plan.
    """
    db = SessionLocal()
    try:
        # Iterate over all tenants
        tenants = db.scalars(select(Tenant).where(Tenant.is_active.is_(True))).all()
        total_created = 0
        plan_results: dict[str, int] = {}

        for tenant in tenants:
            plans = reminder_repo.list_plans(db, tenant.id)
            active_plans = [p for p in plans if p.is_active]

            for plan in active_plans:
                created = reminder_service.execute_plan(db, tenant.id, plan.id, user_id=0)
                count = len(created)
                plan_results[f"{tenant.slug}:{plan.name}"] = count
                total_created += count

                # Auto-send email reminders
                for r in created:
                    if r.channel == "email":
                        reminder_service.send_reminder(db, tenant.id, r.id, user_id=0)

        logger.info(
            "auto_generate_complete",
            tenants_processed=len(tenants),
            reminders_created=total_created,
        )
        return plan_results
    except Exception as exc:
        logger.error("auto_generate_failed", error=str(exc))
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.reminder_tasks.check_overdue_invoices",
    bind=True,
    max_retries=1,
    default_retry_delay=600,
)
def check_overdue_invoices(self) -> dict[str, int]:
    """Check for Cosium invoices overdue > 30 days and create reminders.

    For each tenant, finds customers with outstanding balance > 0 whose oldest
    unpaid invoice is older than 30 days. If no reminder was already sent in
    the last 30 days for that customer, creates a reminder and sends an email.

    Runs weekly (Monday 9 AM) via Celery Beat.
    """
    from app.models import Reminder

    db = SessionLocal()
    try:
        tenants = db.scalars(select(Tenant).where(Tenant.is_active.is_(True))).all()
        thirty_days_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
        results: dict[str, int] = {}

        for tenant in tenants:
            reminders_created = 0

            # Find customers with overdue invoices (outstanding > 0, invoice > 30 days old)
            overdue_rows = db.execute(
                select(
                    CosiumInvoice.customer_id,
                    CosiumInvoice.customer_name,
                    func.sum(CosiumInvoice.outstanding_balance).label("total_due"),
                    func.min(CosiumInvoice.invoice_date).label("oldest_date"),
                )
                .where(
                    CosiumInvoice.outstanding_balance > 0,
                    CosiumInvoice.type == "INVOICE",
                    CosiumInvoice.invoice_date < thirty_days_ago,
                    CosiumInvoice.tenant_id == tenant.id,
                )
                .group_by(CosiumInvoice.customer_id, CosiumInvoice.customer_name)
                .having(func.sum(CosiumInvoice.outstanding_balance) > 0)
            ).all()

            for row in overdue_rows:
                customer_id = row.customer_id
                customer_name = row.customer_name or "Client inconnu"
                total_due = float(row.total_due or 0)

                if not customer_id:
                    continue

                # Check if reminder already sent in last 30 days for this client
                existing = db.scalars(
                    select(Reminder).where(
                        Reminder.tenant_id == tenant.id,
                        Reminder.target_type == "client",
                        Reminder.target_id == customer_id,
                        Reminder.created_at >= thirty_days_ago,
                    ).limit(1)
                ).first()

                if existing:
                    continue

                # Calculate days overdue
                oldest_date = row.oldest_date
                days_overdue = (datetime.now(UTC).replace(tzinfo=None) - oldest_date).days if oldest_date else 30

                # Build reminder content
                content = (
                    f"Bonjour {customer_name},\n\n"
                    f"Nous constatons un solde impaye de {total_due:.2f} EUR "
                    f"depuis {days_overdue} jours.\n"
                    f"Merci de bien vouloir regulariser votre situation.\n\n"
                    f"Cordialement,\nOptiFlow"
                )

                # Create the reminder
                reminder = reminder_repo.create_reminder(
                    db,
                    tenant_id=tenant.id,
                    plan_id=None,
                    target_type="client",
                    target_id=customer_id,
                    facture_id=None,
                    pec_request_id=None,
                    channel="email",
                    content=content,
                    template_name=None,
                    sent_at=None,
                    user_id=0,
                )

                # Try to send email
                customer_obj = db.get(Customer, customer_id)
                if customer_obj and customer_obj.email:
                    from app.integrations.email_sender import email_sender

                    subject = f"Relance — Solde impaye de {total_due:.2f} EUR"
                    body_html = content.replace("\n", "<br>")
                    success = email_sender.send_email(
                        to=customer_obj.email,
                        subject=subject,
                        body_html=f"<p>{body_html}</p>",
                    )
                    new_status = "sent" if success else "failed"
                    reminder_repo.update_status(db, reminder, new_status)
                    if success:
                        reminders_created += 1
                else:
                    # No email available — mark as pending
                    reminder_repo.update_status(db, reminder, "pending")
                    reminders_created += 1

            results[tenant.slug] = reminders_created
            if reminders_created > 0:
                logger.info(
                    "overdue_reminders_created",
                    tenant=tenant.slug,
                    count=reminders_created,
                )

        total = sum(results.values())
        logger.info("check_overdue_complete", tenants_processed=len(tenants), total_reminders=total)
        return results
    except Exception as exc:
        logger.error("check_overdue_failed", error=str(exc))
        raise self.retry(exc=exc)
    finally:
        db.close()
