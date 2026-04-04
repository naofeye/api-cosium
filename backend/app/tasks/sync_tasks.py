"""Celery tasks for automated ERP synchronization."""

from app.core.logging import get_logger
from app.tasks import celery_app

logger = get_logger("sync_tasks")


@celery_app.task(name="app.tasks.sync_tasks.sync_all_tenants")
def sync_all_tenants() -> dict[str, int]:
    """Sync all active tenants with their ERP (hourly)."""
    from app.db.session import SessionLocal
    from app.models import Tenant

    db = SessionLocal()
    try:
        tenants = db.query(Tenant).filter(Tenant.is_active.is_(True), Tenant.cosium_connected.is_(True)).all()
        synced = 0
        failed = 0

        for tenant in tenants:
            try:
                from app.services import erp_sync_service

                erp_sync_service.sync_customers(db, tenant_id=tenant.id)
                logger.info("tenant_sync_done", tenant_id=tenant.id, tenant_name=tenant.name)
                synced += 1
            except Exception as e:
                logger.error("tenant_sync_failed", tenant_id=tenant.id, error=str(e))
                failed += 1

        logger.info("sync_all_tenants_complete", synced=synced, failed=failed, total=len(tenants))
        return {"synced": synced, "failed": failed, "total": len(tenants)}
    finally:
        db.close()
