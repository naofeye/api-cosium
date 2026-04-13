"""Individual sync functions for each Cosium reference entity type.

Thin wrappers around the generic _sync_entity helper in cosium_reference_sync.
"""

import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.cosium.adapter_reference import (
    adapt_bank,
    adapt_brand,
    adapt_calendar_category,
    adapt_calendar_event,
    adapt_company,
    adapt_cosium_user,
    adapt_doctor,
    adapt_equipment_type,
    adapt_frame_material,
    adapt_lens_focus_category,
    adapt_lens_focus_type,
    adapt_lens_material,
    adapt_mutuelle,
    adapt_site,
    adapt_supplier,
    adapt_tag,
)
from app.models.client import Customer
from app.models.cosium_reference import (
    CosiumBank,
    CosiumBrand,
    CosiumCalendarCategory,
    CosiumCalendarEvent,
    CosiumCompany,
    CosiumCustomerTag,
    CosiumDoctor,
    CosiumEquipmentType,
    CosiumFrameMaterial,
    CosiumLensFocusCategory,
    CosiumLensFocusType,
    CosiumLensMaterial,
    CosiumMutuelle,
    CosiumSite,
    CosiumSupplier,
    CosiumTag,
    CosiumUser,
)
from app.services import audit_service

logger = get_logger("cosium_reference_sync_entities")


def _do_sync(db, tenant_id, user_id, endpoint, adapter_fn, model_class, entity_name, **kw):
    """Shortcut: authenticate + call _sync_entity."""
    from app.services.cosium_reference_sync import _get_cosium_client, _sync_entity
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(db, tenant_id, user_id, client, endpoint=endpoint,
                        adapter_fn=adapter_fn, model_class=model_class,
                        entity_name=entity_name, **kw)


def sync_calendar_events(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les evenements calendrier depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/calendar-events", adapt_calendar_event,
                    CosiumCalendarEvent, "calendar_events", id_field="cosium_id",
                    page_size=100, max_pages=200)


def sync_mutuelles(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les mutuelles depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/additional-health-cares", adapt_mutuelle,
                    CosiumMutuelle, "mutuelles", id_field="cosium_id", max_pages=50)


def sync_doctors(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les medecins/prescripteurs depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/doctors", adapt_doctor,
                    CosiumDoctor, "doctors", id_field="cosium_id")


def sync_brands(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les marques depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/brands", adapt_brand,
                    CosiumBrand, "brands", id_field="name")


def sync_suppliers(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les fournisseurs depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/suppliers", adapt_supplier,
                    CosiumSupplier, "suppliers", id_field="name", max_pages=10)


def sync_tags(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les tags depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/tags", adapt_tag,
                    CosiumTag, "tags", id_field="cosium_id", max_pages=5)


def sync_sites(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les sites/magasins depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/sites", adapt_site,
                    CosiumSite, "sites", id_field="cosium_id", max_pages=5)


def sync_banks(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les banques depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/banks", adapt_bank,
                    CosiumBank, "banks", id_field="name", max_pages=5)


def sync_companies(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les societes depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/companies", adapt_company,
                    CosiumCompany, "companies", id_field="name", max_pages=5)


def sync_users(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les utilisateurs/employes depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/users", adapt_cosium_user,
                    CosiumUser, "users", id_field="cosium_id", max_pages=5)


def sync_equipment_types(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les types de famille d'equipement depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/equipment-family-types", adapt_equipment_type,
                    CosiumEquipmentType, "equipment_types", id_field="label_code", max_pages=5)


def sync_frame_materials(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les materiaux de monture depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/eyewear-frame-materials", adapt_frame_material,
                    CosiumFrameMaterial, "frame_materials", id_field="code", max_pages=5)


def sync_calendar_categories(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les categories d'evenements calendrier depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/calendar-event-categories", adapt_calendar_category,
                    CosiumCalendarCategory, "calendar_categories", id_field="name", max_pages=5)


def sync_lens_focus_types(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les types de foyer de verre depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/lens-focus-types", adapt_lens_focus_type,
                    CosiumLensFocusType, "lens_focus_types", id_field="code", max_pages=5)


def sync_lens_focus_categories(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les categories de foyer de verre depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/lens-focus-categories", adapt_lens_focus_category,
                    CosiumLensFocusCategory, "lens_focus_categories", id_field="code", max_pages=5)


def sync_lens_materials(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les materiaux de verre depuis Cosium."""
    return _do_sync(db, tenant_id, user_id, "/lens-materials", adapt_lens_material,
                    CosiumLensMaterial, "lens_materials", id_field="code", max_pages=5)


def sync_customer_tags(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les tags par client depuis Cosium.

    Itere tous les clients avec un cosium_id et recupere leurs tags.
    Rate limited: 0.3s entre chaque client pour eviter de surcharger Cosium.
    """
    from app.services.cosium_reference_sync import _get_cosium_client

    logger.info("sync_customer_tags_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    customers = db.scalars(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id.isnot(None),
            Customer.cosium_id != "",
        )
    ).all()
    logger.info("sync_customer_tags_customers_count", tenant_id=tenant_id, count=len(customers))

    existing_rows = db.scalars(
        select(CosiumCustomerTag).where(CosiumCustomerTag.tenant_id == tenant_id)
    ).all()
    existing_set: set[tuple[str, str]] = {
        (row.customer_cosium_id, row.tag_code) for row in existing_rows
    }

    created = 0
    skipped = 0
    errors = 0
    total_fetched = 0

    for i, cust in enumerate(customers):
        cosium_id = str(cust.cosium_id)
        try:
            data = client.get(f"/customers/{cosium_id}/tags")
            codes = data.get("codes", []) if isinstance(data, dict) else []
            total_fetched += len(codes)
            for tag_code in codes:
                if not tag_code:
                    continue
                tag_code_str = str(tag_code)
                if (cosium_id, tag_code_str) in existing_set:
                    skipped += 1
                    continue
                db.add(CosiumCustomerTag(
                    tenant_id=tenant_id, customer_id=cust.id,
                    customer_cosium_id=cosium_id, tag_code=tag_code_str,
                ))
                existing_set.add((cosium_id, tag_code_str))
                created += 1
            if (i + 1) % 50 == 0:
                db.commit()
                logger.info("sync_customer_tags_progress", tenant_id=tenant_id,
                            progress=f"{i + 1}/{len(customers)}", created=created)
        except (ConnectionError, TimeoutError, OSError, ValueError) as exc:
            errors += 1
            logger.warning("sync_customer_tags_error", tenant_id=tenant_id,
                           customer_cosium_id=cosium_id, error=str(exc))
        time.sleep(0.3)

    db.commit()
    result = {
        "entity": "customer_tags", "created": created, "skipped": skipped,
        "errors": errors, "total_fetched": total_fetched,
        "customers_processed": len(customers),
    }
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_customer_tags", 0, new_value=result)
    logger.info("sync_customer_tags_done", tenant_id=tenant_id, **result)
    return result
