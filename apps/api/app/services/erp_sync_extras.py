"""
Service de synchronisation ERP -> OptiFlow : paiements, tiers payants, ordonnances, produits.

SYNCHRONISATION UNIDIRECTIONNELLE : ERP -> OptiFlow uniquement.
Aucune ecriture vers l'ERP.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.models import Customer
from app.models.cosium_data import (
    CosiumPayment,
    CosiumPrescription,
    CosiumProduct,
    CosiumThirdPartyPayment,
)
from app.services import audit_service
from app.services.erp_auth_service import (
    _authenticate_connector,
    _get_connector_for_tenant,
)
from app.services.erp_matching_service import (
    _match_customer_by_name,
    _normalize_name,
)

BATCH_SIZE = 500

logger = get_logger("erp_sync_extras")


@log_operation("sync_products")
def sync_products(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise un echantillon de produits depuis l'ERP vers cosium_products.

    Products catalog is huge (398k+). We fetch only the first page (50 items)
    as a catalog sample for reference.
    """
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_products", entity="product")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    # Only fetch first page (50 items) -- catalog is too large for full sync
    erp_products = connector.get_products(page_size=50)

    # Upsert into cosium_products
    existing_map: dict[str, CosiumProduct] = {}
    existing_rows = db.scalars(select(CosiumProduct).where(CosiumProduct.tenant_id == tenant_id)).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0
    processed = 0
    batch_errors = 0

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
            new_row = CosiumProduct(
                tenant_id=tenant_id,
                cosium_id=prod.erp_id,
                label=prod.label,
                code=prod.code,
                ean_code=prod.ean,
                price=prod.price,
                family_type=prod.family,
            )
            db.add(new_row)
            created += 1

        processed += 1
        if processed % BATCH_SIZE == 0:
            try:
                db.flush()
            except SQLAlchemyError as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_products_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("sync_products_commit_failed", tenant_id=tenant_id, error=str(e))
        raise

    result = {
        "created": created,
        "updated": updated,
        "batch_errors": batch_errors,
        "total": len(erp_products),
    }
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_products", 0, new_value=result)
    logger.info("sync_products_done", tenant_id=tenant_id, erp=connector.erp_type, **result)
    return result


