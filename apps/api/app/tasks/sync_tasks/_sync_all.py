"""Task Celery : sync_all_tenants — sync incrémentale quotidienne."""

from datetime import UTC, datetime

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
    from app.repositories import onboarding_repo

    db = SessionLocal()
    try:
        tenants = onboarding_repo.get_active_cosium_tenants(db)
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
                logger.info(
                    "tenant_sync_done", tenant_id=tenant.id, tenant_name=tenant.name
                )
                synced += 1
                # Mark tenant as synced today (TTL = time_limit = 3600s)
                if redis_client:
                    try:
                        redis_client.setex(idempotency_key, 3600, "1")
                    except Exception:
                        pass
            except Exception as e:
                logger.error("tenant_sync_failed", tenant_id=tenant.id, error=str(e))
                from app.core.sentry_helpers import report_incident_to_sentry

                report_incident_to_sentry(
                    e,
                    "cosium_sync_failed",
                    category="sync",
                    tenant_id=tenant.id,
                    tenant_name=tenant.name,
                )
                db.rollback()
                failed += 1
            finally:
                release_lock(lock_key)

        total = len(tenants)
        logger.info(
            "sync_all_tenants_complete", synced=synced, failed=failed, total=total
        )

        if failed > 0:
            logger.error(
                "sync_all_tenants_partial_failure", failed=failed, total=total
            )
            from app.core.sentry_helpers import report_incident_to_sentry

            report_incident_to_sentry(
                RuntimeError(f"{failed}/{total} tenants failed sync"),
                "cosium_sync_partial_failure",
                category="sync",
                level="warning",
                failed=failed,
                total=total,
            )
            # Creer une notification admin pour chaque tenant actif
            try:
                from app.models import Notification

                for tenant in tenants:
                    notif = Notification(
                        tenant_id=tenant.id,
                        type="error",
                        title="Echec de synchronisation",
                        message=(
                            f"Synchronisation Cosium echouee pour {failed}/{total} tenants. "
                            f"Verifiez les logs."
                        ),
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
            from app.core.sentry_helpers import report_incident_to_sentry

            report_incident_to_sentry(
                e,
                "cosium_sync_domain_failed",
                category="sync",
                tenant_id=tenant_id,
                domain=name,
            )

    return results
