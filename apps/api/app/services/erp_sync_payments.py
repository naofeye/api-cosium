"""Sync ERP -> cosium_payments (paiements de factures)."""
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.models.cosium_data import CosiumPayment
from app.services._erp_sync_helpers import (
    audit_sync_completion,
    build_customer_name_lookup,
    parse_iso_date,
    safe_batch_flush,
    safe_final_commit,
    warn_if_no_user,
)
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant
from app.services.erp_matching_service import _match_customer_by_name

logger = get_logger("erp_sync_payments")


@log_operation("sync_payments")
def sync_payments(db: Session, tenant_id: int, user_id: int = 0, *, full: bool = False) -> dict:
    """Sync paiements depuis l'ERP. full=True pour resynchroniser tout (sinon 20 pages incrementales)."""
    warn_if_no_user("sync_payments", "payment", user_id)
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    from app.integrations.cosium.cosium_connector import CosiumConnector

    if not isinstance(connector, CosiumConnector):
        return {"created": 0, "updated": 0, "total": 0, "note": "Connector does not support invoice-payments"}

    existing_count = db.scalar(
        select(func.count()).select_from(CosiumPayment).where(CosiumPayment.tenant_id == tenant_id)
    )
    if full or not existing_count:
        logger.info("sync_payments_full_mode", tenant_id=tenant_id)
        all_payments = connector.get_invoice_payments()
    else:
        logger.info("sync_payments_incremental", tenant_id=tenant_id, existing=existing_count)
        all_payments = connector.get_invoice_payments(max_pages=20)

    customer_name_map, customer_cosium_id_map = build_customer_name_lookup(db, tenant_id)
    existing_map = {
        row.cosium_id: row
        for row in db.scalars(select(CosiumPayment).where(CosiumPayment.tenant_id == tenant_id)).all()
    }

    created = updated = processed = batch_errors = 0
    for pmt in all_payments:
        cosium_id = pmt.get("cosium_id")
        if not cosium_id:
            continue
        cosium_id = int(cosium_id)
        due_date = parse_iso_date(pmt.get("due_date"))

        pmt_customer_cosium_id = pmt.get("customer_cosium_id") or ""
        customer_id = customer_cosium_id_map.get(pmt_customer_cosium_id) if pmt_customer_cosium_id else None
        if not customer_id and pmt.get("issuer_name"):
            customer_id = _match_customer_by_name(pmt["issuer_name"], customer_name_map)

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            row.payment_type_id = pmt.get("payment_type_id")
            row.amount = pmt.get("amount", 0)
            row.original_amount = pmt.get("original_amount")
            row.type = pmt.get("type", "")
            row.due_date = due_date
            row.issuer_name = pmt.get("issuer_name", "")
            row.bank = pmt.get("bank", "")
            row.site_name = pmt.get("site_name", "")
            row.comment = pmt.get("comment")
            row.payment_number = pmt.get("payment_number", "")
            row.invoice_cosium_id = pmt.get("invoice_cosium_id")
            row.customer_cosium_id = pmt_customer_cosium_id or row.customer_cosium_id
            row.customer_id = customer_id or row.customer_id
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            db.add(CosiumPayment(
                tenant_id=tenant_id, cosium_id=cosium_id,
                payment_type_id=pmt.get("payment_type_id"),
                amount=pmt.get("amount", 0),
                original_amount=pmt.get("original_amount"),
                type=pmt.get("type", ""), due_date=due_date,
                issuer_name=pmt.get("issuer_name", ""),
                bank=pmt.get("bank", ""), site_name=pmt.get("site_name", ""),
                comment=pmt.get("comment"),
                payment_number=pmt.get("payment_number", ""),
                invoice_cosium_id=pmt.get("invoice_cosium_id"),
                customer_cosium_id=pmt_customer_cosium_id or None,
                customer_id=customer_id,
            ))
            created += 1
        processed += 1
        batch_errors = safe_batch_flush(db, processed, batch_errors, "sync_payments")

    safe_final_commit(db, tenant_id, "sync_payments")

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(all_payments)}
    audit_sync_completion(db, tenant_id, user_id, "sync_payments", result)
    logger.info("sync_payments_done", tenant_id=tenant_id, **result)
    return result
