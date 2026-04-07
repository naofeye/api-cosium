"""Celery tasks for automated ERP synchronization.

Task 1: sync_all_cosium — runs daily at 6:00 AM
  Calls sync_customers, sync_invoices, sync_payments, sync_prescriptions, sync_all_reference
  Logs results, handles errors gracefully.

Task 2: test_cosium_connection — runs every 4 hours
  Tests if Cosium cookie/token is still valid.
  If 401: creates a notification for admin users "Cookie Cosium expire".
  If OK: logs success.

Task 3: check_expiring_prescriptions — runs weekly (Monday 10 AM)
  Finds clients whose latest prescription is older than 2 years.
  Creates a notification for admin/manager users.
"""

from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("sync_tasks")


@celery_app.task(
    name="app.tasks.sync_tasks.sync_all_tenants",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    time_limit=3600,
    soft_time_limit=3300,
)
def sync_all_tenants(self) -> dict[str, int]:
    """Sync all active tenants with their ERP (daily incremental sync)."""
    from app.db.session import SessionLocal
    from app.models import Tenant

    db = SessionLocal()
    try:
        tenants = (
            db.query(Tenant)
            .filter(Tenant.is_active.is_(True), Tenant.cosium_connected.is_(True))
            .all()
        )
        synced = 0
        failed = 0

        from app.core.redis_cache import acquire_lock, get_redis_client, release_lock

        today = datetime.now(UTC).strftime("%Y-%m-%d")

        for tenant in tenants:
            # Idempotency: skip if this tenant was already synced today
            idempotency_key = f"sync:{tenant.id}:{today}"
            redis_client = get_redis_client()
            if redis_client:
                try:
                    if redis_client.exists(idempotency_key):
                        logger.info(
                            "tenant_sync_skipped_already_done",
                            tenant_id=tenant.id,
                            idempotency_key=idempotency_key,
                        )
                        continue
                except Exception:
                    pass  # Redis unavailable — proceed without idempotency check

            lock_key = f"sync:tenant:{tenant.id}"
            if not acquire_lock(lock_key, ttl=1200):
                logger.warning("tenant_sync_skipped_locked", tenant_id=tenant.id)
                continue
            try:
                _sync_single_tenant(db, tenant.id)
                logger.info("tenant_sync_done", tenant_id=tenant.id, tenant_name=tenant.name)
                synced += 1
                # Mark tenant as synced today (TTL = time_limit = 3600s)
                if redis_client:
                    try:
                        redis_client.setex(idempotency_key, 3600, "1")
                    except Exception:
                        pass
            except Exception as e:
                logger.error("tenant_sync_failed", tenant_id=tenant.id, error=str(e))
                db.rollback()
                failed += 1
            finally:
                release_lock(lock_key)

        total = len(tenants)
        logger.info("sync_all_tenants_complete", synced=synced, failed=failed, total=total)

        if failed > 0:
            logger.error("sync_all_tenants_partial_failure", failed=failed, total=total)
            # Creer une notification admin pour chaque tenant actif
            try:
                from app.models import Notification

                for tenant in tenants:
                    notif = Notification(
                        tenant_id=tenant.id,
                        type="error",
                        title="Echec de synchronisation",
                        message=f"Synchronisation Cosium echouee pour {failed}/{total} tenants. Verifiez les logs.",
                        created_at=datetime.now(UTC).replace(tzinfo=None),  # naive datetime for DB compatibility
                    )
                    db.add(notif)
                db.commit()
            except Exception:
                pass  # Ne pas bloquer si la notification echoue
            raise RuntimeError(
                f"sync_all_tenants partial failure: {failed}/{total} tenants failed"
            )

        return {"synced": synced, "failed": failed, "total": total}
    finally:
        db.close()


def _sync_single_tenant(db, tenant_id: int) -> dict[str, dict]:
    """Run all sync functions for a single tenant. Returns results per domain."""
    from app.services import erp_sync_service
    from app.services.cosium_reference_sync import sync_all_reference

    results: dict[str, dict] = {}

    sync_functions = [
        ("customers", erp_sync_service.sync_customers),
        ("invoices", erp_sync_service.sync_invoices),
        ("payments", erp_sync_service.sync_payments),
        ("prescriptions", erp_sync_service.sync_prescriptions),
        ("reference_data", sync_all_reference),
    ]

    for name, sync_fn in sync_functions:
        try:
            result = sync_fn(db, tenant_id=tenant_id)
            results[name] = result
            logger.info(
                "sync_domain_done",
                tenant_id=tenant_id,
                domain=name,
                result=result,
            )
        except Exception as e:
            results[name] = {"error": str(e)}
            logger.error(
                "sync_domain_failed",
                tenant_id=tenant_id,
                domain=name,
                error=str(e),
            )

    return results


