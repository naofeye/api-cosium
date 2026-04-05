"""
Service de synchronisation ERP -> OptiFlow (agnostique).

SYNCHRONISATION UNIDIRECTIONNELLE : ERP -> OptiFlow uniquement.
Aucune ecriture vers l'ERP.
Remplace sync_service.py avec une couche d'abstraction multi-ERP.
"""

from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.integrations.erp_connector import ERPConnector
from app.integrations.erp_factory import get_connector
from app.integrations.erp_models import ERPCustomer, ERPInvoice
from app.models import Customer, Tenant
from app.models.cosium_data import CosiumInvoice, CosiumProduct
from app.services import audit_service

logger = get_logger("erp_sync_service")


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
        except Exception:
            # Backward compat: fallback to raw value if not encrypted
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

    # Update tenant sync timestamp
    tenant.last_cosium_sync_at = datetime.now(UTC).replace(tzinfo=None)
    if not tenant.first_sync_done:
        tenant.first_sync_done = True

    db.commit()

    result = {
        "mode": sync_mode,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
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

    # Collect all invoices via month-by-month date ranges (24 months)
    all_invoices: list[ERPInvoice] = []
    seen_ids: set[str] = set()
    now = datetime.now(UTC)

    for months_back in range(24):
        start = (now - relativedelta(months=months_back + 1)).replace(day=1)
        end = (now - relativedelta(months=months_back)).replace(day=1)
        date_from = start.strftime("%Y-%m-%dT00:00:00.000Z")
        date_to = end.strftime("%Y-%m-%dT00:00:00.000Z")

        try:
            if hasattr(connector, "get_invoices_by_date_range"):
                batch = connector.get_invoices_by_date_range(date_from, date_to)
            else:
                # Fallback for non-Cosium connectors
                batch = connector.get_invoices()
                all_invoices.extend(batch)
                break

            for inv in batch:
                if inv.erp_id not in seen_ids:
                    seen_ids.add(inv.erp_id)
                    all_invoices.append(inv)
        except Exception as e:
            logger.warning(
                "sync_invoices_month_failed",
                date_from=date_from,
                date_to=date_to,
                error=str(e),
            )

    logger.info("sync_invoices_fetched", tenant_id=tenant_id, total=len(all_invoices))

    # Build customer name lookup for fuzzy matching
    all_customers = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    customer_name_map: dict[str, int] = {}
    for c in all_customers:
        full_name = f"{c.last_name} {c.first_name}".upper().strip()
        customer_name_map[full_name] = c.id
        # Also index with title prefix patterns like "M. LASTNAME FIRSTNAME"
        for prefix in ("M. ", "MME ", "MLLE "):
            customer_name_map[f"{prefix}{full_name}"] = c.id

    # Upsert into cosium_invoices
    existing_map: dict[int, CosiumInvoice] = {}
    existing_rows = db.scalars(select(CosiumInvoice).where(CosiumInvoice.tenant_id == tenant_id)).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0

    for inv in all_invoices:
        cosium_id = int(inv.erp_id) if inv.erp_id.isdigit() else 0
        if not cosium_id:
            continue

        # Try to match customer
        customer_id = _match_customer_by_name(inv.customer_name, customer_name_map)

        # Parse date
        invoice_date = None
        if inv.date:
            invoice_date = inv.date if isinstance(inv.date, datetime) else None

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            row.invoice_number = inv.number
            row.invoice_date = invoice_date
            row.customer_name = inv.customer_name
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

    db.commit()

    result = {
        "created": created,
        "updated": updated,
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

    db.commit()

    result = {
        "created": created,
        "updated": updated,
        "total": len(erp_products),
    }
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_products", 0, new_value=result)
    logger.info("sync_products_done", tenant_id=tenant_id, erp=connector.erp_type, **result)
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
    """Cherche un client existant par email ou nom."""
    if erp_c.email:
        existing = db.scalars(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.email == erp_c.email,
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
    for field in ("phone", "address", "city", "postal_code", "social_security_number"):
        erp_val = getattr(erp_c, field, None)
        if erp_val and not getattr(existing, field, None):
            setattr(existing, field, erp_val)
            changed = True
    if erp_c.birth_date and not existing.birth_date:
        existing.birth_date = erp_c.birth_date
        changed = True
    return changed


def _create_customer_from_erp(tenant_id: int, erp_c: ERPCustomer) -> Customer:
    """Cree un nouveau client a partir des donnees ERP."""
    return Customer(
        tenant_id=tenant_id,
        first_name=erp_c.first_name,
        last_name=erp_c.last_name,
        phone=erp_c.phone,
        email=erp_c.email,
        address=erp_c.address,
        city=erp_c.city,
        postal_code=erp_c.postal_code,
        social_security_number=erp_c.social_security_number,
        birth_date=erp_c.birth_date,
    )


def _match_customer_by_name(customer_name: str, name_map: dict[str, int]) -> int | None:
    """Try to match a Cosium customerName to an OptiFlow customer ID.

    Cosium format is typically "M. LASTNAME FIRSTNAME" or "MME LASTNAME FIRSTNAME".
    We do an exact upper-case lookup first, then try stripping common title prefixes.
    """
    if not customer_name:
        return None

    normalized = customer_name.upper().strip()

    # Direct match (with title prefix already in the map)
    if normalized in name_map:
        return name_map[normalized]

    # Strip title prefixes and try again
    for prefix in ("M. ", "MME ", "MLLE ", "MR ", "MRS "):
        if normalized.startswith(prefix):
            stripped = normalized[len(prefix) :]
            if stripped in name_map:
                return name_map[stripped]

    return None
