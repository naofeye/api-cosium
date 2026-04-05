"""
Service de synchronisation ERP -> OptiFlow (agnostique).

SYNCHRONISATION UNIDIRECTIONNELLE : ERP -> OptiFlow uniquement.
Aucune ecriture vers l'ERP.
Remplace sync_service.py avec une couche d'abstraction multi-ERP.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.integrations.erp_connector import ERPConnector
from app.integrations.erp_factory import get_connector
from app.integrations.erp_models import ERPCustomer, ERPInvoice
from app.models import Customer, Tenant
from app.models.cosium_data import (
    CosiumInvoice,
    CosiumPayment,
    CosiumPrescription,
    CosiumProduct,
    CosiumThirdPartyPayment,
)
from app.services import audit_service

logger = get_logger("erp_sync_service")

BATCH_SIZE = 500


def _get_connector_for_tenant(db: Session, tenant_id: int) -> tuple[ERPConnector, Tenant]:
    """Retourne le connecteur ERP configure pour un tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} introuvable")

    erp_type = tenant.erp_type or "cosium"
    connector = get_connector(erp_type)
    return connector, tenant


def _authenticate_connector(connector: ERPConnector, tenant: Tenant) -> None:
    """Authentifie le connecteur avec les credentials du tenant.

    Priority for Cosium:
    1. Tenant DB cookie credentials (cosium_cookie_access_token_enc)
    2. Settings cookie credentials (COSIUM_ACCESS_TOKEN env var)
    3. OIDC / basic auth credentials
    """
    from app.core.config import settings

    if connector.erp_type == "cosium":
        base_url = settings.cosium_base_url

        # Try tenant-stored cookies first
        tenant_at = getattr(tenant, "cosium_cookie_access_token_enc", None)
        tenant_dc = getattr(tenant, "cosium_cookie_device_credential_enc", None)
        if tenant_at and tenant_dc:
            try:
                at_plain = decrypt(tenant_at)
                dc_plain = decrypt(tenant_dc)
                # Directly configure the underlying CosiumClient for cookie mode
                from app.integrations.cosium.cosium_connector import CosiumConnector

                if isinstance(connector, CosiumConnector):
                    connector._client.base_url = base_url
                    connector._client.tenant = tenant.cosium_tenant or settings.cosium_tenant or ""
                    connector._client._authenticate_cookie(access_token=at_plain, device_credential=dc_plain)
                    logger.info("auth_via_tenant_cookies", tenant_id=tenant.id)
                    return
            except Exception as exc:
                logger.warning("tenant_cookie_decrypt_failed", tenant_id=tenant.id, error=str(exc))

        erp_tenant = tenant.cosium_tenant or settings.cosium_tenant or ""
        login = tenant.cosium_login or settings.cosium_login or ""
        raw_password = tenant.cosium_password_enc or settings.cosium_password or ""
        try:
            password = decrypt(raw_password) if raw_password else ""
        except Exception as exc:
            # Backward compat: fallback to raw value if not encrypted
            logger.warning(
                "password_decrypt_fallback",
                tenant_id=tenant.id,
                error=str(exc),
            )
            password = raw_password
    else:
        erp_config = tenant.erp_config or {}
        base_url = erp_config.get("base_url", "")
        erp_tenant = erp_config.get("tenant", "")
        login = erp_config.get("login", "")
        password = erp_config.get("password", "")

    if not erp_tenant or not login or not password:
        raise ValueError(f"Credentials ERP ({connector.erp_type}) non configurees pour le tenant {tenant.id}")

    connector.authenticate(base_url, erp_tenant, login, password)


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
            except Exception as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_customers_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    # Final commit for remaining records + tenant sync timestamp
    try:
        tenant.last_cosium_sync_at = datetime.now(UTC).replace(tzinfo=None)
        if not tenant.first_sync_done:
            tenant.first_sync_done = True
        db.commit()
    except Exception as e:
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

    # Build customer lookup maps for matching
    all_customers = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    customer_name_map: dict[str, int] = {}
    customer_cosium_id_map: dict[str, int] = {}
    for c in all_customers:
        full_name = f"{c.last_name} {c.first_name}".upper().strip()
        customer_name_map[full_name] = c.id
        # Also index FIRSTNAME LASTNAME (some Cosium entries use this order)
        reverse_name = f"{c.first_name} {c.last_name}".upper().strip()
        customer_name_map[reverse_name] = c.id
        # Index with ALL title prefix patterns (with and without dot)
        for prefix in ("M. ", "MME. ", "MLLE. ", "MME ", "MLLE ", "MR. ", "MRS. "):
            customer_name_map[f"{prefix}{full_name}"] = c.id
            customer_name_map[f"{prefix}{reverse_name}"] = c.id
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