@log_operation("sync_payments")
def sync_payments(db: Session, tenant_id: int, user_id: int = 0, *, full: bool = False) -> dict:
    """Synchronise les paiements de factures depuis l'ERP vers cosium_payments (lecture seule).

    Par defaut (full=False), sync incrementale : limite a 20 pages (~1000 paiements recents).
    Avec full=True, re-fetch toutes les pages (600 max).
    """
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_payments", entity="payment")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    from app.integrations.cosium.cosium_connector import CosiumConnector

    if not isinstance(connector, CosiumConnector):
        return {"created": 0, "updated": 0, "total": 0, "note": "Connector does not support invoice-payments"}

    # Verifier si on a deja des paiements pour determiner le mode
    existing_count = db.scalar(
        select(func.count()).select_from(CosiumPayment).where(CosiumPayment.tenant_id == tenant_id)
    )
    if full or not existing_count:
        logger.info("sync_payments_full_mode", tenant_id=tenant_id)
        all_payments = connector.get_invoice_payments()
    else:
        logger.info("sync_payments_incremental", tenant_id=tenant_id, existing=existing_count)
        all_payments = connector.get_invoice_payments(max_pages=20)

    # Build customer lookup maps for matching
    all_customers = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    customer_name_map: dict[str, int] = {}
    customer_cosium_id_map: dict[str, int] = {}
    for c in all_customers:
        normalized_full = _normalize_name(f"{c.last_name} {c.first_name}")
        customer_name_map[normalized_full] = c.id
        normalized_reverse = _normalize_name(f"{c.first_name} {c.last_name}")
        customer_name_map[normalized_reverse] = c.id
        if c.cosium_id:
            customer_cosium_id_map[str(c.cosium_id)] = c.id

    # Build existing map for upsert
    existing_map: dict[int, CosiumPayment] = {}
    existing_rows = db.scalars(select(CosiumPayment).where(CosiumPayment.tenant_id == tenant_id)).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0
    processed = 0
    batch_errors = 0

    for pmt in all_payments:
        cosium_id = pmt.get("cosium_id")
        if not cosium_id:
            continue
        cosium_id = int(cosium_id)

        # Parse due_date
        due_date = None
        if pmt.get("due_date"):
            try:
                due_date = datetime.fromisoformat(str(pmt["due_date"]).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Resolve customer_id from cosium_id or issuer_name
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
            new_row = CosiumPayment(
                tenant_id=tenant_id,
                cosium_id=cosium_id,
                payment_type_id=pmt.get("payment_type_id"),
                amount=pmt.get("amount", 0),
                original_amount=pmt.get("original_amount"),
                type=pmt.get("type", ""),
                due_date=due_date,
                issuer_name=pmt.get("issuer_name", ""),
                bank=pmt.get("bank", ""),
                site_name=pmt.get("site_name", ""),
                comment=pmt.get("comment"),
                payment_number=pmt.get("payment_number", ""),
                invoice_cosium_id=pmt.get("invoice_cosium_id"),
                customer_cosium_id=pmt_customer_cosium_id or None,
                customer_id=customer_id,
            )
            db.add(new_row)
            created += 1

        processed += 1
        if processed % BATCH_SIZE == 0:
            try:
                db.flush()
            except SQLAlchemyError as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_payments_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("sync_payments_commit_failed", tenant_id=tenant_id, error=str(e))
        raise

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(all_payments)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_payments", 0, new_value=result)
    logger.info("sync_payments_done", tenant_id=tenant_id, **result)
    return result


@log_operation("sync_third_party_payments")
def sync_third_party_payments(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les tiers payants depuis l'ERP vers cosium_third_party_payments (lecture seule)."""
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_tpp", entity="third_party_payment")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    from app.integrations.cosium.cosium_connector import CosiumConnector

    if not isinstance(connector, CosiumConnector):
        return {"created": 0, "updated": 0, "total": 0, "note": "Connector does not support third-party-payments"}

    all_tpp = connector.get_third_party_payments()

    existing_map: dict[int, CosiumThirdPartyPayment] = {}
    existing_rows = db.scalars(
        select(CosiumThirdPartyPayment).where(CosiumThirdPartyPayment.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0
    processed = 0
    batch_errors = 0

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
            new_row = CosiumThirdPartyPayment(
                tenant_id=tenant_id,
                cosium_id=cosium_id,
                social_security_amount=tpp.get("social_security_amount", 0),
                social_security_tpp=tpp.get("social_security_tpp", False),
                additional_health_care_amount=tpp.get("additional_health_care_amount", 0),
                additional_health_care_tpp=tpp.get("additional_health_care_tpp", False),
                invoice_cosium_id=tpp.get("invoice_cosium_id"),
            )
            db.add(new_row)
            created += 1

        processed += 1
        if processed % BATCH_SIZE == 0:
            try:
                db.flush()
            except SQLAlchemyError as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_tpp_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("sync_tpp_commit_failed", tenant_id=tenant_id, error=str(e))
        raise

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(all_tpp)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_tpp", 0, new_value=result)
    logger.info("sync_tpp_done", tenant_id=tenant_id, **result)
    return result


@log_operation("sync_prescriptions")
def sync_prescriptions(db: Session, tenant_id: int, user_id: int = 0, *, full: bool = False) -> dict:
    """Synchronise les ordonnances optiques depuis l'ERP vers cosium_prescriptions (lecture seule).

    Par defaut (full=False), sync incrementale : limite a 20 pages (~1000 prescriptions recentes).
    Avec full=True, re-fetch toutes les pages (600 max).
    """
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_prescriptions", entity="prescription")
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

    # Build customer cosium_id -> OptiFlow customer.id map
    all_customers = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    cosium_to_customer: dict[int, int] = {}
    for c in all_customers:
        erp_id = getattr(c, "cosium_id", None) or getattr(c, "erp_id", None)
        if erp_id:
            try:
                cosium_to_customer[int(erp_id)] = c.id
            except (ValueError, TypeError):
                pass

    existing_map: dict[int, CosiumPrescription] = {}
    existing_rows = db.scalars(
        select(CosiumPrescription).where(CosiumPrescription.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0
    processed = 0
    batch_errors = 0

    for presc in all_prescriptions:
        cosium_id = presc.get("cosium_id")
        if not cosium_id:
            continue
        cosium_id = int(cosium_id)

        # Resolve customer_id
        customer_cosium_id = presc.get("customer_cosium_id")
        customer_id = cosium_to_customer.get(customer_cosium_id) if customer_cosium_id else None

        # Parse file_date
        file_date = None
        if presc.get("file_date"):
            try:
                file_date = datetime.fromisoformat(str(presc["file_date"]).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

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
            new_row = CosiumPrescription(
                tenant_id=tenant_id,
                cosium_id=cosium_id,
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
            )
            db.add(new_row)
            created += 1

        processed += 1
        if processed % BATCH_SIZE == 0:
            try:
                db.flush()
            except SQLAlchemyError as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_prescriptions_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("sync_prescriptions_commit_failed", tenant_id=tenant_id, error=str(e))
        raise

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(all_prescriptions)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_prescriptions", 0, new_value=result)
    logger.info("sync_prescriptions_done", tenant_id=tenant_id, **result)
    return result
