"""Task Celery : check_expiring_prescriptions — alertes ordonnances > 2 ans."""

from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("sync_tasks")


@celery_app.task(
    name="app.tasks.sync_tasks.check_expiring_prescriptions",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
)
def check_expiring_prescriptions(self) -> dict[str, int]:
    """Check for prescriptions > 2 years old and create notifications.

    Runs weekly on Mondays at 10 AM. For each active tenant, finds clients
    whose latest prescription is older than 2 years and creates a notification
    for admin/manager users.
    """
    from sqlalchemy import func as sa_func
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models import Customer
    from app.models.cosium_data import CosiumPrescription
    from app.models.notification import Notification
    from app.repositories import onboarding_repo, tenant_user_repo

    db = SessionLocal()
    try:
        tenants = onboarding_repo.get_active_tenants(db)

        total_notified = 0
        two_years_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=730)  # naive datetime for DB compatibility

        for tenant in tenants:
            # Subquery: latest prescription date per customer
            latest_rx = (
                select(
                    CosiumPrescription.customer_id,
                    sa_func.max(CosiumPrescription.prescription_date).label("latest_date"),
                )
                .where(
                    CosiumPrescription.tenant_id == tenant.id,
                    CosiumPrescription.customer_id.isnot(None),
                )
                .group_by(CosiumPrescription.customer_id)
                .subquery()
            )

            # Find customers whose latest prescription is older than 2 years
            expired_clients = db.execute(
                select(
                    Customer.id,
                    Customer.first_name,
                    Customer.last_name,
                    latest_rx.c.latest_date,
                )
                .join(latest_rx, Customer.id == latest_rx.c.customer_id)
                .where(
                    Customer.tenant_id == tenant.id,
                    latest_rx.c.latest_date < str(two_years_ago.date()),
                )
                .limit(100)
            ).all()

            if not expired_clients:
                continue

            # Get admin/manager users for this tenant
            staff_user_ids = tenant_user_repo.list_user_ids_by_roles(
                db, tenant.id, ["admin", "owner", "manager"]
            )

            for client_row in expired_clients:
                client_id, first_name, last_name, latest_date = client_row
                client_name = f"{last_name} {first_name}".strip()

                for uid in staff_user_ids:
                    # Check if notification already exists (avoid duplicates)
                    existing = (
                        db.query(Notification)
                        .filter(
                            Notification.tenant_id == tenant.id,
                            Notification.user_id == uid,
                            Notification.entity_type == "prescription_expiry",
                            Notification.entity_id == client_id,
                            Notification.created_at
                            > datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7),  # naive datetime for DB compatibility
                        )
                        .first()
                    )

                    if existing:
                        continue

                    notification = Notification(
                        tenant_id=tenant.id,
                        user_id=uid,
                        type="warning",
                        title="Ordonnance expiree",
                        message=(
                            f"L'ordonnance de {client_name} date de plus de 2 ans "
                            f"(derniere : {latest_date}). "
                            f"Pensez a contacter le client pour un renouvellement."
                        ),
                        entity_type="prescription_expiry",
                        entity_id=client_id,
                        created_at=datetime.now(UTC).replace(tzinfo=None),  # naive datetime for DB compatibility
                    )
                    db.add(notification)
                    total_notified += 1

            db.commit()

        logger.info(
            "check_expiring_prescriptions_complete",
            total_notified=total_notified,
        )
        return {"total_notified": total_notified}
    except Exception as e:
        logger.error("check_expiring_prescriptions_failed", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()