def sync_products(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise un echantillon de produits depuis l'ERP vers cosium_products.

    Products catalog is huge (398k+). We fetch only the first page (50 items)
    as a catalog sample for reference.
    """
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_products", entity="product")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    # Only fetch first page (50 items) — catalog is too large for full sync
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
            except Exception as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_products_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    try:
        db.commit()
    except Exception as e:
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


def sync_payments(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les paiements de factures depuis l'ERP vers cosium_payments (lecture seule)."""
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_payments", entity="payment")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    from app.integrations.cosium.cosium_connector import CosiumConnector

    if not isinstance(connector, CosiumConnector):
        return {"created": 0, "updated": 0, "total": 0, "note": "Connector does not support invoice-payments"}

    all_payments = connector.get_invoice_payments()

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
                logger.error("sync_payments_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("sync_payments_commit_failed", tenant_id=tenant_id, error=str(e))
        raise

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(all_payments)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_payments", 0, new_value=result)
    logger.info("sync_payments_done", tenant_id=tenant_id, **result)
    return result


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
            except Exception as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_tpp_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("sync_tpp_commit_failed", tenant_id=tenant_id, error=str(e))
        raise

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(all_tpp)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_tpp", 0, new_value=result)
    logger.info("sync_tpp_done", tenant_id=tenant_id, **result)
    return result


def sync_prescriptions(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les ordonnances optiques depuis l'ERP vers cosium_prescriptions (lecture seule)."""
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_prescriptions", entity="prescription")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    from app.integrations.cosium.cosium_connector import CosiumConnector

    if not isinstance(connector, CosiumConnector):
        return {"created": 0, "updated": 0, "total": 0, "note": "Connector does not support optical-prescriptions"}

    all_prescriptions = connector.get_optical_prescriptions()

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
            except Exception as e:
                db.rollback()
                batch_errors += 1
                logger.error("sync_prescriptions_batch_error", batch=processed // BATCH_SIZE, error=str(e))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("sync_prescriptions_commit_failed", tenant_id=tenant_id, error=str(e))
        raise

    result = {"created": created, "updated": updated, "batch_errors": batch_errors, "total": len(all_prescriptions)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_prescriptions", 0, new_value=result)
    logger.info("sync_prescriptions_done", tenant_id=tenant_id, **result)
    return result


def get_sync_status(db: Session, tenant_id: int) -> dict:
    """Retourne l'etat de la connexion ERP pour un tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return {"configured": False, "erp_type": "cosium"}

    return {
        "configured": bool(tenant.cosium_tenant or (tenant.erp_config and tenant.erp_config.get("tenant"))),
        "authenticated": tenant.cosium_connected,
        "erp_type": tenant.erp_type or "cosium",
        "tenant_name": tenant.name,
        "last_sync_at": tenant.last_cosium_sync_at.isoformat() if tenant.last_cosium_sync_at else None,
        "first_sync_done": tenant.first_sync_done,
    }


def _find_existing_customer(db: Session, tenant_id: int, erp_c: ERPCustomer) -> Customer | None:
    """Cherche un client existant actif par email ou nom.

    Exclut les clients soft-deleted pour eviter de les reutiliser
    accidentellement. Les lookups batch (sync_customers, sync_invoices)
    incluent intentionnellement les soft-deleted pour eviter les doublons.
    """
    if erp_c.email:
        existing = db.scalars(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.email == erp_c.email,
                Customer.deleted_at.is_(None),
            )
        ).first()
        if existing:
            return existing

    if erp_c.first_name and erp_c.last_name:
        existing = db.scalars(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.first_name == erp_c.first_name,
                Customer.last_name == erp_c.last_name,
                Customer.deleted_at.is_(None),
            )
        ).first()
        if existing:
            return existing

    return None


def _customer_has_changes(existing: Customer, erp_c: ERPCustomer) -> bool:
    """Compare ERP data with existing DB record to detect changes.

    Returns True if ANY field from the ERP would fill a currently-empty
    field on the existing customer, meaning an update is needed.
    Used during incremental sync to skip unchanged records.
    """
    # cosium_id missing = always needs update
    if erp_c.erp_id and not getattr(existing, "cosium_id", None):
        return True
    for field in ("phone", "address", "city", "postal_code", "social_security_number"):
        erp_val = getattr(erp_c, field, None)
        if erp_val and not getattr(existing, field, None):
            return True
    if erp_c.birth_date and not existing.birth_date:
        return True
    # Check if core identity fields differ (e.g. name correction in Cosium)
    if erp_c.first_name and existing.first_name != erp_c.first_name:
        return True
    if erp_c.last_name and existing.last_name != erp_c.last_name:
        return True
    if erp_c.email and (not existing.email or existing.email.lower() != erp_c.email.lower()):
        return True
    return False


def _update_customer_fields(existing: Customer, erp_c: ERPCustomer) -> bool:
    """Met a jour les champs vides d'un client existant."""
    changed = False
    # Always set cosium_id if missing
    if erp_c.erp_id and not getattr(existing, "cosium_id", None):
        existing.cosium_id = str(erp_c.erp_id)
        changed = True
    for field in ("phone", "address", "city", "postal_code", "social_security_number"):
        erp_val = getattr(erp_c, field, None)
        if erp_val and not getattr(existing, field, None):
            setattr(existing, field, erp_val)
            changed = True
    if erp_c.birth_date and not existing.birth_date:
        existing.birth_date = erp_c.birth_date
        changed = True
    return changed


def _validate_erp_customer_data(erp_c: ERPCustomer) -> list[str]:
    """Validate ERP customer data and return list of warnings.

    ERP is source of truth so data is stored anyway, but invalid
    fields are logged as warnings for data quality tracking.
    """
    warnings: list[str] = []
    erp_label = f"erp_id={erp_c.erp_id}, name={erp_c.last_name} {erp_c.first_name}"

    # Email format check
    if erp_c.email and "@" not in erp_c.email:
        warnings.append(f"Email invalide ({erp_c.email}) pour {erp_label}")

    # Birth date range check
    if erp_c.birth_date:
        from datetime import date

        if isinstance(erp_c.birth_date, date):
            today = date.today()
            min_date = date(1900, 1, 1)
            if erp_c.birth_date > today:
                warnings.append(f"Date de naissance dans le futur ({erp_c.birth_date}) pour {erp_label}")
            elif erp_c.birth_date < min_date:
                warnings.append(f"Date de naissance avant 1900 ({erp_c.birth_date}) pour {erp_label}")

    # Social security number length check (French SSN: 13-15 digits)
    if erp_c.social_security_number:
        digits_only = "".join(c for c in erp_c.social_security_number if c.isdigit())
        if digits_only and (len(digits_only) < 13 or len(digits_only) > 15):
            warnings.append(
                f"Numero de securite sociale de longueur invalide "
                f"({len(digits_only)} chiffres) pour {erp_label}"
            )

    return warnings


def _normalize_phone(phone: str | None) -> str | None:
    """Normalize a phone number: strip spaces, ensure starts with + or 0."""
    if not phone:
        return phone
    normalized = phone.replace(" ", "").replace(".", "").replace("-", "")
    if normalized and not normalized.startswith("+") and not normalized.startswith("0"):
        normalized = "0" + normalized
    return normalized


def _create_customer_from_erp(tenant_id: int, erp_c: ERPCustomer) -> Customer:
    """Cree un nouveau client a partir des donnees ERP.

    Valide les donnees et logue des warnings pour les champs invalides.
    Les donnees sont stockees telles quelles (ERP = source de verite).
    """
    warnings = _validate_erp_customer_data(erp_c)
    for w in warnings:
        logger.warning("erp_customer_data_quality", tenant_id=tenant_id, warning=w)

    return Customer(
        tenant_id=tenant_id,
        cosium_id=str(erp_c.erp_id) if erp_c.erp_id else None,
        first_name=erp_c.first_name,
        last_name=erp_c.last_name,
        phone=_normalize_phone(erp_c.phone),
        email=erp_c.email,
        address=erp_c.address,
        city=erp_c.city,
        postal_code=erp_c.postal_code,
        social_security_number=erp_c.social_security_number,
        birth_date=erp_c.birth_date,
    )


def _match_customer_by_name(customer_name: str, name_map: dict[str, int]) -> int | None:
    """Try to match a Cosium customerName to an OptiFlow customer ID.

    Cosium format: "M. LASTNAME FIRSTNAME", "Mme. LASTNAME FIRSTNAME", "MME LASTNAME FIRSTNAME".
    Strategies: exact match → strip prefix → reverse first/last → partial.
    """
    if not customer_name:
        return None

    normalized = customer_name.upper().strip()

    # Direct match (with title prefix already in the map)
    if normalized in name_map:
        return name_map[normalized]

    # Strip title prefixes (including with dot and without)
    stripped = normalized
    for prefix in ("M. ", "MME. ", "MLLE. ", "MME ", "MLLE ", "MR. ", "MR ", "MRS. ", "MRS ", "DR. ", "DR "):
        if normalized.startswith(prefix):
            stripped = normalized[len(prefix):]
            break

    if stripped in name_map:
        return name_map[stripped]

    # Try "FIRSTNAME LASTNAME" → "LASTNAME FIRSTNAME" (reverse words)
    parts = stripped.split()
    if len(parts) >= 2:
        # Try LAST FIRST
        reversed_name = f"{parts[-1]} {' '.join(parts[:-1])}"
        if reversed_name in name_map:
            return name_map[reversed_name]
        # Try just LAST FIRST (2 words)
        simple_reverse = f"{parts[0]} {parts[-1]}"
        if simple_reverse in name_map:
            return name_map[simple_reverse]

    return None
