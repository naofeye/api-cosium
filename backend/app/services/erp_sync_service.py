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
from app.integrations.erp_models import ERPCustomer
from app.models import Customer, Tenant
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
    """Authentifie le connecteur avec les credentials du tenant."""
    from app.core.config import settings

    if connector.erp_type == "cosium":
        base_url = settings.cosium_base_url
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
    """Synchronise les clients depuis l'ERP vers OptiFlow (lecture seule)."""
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_customers", entity="customer")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    erp_customers = connector.get_customers()
    created = 0
    updated = 0
    skipped = 0
    warnings: list[str] = []

    for erp_c in erp_customers:
        if not erp_c.last_name:
            skipped += 1
            msg = f"Client sans nom de famille ignore (email={erp_c.email}, prenom={erp_c.first_name})"
            warnings.append(msg)
            logger.warning("sync_customer_skipped", reason="empty_last_name", email=erp_c.email)
            continue

        existing = _find_existing_customer(db, tenant_id, erp_c)

        if existing:
            changed = _update_customer_fields(existing, erp_c)
            if changed:
                existing.updated_at = datetime.now(UTC).replace(tzinfo=None)
                updated += 1
        else:
            customer = _create_customer_from_erp(tenant_id, erp_c)
            db.add(customer)
            created += 1

    db.commit()

    result = {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "warnings": warnings,
        "total": len(erp_customers),
    }
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_customers", 0, new_value=result)
    logger.info("sync_customers_done", tenant_id=tenant_id, erp=connector.erp_type, **result)
    return result


def sync_invoices(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les factures depuis l'ERP (lecture seule)."""
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_invoices", entity="invoice")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    erp_invoices = connector.get_invoices()
    result = {"fetched": len(erp_invoices), "note": "Invoice import requires mapping to OptiFlow factures model"}

    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_invoices", 0, new_value=result)
    logger.info("sync_invoices_done", tenant_id=tenant_id, erp=connector.erp_type, fetched=len(erp_invoices))
    return result


def sync_products(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les produits depuis l'ERP (lecture seule)."""
    if not user_id:
        logger.warning("operation_without_user_id", action="sync_products", entity="product")
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)

    erp_products = connector.get_products()
    result = {"fetched": len(erp_products), "note": "Product catalog import for future use"}

    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_products", 0, new_value=result)
    logger.info("sync_products_done", tenant_id=tenant_id, erp=connector.erp_type, fetched=len(erp_products))
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
