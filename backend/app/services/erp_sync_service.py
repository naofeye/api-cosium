"""
Service de synchronisation ERP -> OptiFlow (agnostique).

SYNCHRONISATION UNIDIRECTIONNELLE : ERP -> OptiFlow uniquement.
Aucune ecriture vers l'ERP.
Remplace sync_service.py avec une couche d'abstraction multi-ERP.

Ce module contient les fonctions de synchronisation client et les helpers
partages (_get_connector_for_tenant, _authenticate_connector, etc.).
Les fonctions de synchronisation factures, paiements, produits et ordonnances
sont dans erp_sync_invoices.py et erp_sync_extras.py.
"""

import unicodedata
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.integrations.erp_connector import ERPConnector
from app.integrations.erp_factory import get_connector
from app.integrations.erp_models import ERPCustomer
from app.models import Customer, Tenant
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
    enriched_fields = (
        "phone", "address", "city", "postal_code", "social_security_number",
        "customer_number", "street_number", "street_name",
        "mobile_phone_country",
    )
    for field in enriched_fields:
        erp_val = getattr(erp_c, field, None)
        if erp_val and not getattr(existing, field, None):
            return True
    if erp_c.site_id is not None and not getattr(existing, "site_id", None):
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
    enriched_fields = (
        "phone", "address", "city", "postal_code", "social_security_number",
        "customer_number", "street_number", "street_name",
        "mobile_phone_country",
    )
    for field in enriched_fields:
        erp_val = getattr(erp_c, field, None)
        if erp_val and not getattr(existing, field, None):
            setattr(existing, field, erp_val)
            changed = True
    if erp_c.site_id is not None and not getattr(existing, "site_id", None):
        existing.site_id = erp_c.site_id
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

    # Social security number length check (French JSN: 13-15 digits)
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
        customer_number=erp_c.customer_number,
        street_number=erp_c.street_number,
        street_name=erp_c.street_name,
        mobile_phone_country=erp_c.mobile_phone_country,
        site_id=erp_c.site_id,
    )


def _normalize_name(name: str) -> str:
    """Normalize name for matching: remove accents, uppercase, strip extra spaces."""
    # Remove accents
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Uppercase, strip, normalize hyphens (double or single -> space)
    result = ascii_only.upper().strip()
    result = result.replace("--", "-").replace("-", " ")
    # Collapse multiple spaces
    result = " ".join(result.split())
    return result


def _match_customer_by_name(customer_name: str, name_map: dict[str, int]) -> int | None:
    """Try to match a Cosium customerName to an OptiFlow customer ID.

    Cosium format: "M. LASTNAME FIRSTNAME", "Mme. LASTNAME FIRSTNAME", "MME LASTNAME FIRSTNAME".
    Strategies: exact match -> strip prefix -> reverse first/last -> partial (2-word prefix).

    Both the input name and map keys are normalized (accent-insensitive,
    hyphen-normalised, uppercased) before comparison.
    """
    if not customer_name:
        return None

    # Build a normalized version of the map for accent/hyphen-insensitive matching
    normalized_map: dict[str, int] = {}
    for key, cid in name_map.items():
        norm_key = _normalize_name(key)
        # Keep the first mapping (don't overwrite)
        if norm_key not in normalized_map:
            normalized_map[norm_key] = cid

    normalized = _normalize_name(customer_name)

    # Direct match
    if normalized in normalized_map:
        return normalized_map[normalized]

    # Strip title prefixes (including with dot and without)
    stripped = normalized
    for prefix in ("M. ", "MME. ", "MLLE. ", "MME ", "MLLE ", "MR. ", "MR ", "MRS. ", "MRS ", "DR. ", "DR "):
        if normalized.startswith(prefix):
            stripped = normalized[len(prefix):]
            break

    if stripped in normalized_map:
        return normalized_map[stripped]

    # Try "FIRSTNAME LASTNAME" -> "LASTNAME FIRSTNAME" (reverse words)
    parts = stripped.split()
    if len(parts) >= 2:
        # Try LAST FIRST (move last word to front)
        reversed_name = f"{parts[-1]} {' '.join(parts[:-1])}"
        if reversed_name in normalized_map:
            return normalized_map[reversed_name]
        # Try just first and last word swapped
        simple_reverse = f"{parts[0]} {parts[-1]}"
        if simple_reverse in normalized_map:
            return normalized_map[simple_reverse]

    # Partial matching: try just the first 2 words (handles compound names
    # like "RENGIG KULISKOVA LUBICA" matching "KULISKOVA LUBICA" or vice versa)
    if len(parts) >= 2:
        two_word = f"{parts[0]} {parts[1]}"
        if two_word in normalized_map:
            return normalized_map[two_word]

    # Try matching the last 2 words (e.g. "RENGIG KULISKOVA LUBICA" -> "KULISKOVA LUBICA")
    if len(parts) >= 3:
        last_two = f"{parts[-2]} {parts[-1]}"
        if last_two in normalized_map:
            return normalized_map[last_two]

    return None


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
        except Exception as exc:
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
            except Exception as e:
                logger.error("enrich_batch_flush_error", error=str(e))

    try:
        db.commit()
    except Exception as e:
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
# Code was moved to erp_sync_invoices.py and erp_sync_extras.py but callers
# that do `from app.services import erp_sync_service; erp_sync_service.sync_invoices()`
# or `@patch("app.services.erp_sync_service.sync_invoices")` still work.
# ---------------------------------------------------------------------------
from app.services.erp_sync_invoices import sync_invoices  # noqa: E402, F401
from app.services.erp_sync_extras import (  # noqa: E402, F401
    sync_payments,
    sync_prescriptions,
    sync_products,
    sync_third_party_payments,
)
