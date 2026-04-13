"""Sync ERP -> cosium_prescriptions (ordonnances optiques)."""
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.models.cosium_data import CosiumPrescription
from app.services._erp_sync_helpers import (
    audit_sync_completion,
    build_cosium_id_to_customer,
    parse_iso_date,
    safe_batch_flush,
    safe_final_commit,
    warn_if_no_user,
)
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("erp_sync_prescriptions")


@log_operation("sync_prescriptions")
def sync_prescriptions(db: Session, tenant_id: int, user_id: int = 0, *, full: bool = False) -> dict:
    """Sync ordonnances depuis l'ERP. full=True pour resynchroniser tout."""
    warn_if_no_user("sync_prescriptions", "prescription", user_id)
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    from app.integrations.cosium.cosium_connector import CosiumConnector

    if not isinstance(connector, CosiumConnector):
        return {"created": 0, "updated": 0, "total": 0, "note": "Connector does not support optical-prescriptions"}

    existing_count = db.scalar(
        select(func.count()).select_from(CosiumPrescription).where(CosiumPrescription.tenant_id == tenant_id)
    )
    if full or not existing_count:
        logger.info("sync_prescriptions_full_mode", tenant_id=tenant_id)
        all_prescriptions = connector.get_optical_prescriptions()
    else:
        logger.info("sync_prescriptions_incremental", tenant_id=tenant_id, existing=existing_count)
        all_prescriptions = connector.get_optical_prescriptions(max_pages=20)

    cosium_to_customer = build_cosium_id_to_customer(db, tenant_id)
    existing_map = {
        row.cosium_id: row
        for row in db.scalars(
            select(CosiumPrescription).where(CosiumPrescription.tenant_id == tenant_id)
        ).all()
    }

    created = updated = processed = batch_errors = 0
    for presc in all_prescriptions:
        cosium_id = presc.get("cosium_id")
        if not cosium_id:
            continue
        cosium_id = int(cosium_id)

        customer_cosium_id = presc.get("customer_cosium_id")
        customer_id = cosium_to_customer.get(customer_cosium_id) if customer_cosium_id else None
        file_date = parse_iso_date(presc.get("file_date"))

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            row.prescription_date = presc.get("prescription_date")
            row.file_date = file_date
            row.customer_cosium_id = customer_cosium_id
            row.customer_id = customer_id or row.customer_id
            row.sphere_right = presc.get("sphere_right")
            row.cylinder_right = presc.get("cylinder_right")
            row.axis_right = presc.get("axis_right")
            row.addition_right = presc.get("addition_right")
            row.sphere_left = presc.get("sphere_left")
            row.cylinder_left = presc.get("cylinder_left")
            row.axis_left = presc.get("axis_left")
            row.addition_left = presc.get("addition_left")
            row.spectacles_json = presc.get("spectacles_json")
            row.prescriber_name = presc.get("prescriber_name")
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            db.add(CosiumPrescription(
                tenant_id=tenant_id, cosium_id=cosium_id,
                prescription_date=presc.get("prescription_date"),
                file_date=file_date,
                customer_cosium_id=customer_cosium_id,
                customer_id=customer_id,
                sphere_right=presc.get("sphere_right"),
                cylinder_right=presc.get("cylinder_right"),
                axis_right=presc.get("axis_right"),
                addition_right=presc.get("addition_right"),
                sphere_left=presc.get("sphere_left"),
                cylinder_left=presc.get("cylinder_left"),
                axis_left=presc.get("axis_left"),
                addition_left=presc.get("addition_left"),
                spectacles_json=presc.get("spectacles_json"),
                prescriber_name=presc.get("prescriber_name"),
            ))
            created += 1
        processed += 1
        batch_errors = safe_batch_flush(db, processed, batch_errors, "sync_prescriptions")

    safe_final_commit(db, tenant_id, "sync_prescriptions")

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(all_prescriptions)}
    audit_sync_completion(db, tenant_id, user_id, "sync_prescriptions", result)
    logger.info("sync_prescriptions_done", tenant_id=tenant_id, **result)
    return result
