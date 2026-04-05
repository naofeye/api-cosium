"""Celery tasks for automated ERP synchronization.

Task 1: sync_all_cosium — runs daily at 6:00 AM
  Calls sync_customers, sync_invoices, sync_payments, sync_prescriptions, sync_all_reference
  Logs results, handles errors gracefully.

Task 2: test_cosium_connection — runs every 4 hours
  Tests if Cosium cookie/token is still valid.
  If 401: creates a notification for admin users "Cookie Cosium expire".
  If OK: logs success.
"""

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("sync_tasks")


@celery_app.task(name="app.tasks.sync_tasks.sync_all_tenants")
def sync_all_tenants() -> dict[str, int]:
    """Sync all active tenants with their ERP (daily full sync)."""
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

        for tenant in tenants:
            try:
                _sync_single_tenant(db, tenant.id)
                logger.info("tenant_sync_done", tenant_id=tenant.id, tenant_name=tenant.name)
                synced += 1
            except Exception as e:
                logger.error("tenant_sync_failed", tenant_id=tenant.id, error=str(e))
                failed += 1

        logger.info("sync_all_tenants_complete", synced=synced, failed=failed, total=len(tenants))
        return {"synced": synced, "failed": failed, "total": len(tenants)}
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


@celery_app.task(name="app.tasks.sync_tasks.test_cosium_connection")
def test_cosium_connection() -> dict[str, int]:
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
                        created_at=datetime.now(UTC),
                    )
                    db.add(notification)

                db.commit()

        logger.info("test_cosium_connection_complete", ok=ok_count, failed=fail_count)
        return {"ok": ok_count, "failed": fail_count}
    finally:
        db.close()


def _test_tenant_connection(db, tenant_id: int) -> None:
    """Test a single tenant's Cosium connection by making a lightweight GET."""
    from app.services.erp_sync_service import _authenticate_connector, _get_connector_for_tenant

    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)
    # Lightweight test: fetch first page of customers with size=1
    connector.get_customers(page=0, page_size=1)
