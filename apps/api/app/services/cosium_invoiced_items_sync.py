"""Sync `/invoiced-items` Cosium → table locale `cosium_invoiced_items`.

Lecture seule. Upsert par `cosium_id`. Appele periodiquement via Celery beat.
"""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.models.cosium_data import CosiumInvoicedItem
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("cosium_invoiced_items_sync")

BATCH_COMMIT = 200


@log_operation("sync_invoiced_items")
def sync_invoiced_items(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les lignes de facture depuis Cosium. Upsert par cosium_id."""
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    raw_items = connector.list_invoiced_items()

    existing_map: dict[int, CosiumInvoicedItem] = {
        row.cosium_id: row
        for row in db.scalars(
            select(CosiumInvoicedItem).where(CosiumInvoicedItem.tenant_id == tenant_id)
        ).all()
    }

    created = 0
    updated = 0
    skipped = 0
    batch_since_commit = 0
    now = datetime.now(UTC).replace(tzinfo=None)

    for item in raw_items:
        cid = int(item.get("cosium_id") or 0)
        if not cid:
            skipped += 1
            continue
        if cid in existing_map:
            row = existing_map[cid]
            row.invoice_cosium_id = int(item.get("invoice_cosium_id") or 0)
            row.product_cosium_id = item.get("product_cosium_id")
            row.product_label = item.get("product_label") or ""
            row.product_family = item.get("product_family") or ""
            row.quantity = int(item.get("quantity") or 1)
            row.unit_price_ti = float(item.get("unit_price_ti") or 0)
            row.total_ti = float(item.get("total_ti") or 0)
            row.synced_at = now
            updated += 1
        else:
            db.add(
                CosiumInvoicedItem(
                    tenant_id=tenant_id,
                    cosium_id=cid,
                    invoice_cosium_id=int(item.get("invoice_cosium_id") or 0),
                    product_cosium_id=item.get("product_cosium_id"),
                    product_label=item.get("product_label") or "",
                    product_family=item.get("product_family") or "",
                    quantity=int(item.get("quantity") or 1),
                    unit_price_ti=float(item.get("unit_price_ti") or 0),
                    total_ti=float(item.get("total_ti") or 0),
                    synced_at=now,
                )
            )
            created += 1
        batch_since_commit += 1
        if batch_since_commit >= BATCH_COMMIT:
            db.commit()
            batch_since_commit = 0

    db.commit()

    logger.info(
        "sync_invoiced_items_done",
        tenant_id=tenant_id,
        created=created,
        updated=updated,
        skipped=skipped,
        total=len(raw_items),
    )
    return {
        "total": len(raw_items),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }
