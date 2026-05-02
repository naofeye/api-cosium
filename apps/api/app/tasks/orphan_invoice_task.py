"""Celery task : reconciliation periodique des factures Cosium orphelines.

Tourne quotidiennement (Celery beat) pour rattraper les factures laissees
sans customer_id par la sync precedente. Utile quand de nouveaux clients
sont importes apres les factures.
"""
from __future__ import annotations

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import Tenant
from app.services.orphan_invoice_service import reconcile_orphan_invoices
from app.tasks import celery_app

logger = get_logger("orphan_invoice_task")


@celery_app.task(
    name="app.tasks.orphan_invoice_task.reconcile_all_tenants_orphans",
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    time_limit=1800,
)
def reconcile_all_tenants_orphans(self) -> dict[str, dict[str, int]]:
    """Cross-tenant : rejoue le matching pour tous les tenants actifs."""
    db = SessionLocal()
    try:
        tenants = db.scalars(
            select(Tenant).where(Tenant.is_active.is_(True))
        ).all()
        results: dict[str, dict[str, int]] = {}
        for tenant in tenants:
            try:
                result = reconcile_orphan_invoices(db, tenant.id, limit=5000)
                results[tenant.slug] = result
            except Exception as exc:
                logger.error(
                    "orphan_reconcile_tenant_failed",
                    tenant_id=tenant.id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                results[tenant.slug] = {
                    "processed": 0,
                    "matched": 0,
                    "still_orphan": -1,
                    "error": 1,
                }
        return results
    except Exception as exc:
        logger.error("orphan_reconcile_all_failed", error=str(exc))
        raise self.retry(exc=exc) from exc
    finally:
        db.close()
