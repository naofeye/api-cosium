"""Service de synchronisation des donnees de reference Cosium -> OptiFlow.

SYNCHRONISATION UNIDIRECTIONNELLE : Cosium -> OptiFlow uniquement.
Gere : calendrier, mutuelles, medecins, marques, fournisseurs, tags, sites,
       banques, societes, utilisateurs, types equipement, materiaux monture,
       categories calendrier, types/categories foyer, materiaux verre,
       tags par client.
"""

import time
from datetime import UTC, datetime
from typing import Any, Callable

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
from app.integrations.cosium.client import CosiumClient
from app.integrations.cosium.cosium_connector import CosiumConnector
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
from app.services.erp_sync_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("cosium_reference_sync")


def _get_cosium_client(db: Session, tenant_id: int) -> CosiumClient:
    """Get an authenticated CosiumClient for the given tenant."""
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)
    if not isinstance(connector, CosiumConnector):
        raise ValueError("Reference sync is only supported for Cosium ERP")
    return connector._client


# ---------------------------------------------------------------------------
# Generic sync helper — handles the repeated fetch/upsert pattern
# ---------------------------------------------------------------------------

def _sync_entity(
    db: Session,
    tenant_id: int,
    user_id: int,
    client: CosiumClient,
    endpoint: str,
    adapter_fn: Callable[[dict], dict],
    model_class: Any,
    entity_name: str,
    id_field: str = "cosium_id",
    page_size: int = 100,
    max_pages: int = 20,
) -> dict:
    """Generic sync for simple reference entities.

    Fetches paginated data from Cosium, adapts each raw item via adapter_fn,
    then upserts into the DB using id_field as the dedup key.
    """
    logger.info(f"sync_{entity_name}_start", tenant_id=tenant_id)

    items = client.get_paginated(endpoint, page_size=page_size, max_pages=max_pages)
    logger.info(f"sync_{entity_name}_fetched", tenant_id=tenant_id, count=len(items))

    # Build existing map keyed by id_field
    existing_map: dict[Any, Any] = {}
    existing_rows = db.scalars(
        select(model_class).where(model_class.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[getattr(row, id_field)] = row

    created = 0
    updated = 0
    seen: set = set()

    for raw in items:
        adapted = adapter_fn(raw)
        eid = adapted.get(id_field)
        if not eid or eid in seen:
            continue
        seen.add(eid)

        if eid in existing_map:
            row = existing_map[eid]
            for key, val in adapted.items():
                setattr(row, key, val)
            if hasattr(row, "synced_at"):
                row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = model_class(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[eid] = new_row
            created += 1

    db.commit()

    result = {"entity": entity_name, "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", f"sync_{entity_name}", 0, new_value=result)
    logger.info(f"sync_{entity_name}_done", tenant_id=tenant_id, **result)
    return result


# ---------------------------------------------------------------------------
# Individual sync functions (thin wrappers around _sync_entity)
# ---------------------------------------------------------------------------

def sync_calendar_events(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les evenements calendrier depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/calendar-events", adapter_fn=adapt_calendar_event,
        model_class=CosiumCalendarEvent, entity_name="calendar_events",
        id_field="cosium_id", page_size=100, max_pages=200,
    )


def sync_mutuelles(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les mutuelles depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/additional-health-cares", adapter_fn=adapt_mutuelle,
        model_class=CosiumMutuelle, entity_name="mutuelles",
        id_field="cosium_id", max_pages=50,
    )


def sync_doctors(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les medecins/prescripteurs depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/doctors", adapter_fn=adapt_doctor,
        model_class=CosiumDoctor, entity_name="doctors",
        id_field="cosium_id",
    )


def sync_brands(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les marques depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/brands", adapter_fn=adapt_brand,
        model_class=CosiumBrand, entity_name="brands",
        id_field="name",
    )


def sync_suppliers(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les fournisseurs depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/suppliers", adapter_fn=adapt_supplier,
        model_class=CosiumSupplier, entity_name="suppliers",
        id_field="name", max_pages=10,
    )


def sync_tags(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les tags depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/tags", adapter_fn=adapt_tag,
        model_class=CosiumTag, entity_name="tags",
        id_field="cosium_id", max_pages=5,
    )


def sync_sites(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les sites/magasins depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/sites", adapter_fn=adapt_site,
        model_class=CosiumSite, entity_name="sites",
        id_field="cosium_id", max_pages=5,
    )


def sync_banks(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les banques depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/banks", adapter_fn=adapt_bank,
        model_class=CosiumBank, entity_name="banks",
        id_field="name", max_pages=5,
    )


def sync_companies(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les societes depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/companies", adapter_fn=adapt_company,
        model_class=CosiumCompany, entity_name="companies",
        id_field="name", max_pages=5,
    )


def sync_users(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les utilisateurs/employes depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/users", adapter_fn=adapt_cosium_user,
        model_class=CosiumUser, entity_name="users",
        id_field="cosium_id", max_pages=5,
    )


def sync_equipment_types(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les types de famille d'equipement depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/equipment-family-types", adapter_fn=adapt_equipment_type,
        model_class=CosiumEquipmentType, entity_name="equipment_types",
        id_field="label_code", max_pages=5,
    )


def sync_frame_materials(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les materiaux de monture depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/eyewear-frame-materials", adapter_fn=adapt_frame_material,
        model_class=CosiumFrameMaterial, entity_name="frame_materials",
        id_field="code", max_pages=5,
    )


def sync_calendar_categories(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les categories d'evenements calendrier depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/calendar-event-categories", adapter_fn=adapt_calendar_category,
        model_class=CosiumCalendarCategory, entity_name="calendar_categories",
        id_field="name", max_pages=5,
    )


def sync_lens_focus_types(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les types de foyer de verre depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/lens-focus-types", adapter_fn=adapt_lens_focus_type,
        model_class=CosiumLensFocusType, entity_name="lens_focus_types",
        id_field="code", max_pages=5,
    )


def sync_lens_focus_categories(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les categories de foyer de verre depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/lens-focus-categories", adapter_fn=adapt_lens_focus_category,
        model_class=CosiumLensFocusCategory, entity_name="lens_focus_categories",
        id_field="code", max_pages=5,
    )


def sync_lens_materials(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les materiaux de verre depuis Cosium."""
    client = _get_cosium_client(db, tenant_id)
    return _sync_entity(
        db, tenant_id, user_id, client,
        endpoint="/lens-materials", adapter_fn=adapt_lens_material,
        model_class=CosiumLensMaterial, entity_name="lens_materials",
        id_field="code", max_pages=5,
    )


def sync_customer_tags(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les tags par client depuis Cosium.

    Itere tous les clients avec un cosium_id et recupere leurs tags.
    Rate limited: 0.3s entre chaque client pour eviter de surcharger Cosium.
    """
    logger.info("sync_customer_tags_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    # Get all customers with a cosium_id
    customers = db.scalars(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id.isnot(None),
            Customer.cosium_id != "",
        )
    ).all()
    logger.info("sync_customer_tags_customers_count", tenant_id=tenant_id, count=len(customers))

    # Load existing customer tags for this tenant
    existing_rows = db.scalars(
        select(CosiumCustomerTag).where(CosiumCustomerTag.tenant_id == tenant_id)
    ).all()
    existing_set: set[tuple[str, str]] = set()
    for row in existing_rows:
        existing_set.add((row.customer_cosium_id, row.tag_code))

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

                new_row = CosiumCustomerTag(
                    tenant_id=tenant_id,
                    customer_id=cust.id,
                    customer_cosium_id=cosium_id,
                    tag_code=tag_code_str,
                )
                db.add(new_row)
                existing_set.add((cosium_id, tag_code_str))
                created += 1

            # Commit in batches of 50 customers
            if (i + 1) % 50 == 0:
                db.commit()
                logger.info(
                    "sync_customer_tags_progress",
                    tenant_id=tenant_id,
                    progress=f"{i + 1}/{len(customers)}",
                    created=created,
                )

        except Exception as exc:
            errors += 1
            logger.warning(
                "sync_customer_tags_error",
                tenant_id=tenant_id,
                customer_cosium_id=cosium_id,
                error=str(exc),
            )

        # Rate limit: 0.3s between customers
        time.sleep(0.3)

    db.commit()

    result = {
        "entity": "customer_tags",
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "total_fetched": total_fetched,
        "customers_processed": len(customers),
    }
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_customer_tags", 0, new_value=result)
    logger.info("sync_customer_tags_done", tenant_id=tenant_id, **result)
    return result


def sync_all_reference(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise toutes les donnees de reference depuis Cosium."""
    logger.info("sync_all_reference_start", tenant_id=tenant_id)

    sync_functions = [
        sync_calendar_events,
        sync_mutuelles,
        sync_doctors,
        sync_brands,
        sync_suppliers,
        sync_tags,
        sync_sites,
        sync_banks,
        sync_companies,
        sync_users,
        sync_equipment_types,
        sync_frame_materials,
        sync_calendar_categories,
        sync_lens_focus_types,
        sync_lens_focus_categories,
        sync_lens_materials,
    ]

    results: list[dict] = []
    total_created = 0
    total_updated = 0

    for sync_fn in sync_functions:
        try:
            result = sync_fn(db, tenant_id, user_id)
            results.append(result)
            total_created += result.get("created", 0)
            total_updated += result.get("updated", 0)
        except Exception as exc:
            entity_name = sync_fn.__name__.replace("sync_", "")
            logger.error("sync_reference_entity_failed", entity=entity_name, error=str(exc), exc_info=True)
            results.append({
                "entity": entity_name,
                "created": 0,
                "updated": 0,
                "total_fetched": 0,
                "error": str(exc),
            })

    combined = {
        "results": results,
        "total_created": total_created,
        "total_updated": total_updated,
    }
    logger.info("sync_all_reference_done", tenant_id=tenant_id, total_created=total_created, total_updated=total_updated)
    return combined
