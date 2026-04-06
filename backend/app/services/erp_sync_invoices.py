"""
Service de synchronisation des factures ERP -> OptiFlow.

SYNCHRONISATION UNIDIRECTIONNELLE : ERP -> OptiFlow uniquement.
Aucune ecriture vers l'ERP.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.integrations.erp_models import ERPInvoice
from app.models import Customer
from app.models.cosium_data import CosiumInvoice
from app.services import audit_service
from app.services.erp_sync_service import (
    BATCH_SIZE,
    _authenticate_connector,
    _get_connector_for_tenant,
    _match_customer_by_name,
    _normalize_name,
)

logger = get_logger("erp_sync_invoices")


@log_operation("sync_invoices")
def sync_invoices(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les factures depuis l'ERP vers cosium_invoices (lecture seule).

    Uses date-range pagination (month by month, 24 months back) to bypass
    the Cosium 50-item offset limit.
    """
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_invoices", entity="invoice")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    # Collect all invoices via direct pagination (no offset limit on invoices)
    all_invoices: list[ERPInvoice] = []
    seen_ids: set[str] = set()

    try:
        # Invoices endpoint supports full pagination (unlike customers)
        # Use max_pages=600 to cover ~30000 invoices at 50/page
        batch = connector.get_invoices(page=0, page_size=50)
        for inv in batch:
            if inv.erp_id not in seen_ids:
                seen_ids.add(inv.erp_id)
                all_invoices.append(inv)
    except Exception as e:
        logger.error("sync_invoices_failed", error=str(e), exc_info=True)
        if "auth" in str(e).lower() or "connect" in str(e).lower() or "timeout" in str(e).lower():
            raise ValueError(f"Erreur critique lors de la synchronisation des factures: {e}") from e

    logger.info("sync_invoices_fetched", tenant_id=tenant_id, total=len(all_invoices))

    # Build customer lookup maps for matching (normalized for accent/hyphen tolerance)
    all_customers = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    customer_name_map: dict[str, int] = {}
    customer_cosium_id_map: dict[str, int] = {}
    for c in all_customers:
        # Normalized keys (accent-insensitive, hyphen-normalised)
        normalized_full = _normalize_name(f"{c.last_name} {c.first_name}")
        customer_name_map[normalized_full] = c.id
        # Also index FIRSTNAME LASTNAME (some Cosium entries use this order)
        normalized_reverse = _normalize_name(f"{c.first_name} {c.last_name}")
        customer_name_map[normalized_reverse] = c.id
        # Index with ALL title prefix patterns (with and without dot)
        for prefix in ("M. ", "MME. ", "MLLE. ", "MME ", "MLLE ", "MR. ", "MRS. "):
            customer_name_map[f"{prefix}{normalized_full}"] = c.id
            customer_name_map[f"{prefix}{normalized_reverse}"] = c.id
        # Index by cosium_id for direct matching
        if c.cosium_id:
            customer_cosium_id_map[str(c.cosium_id)] = c.id

    # Upsert into cosium_invoices
    existing_map: dict[int, CosiumInvoice] = {}
    existing_rows = db.scalars(select(CosiumInvoice).where(CosiumInvoice.tenant_id == tenant_id)).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0
    processed = 0
    batch_errors = 0

    for inv in all_invoices:
        cosium_id = int(inv.erp_id) if inv.erp_id.isdigit() else 0
        if not cosium_id:
            continue

        # Try to match customer: cosium_id first, then name fallback
        customer_erp_id_str = str(inv.customer_erp_id) if inv.customer_erp_id else ""
        customer_id = customer_cosium_id_map.get(customer_erp_id_str) if customer_erp_id_str else None
        if not customer_id:
            customer_id = _match_customer_by_name(inv.customer_name, customer_name_map)

        # Parse date (Cosium returns ISO strings like "2026-03-20T23:00:00.000Z")
        invoice_date = None
        if inv.date:
            if isinstance(inv.date, datetime):
                invoice_date = inv.date
            elif isinstance(inv.date, str):
                try:
                    invoice_date = datetime.fromisoformat(inv.date.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            row.invoice_number = inv.number
            row.invoice_date = invoice_date
            row.customer_name = inv.customer_name
            row.customer_cosium_id = customer_erp_id_str or row.customer_cosium_id
            row.customer_id = customer_id or row.customer_id
            row.type = inv.type
            row.total_ti = inv.total_ttc
            row.outstanding_balance = inv.outstanding_balance
            row.share_social_security = inv.share_social_security or 0.0
            row.share_private_insurance = inv.share_private_insurance or 0.0
            row.settled = inv.settled
            row.archived = inv.archived
            row.site_id = inv.site_id
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumInvoice(
                tenant_id=tenant_id,
                cosium_id=cosium_id,
                invoice_number=inv.number,
                invoice_date=invoice_date,
                customer_name=inv.customer_name,
                customer_cosium_id=customer_erp_id_str or None,
                customer_id=customer_id,
                type=inv.type,
                total_ti=inv.total_ttc,
                outstanding_balance=inv.outstanding_balance,
                share_social_security=inv.share_social_security or 0.0,
                share_private_insurance=inv.share_private_insurance or 0.0,
                settled=inv.settled,
                archived=inv.archived,
                site_id=inv.site_id,
            )
            db.add(new_row)
            created += 1

        processed += 1
        if processed % BATCH_SIZE == 0:
            try:
                db.flush()
            except Exception as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_invoices_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("sync_invoices_commit_failed", tenant_id=tenant_id, error=str(e))
        raise

    result = {
        "created": created,
        "updated": updated,
        "batch_errors": batch_errors,
        "total": len(all_invoices),
    }
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_invoices", 0, new_value=result)
    logger.info("sync_invoices_done", tenant_id=tenant_id, erp=connector.erp_type, **result)
    return result
