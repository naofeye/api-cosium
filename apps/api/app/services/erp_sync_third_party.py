"""Sync ERP -> cosium_third_party_payments (tiers payants : secu + AMC)."""
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.models.cosium_data import CosiumThirdPartyPayment
from app.services._erp_sync_helpers import (
    audit_sync_completion,
    safe_batch_flush,
    safe_final_commit,
    warn_if_no_user,
)
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("erp_sync_third_party")


@log_operation("sync_third_party_payments")
def sync_third_party_payments(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Sync tiers payants (TPP) depuis l'ERP."""
    warn_if_no_user("sync_tpp", "third_party_payment", user_id)
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    from app.integrations.cosium.cosium_connector import CosiumConnector

    if not isinstance(connector, CosiumConnector):
        return {"created": 0, "updated": 0, "total": 0, "note": "Connector does not support third-party-payments"}

    all_tpp = connector.get_third_party_payments()
    existing_map = {
        row.cosium_id: row
        for row in db.scalars(
            select(CosiumThirdPartyPayment).where(CosiumThirdPartyPayment.tenant_id == tenant_id)
        ).all()
    }

    created = updated = processed = batch_errors = 0
    for tpp in all_tpp:
        cosium_id = tpp.get("cosium_id")
        if not cosium_id:
            continue
        cosium_id = int(cosium_id)

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            row.social_security_amount = tpp.get("social_security_amount", 0)
            row.social_security_tpp = tpp.get("social_security_tpp", False)
            row.additional_health_care_amount = tpp.get("additional_health_care_amount", 0)
            row.additional_health_care_tpp = tpp.get("additional_health_care_tpp", False)
            row.invoice_cosium_id = tpp.get("invoice_cosium_id")
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            db.add(CosiumThirdPartyPayment(
                tenant_id=tenant_id, cosium_id=cosium_id,
                social_security_amount=tpp.get("social_security_amount", 0),
                social_security_tpp=tpp.get("social_security_tpp", False),
                additional_health_care_amount=tpp.get("additional_health_care_amount", 0),
                additional_health_care_tpp=tpp.get("additional_health_care_tpp", False),
                invoice_cosium_id=tpp.get("invoice_cosium_id"),
            ))
            created += 1
        processed += 1
        batch_errors = safe_batch_flush(db, processed, batch_errors, "sync_tpp")

    safe_final_commit(db, tenant_id, "sync_tpp")

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(all_tpp)}
    audit_sync_completion(db, tenant_id, user_id, "sync_tpp", result)
    logger.info("sync_tpp_done", tenant_id=tenant_id, **result)
    return result
