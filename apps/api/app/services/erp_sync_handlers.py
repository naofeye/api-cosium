"""Per-domain sync orchestration handlers.

Extracted from erp_sync_service.py to keep files under 300 lines.
Contains: sync_all orchestrator and enrich_top_clients_metadata.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import Customer
from app.services import audit_service
from app.services.erp_auth_service import (
    _authenticate_connector,
    _get_connector_for_tenant,
)

logger = get_logger("erp_sync_handlers")


def enrich_top_clients_metadata(
    db: Session, tenant_id: int, user_id: int = 0, limit: int = 500
) -> dict:
    """Fetch optician and ophthalmologist for top clients via sub-resource calls.

    This is a separate, optional enrichment step because it requires one API
    call per customer per sub-resource. Rate-limited to avoid overloading
    the Cosium server (0.3s between calls).

    Only enriches customers that don't already have the data populated.
    """
    import time

    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    # Only CosiumConnector supports sub-resource calls
    from app.integrations.cosium.cosium_connector import CosiumConnector

    if not isinstance(connector, CosiumConnector):
        return {"enriched": 0, "error": "Sub-resource enrichment only supported for Cosium"}

    # Get customers missing optician or ophthalmologist data, with cosium_id set
    customers_to_enrich = db.scalars(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id.isnot(None),
            Customer.deleted_at.is_(None),
            (Customer.optician_name.is_(None)) | (Customer.ophthalmologist_id.is_(None)),
        ).limit(limit)
    ).all()

    enriched = 0
    errors = 0

    for customer in customers_to_enrich:
        try:
            if not customer.optician_name:
                optician = connector.get_customer_optician(customer.cosium_id)
                if optician:
                    customer.optician_name = optician

            if not customer.ophthalmologist_id:
                oph_id = connector.get_customer_ophthalmologist_id(customer.cosium_id)
                if oph_id:
                    customer.ophthalmologist_id = oph_id

            customer.updated_at = datetime.now(UTC).replace(tzinfo=None)
            enriched += 1
            time.sleep(0.3)  # Rate limiting
        except (ConnectionError, TimeoutError, OSError) as exc:
            errors += 1
            logger.warning(
                "enrich_client_failed",
                customer_id=customer.id,
                cosium_id=customer.cosium_id,
                error=str(exc),
            )

        if enriched % 50 == 0 and enriched > 0:
            try:
                db.flush()
            except Exception as e:  # noqa: BLE001 — un batch rate ne doit pas aborter l'enrichissement
                logger.error("enrich_batch_flush_error", error=str(e), error_type=type(e).__name__)

    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("enrich_commit_failed", error=str(e))
        raise

    result = {"enriched": enriched, "errors": errors, "total_candidates": len(customers_to_enrich)}
    logger.info("enrich_top_clients_done", tenant_id=tenant_id, **result)
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "enrich_clients", 0, new_value=result)
    return result


def sync_all(db: Session, tenant_id: int, user_id: int = 0, *, full: bool = False) -> dict:
    """Orchestrate sync de tous les domaines ERP. Retourne dict keye par domaine.

    Capture les erreurs par domaine pour ne pas aborter l'orchestration : chaque
    domaine en erreur produit `{"error": "..."}` dans son slot, les autres continuent.
    Le flag `has_errors` est ajoute au resultat pour que le caller puisse decider
    (HTTP 207 Multi-Status vs 200).

    Domaines (dans l'ordre) :
    - customers (sync incrementale par nature — upsert par cosium_id)
    - invoices / payments / prescriptions (supportent `full`)
    - reference (calendar, mutuelles, doctors, brands, etc.)
    """
    # Import here to avoid circular imports
    from app.services.erp_sync_extras import sync_payments, sync_prescriptions
    from app.services.erp_sync_invoices import sync_invoices
    from app.services.erp_sync_service import sync_customers

    results: dict[str, object] = {}
    has_errors = False

    # Customers sync (deja incremental par nature — upsert par cosium_id)
    try:
        results["customers"] = sync_customers(db, tenant_id=tenant_id, user_id=user_id)
    except Exception as e:
        logger.error("sync_domain_failed", domain="customers", error=str(e), error_type=type(e).__name__)
        results["customers"] = {
            "error": "Echec de la synchronisation. Consultez les logs pour plus de details."
        }
        has_errors = True

    # Sync with incremental support (full=True force un re-fetch complet)
    for sync_name, sync_fn in [
        ("invoices", sync_invoices),
        ("payments", sync_payments),
        ("prescriptions", sync_prescriptions),
    ]:
        try:
            results[sync_name] = sync_fn(
                db, tenant_id=tenant_id, user_id=user_id, full=full,
            )
        except Exception as e:
            logger.error("sync_domain_failed", domain=sync_name, error=str(e), error_type=type(e).__name__)
            results[sync_name] = {
                "error": "Echec de la synchronisation. Consultez les logs pour plus de details."
            }
            has_errors = True

    # Sync reference data (calendar, mutuelles, doctors, etc.)
    try:
        from app.services.cosium_reference_sync import sync_all_reference

        results["reference"] = sync_all_reference(
            db, tenant_id=tenant_id, user_id=user_id
        )
    except Exception as e:
        logger.error("sync_reference_failed", error=str(e), error_type=type(e).__name__)
        results["reference"] = {
            "error": "Echec de la synchronisation des donnees de reference."
        }
        has_errors = True

    results["has_errors"] = has_errors
    return results
