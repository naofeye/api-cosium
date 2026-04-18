"""Task Celery : test_cosium_connection — vérification token/cookie Cosium toutes les 4h."""

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("sync_tasks")


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
    from app.models.notification import Notification
    from app.repositories import onboarding_repo, tenant_user_repo

    db = SessionLocal()
    try:
        tenants = onboarding_repo.get_active_cosium_tenants(db)
        ok_count = 0
        fail_count = 0

        for tenant in tenants:
            try:
                _test_tenant_connection(db, tenant.id)
                logger.info(
                    "cosium_connection_ok",
                    tenant_id=tenant.id,
                    tenant_name=tenant.name,
                )
                ok_count += 1
            except Exception as e:
                fail_count += 1
                error_msg = str(e)
                is_auth_error = (
                    "401" in error_msg
                    or "Unauthorized" in error_msg
                    or "auth" in error_msg.lower()
                )

                logger.warning(
                    "cosium_connection_failed",
                    tenant_id=tenant.id,
                    tenant_name=tenant.name,
                    error=error_msg,
                    is_auth_error=is_auth_error,
                )

                # Create notification for admin users of this tenant
                admin_user_ids = tenant_user_repo.list_user_ids_by_roles(
                    db, tenant.id, ["admin", "owner"]
                )

                title = (
                    "Cookie Cosium expire" if is_auth_error else "Connexion Cosium echouee"
                )
                message = (
                    f"La connexion a Cosium pour le magasin {tenant.name} a echoue. "
                    f"Veuillez reconnecter votre compte Cosium dans les parametres."
                    if is_auth_error
                    else f"Erreur de connexion Cosium pour {tenant.name} : {error_msg[:200]}"
                )

                for uid in admin_user_ids:
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


def _test_tenant_connection(db, tenant_id: int) -> None:
    """Test a single tenant's Cosium connection by making a lightweight GET."""
    from app.services.erp_sync_service import (
        _authenticate_connector,
        _get_connector_for_tenant,
    )

    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)
    # Lightweight test: fetch first page of customers with size=1
    connector.get_customers(page=0, page_size=1)
