"""Sync ERP -> cosium_products (echantillon catalogue)."""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.models.cosium_data import CosiumProduct
from app.services._erp_sync_helpers import (
    audit_sync_completion,
    safe_batch_flush,
    safe_final_commit,
    warn_if_no_user,
)
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("erp_sync_products")


@log_operation("sync_products")
def sync_products(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Sync echantillon de produits (catalog 398k+, on prend la 1ere page de 50)."""
    warn_if_no_user("sync_products", "product", user_id)
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    erp_products = connector.get_products(page_size=50)

    existing_map = {
        row.cosium_id: row
        for row in db.scalars(select(CosiumProduct).where(CosiumProduct.tenant_id == tenant_id)).all()
    }

    created = updated = processed = batch_errors = 0
    for prod in erp_products:
        if not prod.erp_id:
            continue
        if prod.erp_id in existing_map:
            row = existing_map[prod.erp_id]
            row.label = prod.label
            row.code = prod.code
            row.ean_code = prod.ean
            row.price = prod.price
            row.family_type = prod.family
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            db.add(CosiumProduct(
                tenant_id=tenant_id,
                cosium_id=prod.erp_id,
                label=prod.label, code=prod.code, ean_code=prod.ean,
                price=prod.price, family_type=prod.family,
            ))
            created += 1
        processed += 1
        batch_errors = safe_batch_flush(db, processed, batch_errors, "sync_products")

    safe_final_commit(db, tenant_id, "sync_products")

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(erp_products)}
    audit_sync_completion(db, tenant_id, user_id, "sync_products", result)
    logger.info("sync_products_done", tenant_id=tenant_id, erp=connector.erp_type, **result)
    return result
