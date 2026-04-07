"""
Service de synchronisation ERP -> OptiFlow (orchestrateur).

SYNCHRONISATION UNIDIRECTIONNELLE : ERP -> OptiFlow uniquement.
Aucune ecriture vers l'ERP.

Ce module orchestre la synchronisation des clients et l'enrichissement.
Les helpers partages sont dans :
- erp_auth_service.py    : _get_connector_for_tenant, _authenticate_connector
- erp_matching_service.py: _normalize_name, _match_customer_by_name, etc.

Les fonctions de synchronisation factures, paiements, produits et ordonnances
sont dans erp_sync_invoices.py et erp_sync_extras.py.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger, log_operation
from app.models import Customer, Tenant
from app.repositories import onboarding_repo
from app.services import audit_service
from app.integrations.erp_factory import get_connector  # noqa: F401 — re-export for patch targets
from app.services.erp_auth_service import (
    _authenticate_connector,
    _get_connector_for_tenant,
)
from app.services.erp_matching_service import (
    _create_customer_from_erp,
    _customer_has_changes,
    _match_customer_by_name,
    _normalize_name,
    _normalize_phone,
    _update_customer_fields,
    _validate_erp_customer_data,
)

logger = get_logger("erp_sync_service")

BATCH_SIZE = 500


@log_operation("sync_customers")
def sync_customers(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les clients depuis l'ERP vers OptiFlow (lecture seule).

    Supports incremental (delta) sync: if the tenant already has a
    last_cosium_sync_at timestamp, unchanged customers are detected
    via field comparison and skipped, making subsequent syncs faster.
    """
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_customers", entity="customer")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    is_incremental = tenant.last_cosium_sync_at is not None
    sync_mode = "incremental" if is_incremental else "full"
    logger.info("sync_customers_start", tenant_id=tenant_id, mode=sync_mode)

    erp_customers = connector.get_customers()
    created = 0
    updated = 0
    skipped = 0
    unchanged = 0
    warnings: list[str] = []

    # Batch-load all existing customers for the tenant to avoid N+1 queries
    existing_by_email: dict[str, Customer] = {}
    existing_by_name: dict[tuple[str, str], Customer] = {}
    existing_by_erp_id: dict[str, Customer] = {}
    all_existing = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    for c in all_existing:
        if c.email:
            existing_by_email[c.email.lower()] = c
        if c.first_name and c.last_name:
            existing_by_name[(c.first_name, c.last_name)] = c
        erp_id = getattr(c, "cosium_id", None) or getattr(c, "erp_id", None)
        if erp_id:
            existing_by_erp_id[str(erp_id)] = c

    processed = 0
    batch_errors = 0

    for erp_c in erp_customers:
        if not erp_c.last_name:
            skipped += 1
            msg = f"Client sans nom de famille ignore (email={erp_c.email}, prenom={erp_c.first_name})"
            warnings.append(msg)
            logger.warning("sync_customer_skipped", reason="empty_last_name", email=erp_c.email)
            continue

        # In-memory lookup: erp_id first, then email, then name
        existing: Customer | None = None
        if erp_c.erp_id:
            existing = existing_by_erp_id.get(str(erp_c.erp_id))
        if not existing and erp_c.email:
            existing = existing_by_email.get(erp_c.email.lower())
        if not existing and erp_c.first_name and erp_c.last_name:
            existing = existing_by_name.get((erp_c.first_name, erp_c.last_name))

        if existing:
            # For incremental syncs, skip customers with no field changes
            if is_incremental and not _customer_has_changes(existing, erp_c):
                unchanged += 1
                continue
            changed = _update_customer_fields(existing, erp_c)
            if changed:
                existing.updated_at = datetime.now(UTC).replace(tzinfo=None)
                updated += 1
            else:
                unchanged += 1
        else:
            customer = _create_customer_from_erp(tenant_id, erp_c)
            db.add(customer)
            created += 1
            # Keep lookup maps current for duplicate detection within the batch
            if erp_c.email:
                existing_by_email[erp_c.email.lower()] = customer
            if erp_c.first_name and erp_c.last_name:
                existing_by_name[(erp_c.first_name, erp_c.last_name)] = customer
            if erp_c.erp_id:
                existing_by_erp_id[str(erp_c.erp_id)] = customer

        processed += 1
        if processed % BATCH_SIZE == 0:
            try:
                db.flush()
            except SQLAlchemyError as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_customers_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    # Final commit for remaining records + tenant sync timestamp
    try:
        tenant.last_cosium_sync_at = datetime.now(UTC).replace(tzinfo=None)
        if not tenant.first_sync_done:
            tenant.first_sync_done = True
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("sync_customers_commit_failed", tenant_id=tenant_id, error=str(e))
        raise

    result = {
        "mode": sync_mode,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
        "batch_errors": batch_errors,
        "warnings": warnings,
        "total": len(erp_customers),
    }
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_customers", 0, new_value=result)
    logger.info("sync_customers_done", tenant_id=tenant_id, erp=connector.erp_type, **result)
    return result


def get_sync_status(db: Session, tenant_id: int) -> dict:
    """Retourne l'etat de la connexion ERP pour un tenant."""
    tenant = onboarding_repo.get_tenant_by_id(db, tenant_id)
    if not tenant:
        return {"configured": False, "erp_type": "cosium"}

    cosium_tenant = tenant.cosium_tenant or (tenant.erp_config.get("tenant") if tenant.erp_config else "")
    return {
        "configured": bool(cosium_tenant),
        "authenticated": tenant.cosium_connected,
        "erp_type": tenant.erp_type or "cosium",
        "tenant": cosium_tenant or None,
        "tenant_name": tenant.name,
        "base_url": settings.cosium_base_url,
        "last_sync_at": tenant.last_cosium_sync_at.isoformat() if tenant.last_cosium_sync_at else None,
        "first_sync_done": tenant.first_sync_done,
    }


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
            except SQLAlchemyError as e:
                logger.error("enrich_batch_flush_error", error=str(e))

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


# ---------------------------------------------------------------------------
# Re-exports for backward compatibility.
# All symbols that were previously defined here are still importable from
# this module. Callers using `from app.services.erp_sync_service import X`
# or `@patch("app.services.erp_sync_service.X")` continue to work.
# ---------------------------------------------------------------------------
from app.services.erp_sync_extras import (  # noqa: E402, F401
    sync_payments,
    sync_prescriptions,
    sync_products,
    sync_third_party_payments,
)
from app.services.erp_sync_invoices import sync_invoices  # noqa: E402, F401

# Re-export auth and matching helpers (already imported above, listed here
# explicitly so that `from erp_sync_service import _normalize_phone` etc. works)
__all__ = [
    # Orchestration
    "sync_customers",
    "get_sync_status",
    "enrich_top_clients_metadata",
    "BATCH_SIZE",
    # Auth (from erp_auth_service)
    "_get_connector_for_tenant",
    "_authenticate_connector",
    # Matching (from erp_matching_service)
    "_normalize_name",
    "_normalize_phone",
    "_match_customer_by_name",
    "_validate_erp_customer_data",
    "_customer_has_changes",
    "_update_customer_fields",
    "_create_customer_from_erp",
    # Re-exported sync functions
    "sync_invoices",
    "sync_payments",
    "sync_prescriptions",
    "sync_products",
    "sync_third_party_payments",
]