@celery_app.task(
    name="app.tasks.sync_tasks.test_cosium_connection",
    bind=True,
    max_retries=1,
    default_retry_delay=120,
)
def test_cosium_connection(self) -> dict[str, int]:
    """Test Cosium connectivity for all active tenants (every 4 hours).

    If a tenant's connection fails with 401, create a notification for admin users.
    """
    from app.db.session import SessionLocal
    from app.models import Tenant
    from app.models.notification import Notification
    from app.models.tenant import TenantUser

    db = SessionLocal()
    try:
        tenants = (
            db.query(Tenant)
            .filter(Tenant.is_active.is_(True), Tenant.cosium_connected.is_(True))
            .all()
        )
        ok_count = 0
        fail_count = 0

        for tenant in tenants:
            try:
                _test_tenant_connection(db, tenant.id)
                logger.info("cosium_connection_ok", tenant_id=tenant.id, tenant_name=tenant.name)
                ok_count += 1
            except Exception as e:
                fail_count += 1
                error_msg = str(e)
                is_auth_error = "401" in error_msg or "Unauthorized" in error_msg or "auth" in error_msg.lower()

                logger.warning(
                    "cosium_connection_failed",
                    tenant_id=tenant.id,
                    tenant_name=tenant.name,
                    error=error_msg,
                    is_auth_error=is_auth_error,
                )

                # Create notification for admin users of this tenant
                admin_user_ids = (
                    db.query(TenantUser.user_id)
                    .filter(
                        TenantUser.tenant_id == tenant.id,
                        TenantUser.role.in_(["admin", "owner"]),
                    )
                    .all()
                )

                title = (
                    "Cookie Cosium expire"
                    if is_auth_error
                    else "Connexion Cosium echouee"
                )
                message = (
                    f"La connexion a Cosium pour le magasin {tenant.name} a echoue. "
                    f"Veuillez reconnecter votre compte Cosium dans les parametres."
                    if is_auth_error
                    else f"Erreur de connexion Cosium pour {tenant.name} : {error_msg[:200]}"
                )

                for (uid,) in admin_user_ids:
                    notification = Notification(
                        tenant_id=tenant.id,
                        user_id=uid,
                        type="warning" if is_auth_error else "error",
                        title=title,
                        message=message,
                        entity_type="tenant",
                        entity_id=tenant.id,
                        created_at=datetime.now(UTC).replace(tzinfo=None),  # naive datetime for DB compatibility
                    )
                    db.add(notification)

                db.commit()

        logger.info("test_cosium_connection_complete", ok=ok_count, failed=fail_count)

        if fail_count > 0:
            logger.error(
                "test_cosium_connection_has_failures",
                ok=ok_count,
                failed=fail_count,
            )
            raise RuntimeError(
                f"test_cosium_connection: {fail_count} tenant(s) failed connectivity check"
            )

        return {"ok": ok_count, "failed": fail_count}
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.sync_tasks.bulk_download_cosium_documents",
    bind=True,
    max_retries=0,
)
def bulk_download_cosium_documents(
    self,
    tenant_id: int,
    user_id: int = 0,
    max_customers: int | None = None,
    delay_docs: float = 1.0,
    delay_customers: float = 2.0,
) -> dict:
    """Background task for bulk document download from Cosium to MinIO.

    Designed to run for hours. Rate-limited to avoid overloading Cosium.
    """
    from app.db.session import SessionLocal
    from app.services.cosium_document_sync import sync_all_documents

    db = SessionLocal()
    try:
        logger.info(
            "bulk_download_start",
            tenant_id=tenant_id,
            user_id=user_id,
            max_customers=max_customers,
        )
        result = sync_all_documents(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            delay_between_customers=delay_customers,
            delay_between_docs=delay_docs,
            max_customers=max_customers,
        )
        logger.info("bulk_download_complete", tenant_id=tenant_id, result=result)
        return result
    except Exception as e:
        logger.error("bulk_download_failed", tenant_id=tenant_id, error=str(e))
        return {"error": str(e)}
    finally:
        db.close()


def _test_tenant_connection(db, tenant_id: int) -> None:
    """Test a single tenant's Cosium connection by making a lightweight GET."""
    from app.services.erp_sync_service import _authenticate_connector, _get_connector_for_tenant

    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)
    # Lightweight test: fetch first page of customers with size=1
    connector.get_customers(page=0, page_size=1)


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
    from app.models import Customer, Tenant
    from app.models.cosium_data import CosiumPrescription
    from app.models.notification import Notification
    from app.models.tenant import TenantUser

    db = SessionLocal()
    try:
        tenants = (
            db.query(Tenant)
            .filter(Tenant.is_active.is_(True))
            .all()
        )

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
                select(Customer.id, Customer.first_name, Customer.last_name, latest_rx.c.latest_date)
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
            staff_user_ids = (
                db.query(TenantUser.user_id)
                .filter(
                    TenantUser.tenant_id == tenant.id,
                    TenantUser.role.in_(["admin", "owner", "manager"]),
                )
                .all()
            )

            for client_row in expired_clients:
                client_id, first_name, last_name, latest_date = client_row
                client_name = f"{last_name} {first_name}".strip()

                for (uid,) in staff_user_ids:
                    # Check if notification already exists (avoid duplicates)
                    existing = db.query(Notification).filter(
                        Notification.tenant_id == tenant.id,
                        Notification.user_id == uid,
                        Notification.entity_type == "prescription_expiry",
                        Notification.entity_id == client_id,
                        Notification.created_at > datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7),  # naive datetime for DB compatibility
                    ).first()

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
