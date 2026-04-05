"""Service de synchronisation des donnees de reference Cosium -> OptiFlow.

SYNCHRONISATION UNIDIRECTIONNELLE : Cosium -> OptiFlow uniquement.
Gere : calendrier, mutuelles, medecins, marques, fournisseurs, tags, sites.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.cosium.adapter_reference import (
    adapt_brand,
    adapt_calendar_event,
    adapt_doctor,
    adapt_mutuelle,
    adapt_site,
    adapt_supplier,
    adapt_tag,
)
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.models.cosium_reference import (
    CosiumBrand,
    CosiumCalendarEvent,
    CosiumDoctor,
    CosiumMutuelle,
    CosiumSite,
    CosiumSupplier,
    CosiumTag,
)
from app.services import audit_service
from app.services.erp_sync_service import _authenticate_connector, _get_connector_for_tenant

logger = get_logger("cosium_reference_sync")


def _get_cosium_client(db: Session, tenant_id: int):
    """Get an authenticated CosiumClient for the given tenant."""
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)
    if not isinstance(connector, CosiumConnector):
        raise ValueError("Reference sync is only supported for Cosium ERP")
    return connector._client


def sync_calendar_events(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les evenements calendrier depuis Cosium."""
    logger.info("sync_calendar_events_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/calendar-events", page_size=100, max_pages=200)
    logger.info("sync_calendar_events_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[int, CosiumCalendarEvent] = {}
    existing_rows = db.scalars(
        select(CosiumCalendarEvent).where(CosiumCalendarEvent.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0
    seen_ids: set[int] = set()

    for raw in items:
        adapted = adapt_calendar_event(raw)
        cosium_id = adapted["cosium_id"]
        if not cosium_id or cosium_id in seen_ids:
            continue
        seen_ids.add(cosium_id)

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumCalendarEvent(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            created += 1

    db.commit()

    result = {"entity": "calendar_events", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_calendar_events", 0, new_value=result)
    logger.info("sync_calendar_events_done", tenant_id=tenant_id, **result)
    return result


def sync_mutuelles(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les mutuelles depuis Cosium."""
    logger.info("sync_mutuelles_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/additional-health-cares", page_size=100, max_pages=50)
    logger.info("sync_mutuelles_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[int, CosiumMutuelle] = {}
    existing_rows = db.scalars(
        select(CosiumMutuelle).where(CosiumMutuelle.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_mutuelle(raw)
        cosium_id = adapted["cosium_id"]
        if not cosium_id:
            continue

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumMutuelle(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            created += 1

    db.commit()

    result = {"entity": "mutuelles", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_mutuelles", 0, new_value=result)
    logger.info("sync_mutuelles_done", tenant_id=tenant_id, **result)
    return result


def sync_doctors(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les medecins/prescripteurs depuis Cosium."""
    logger.info("sync_doctors_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/doctors", page_size=100, max_pages=20)
    logger.info("sync_doctors_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumDoctor] = {}
    existing_rows = db.scalars(
        select(CosiumDoctor).where(CosiumDoctor.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0
    seen_ids: set[str] = set()

    for raw in items:
        adapted = adapt_doctor(raw)
        cosium_id = adapted["cosium_id"]
        if not cosium_id or cosium_id in seen_ids:
            continue
        seen_ids.add(cosium_id)

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumDoctor(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            created += 1

    db.commit()

    result = {"entity": "doctors", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_doctors", 0, new_value=result)
    logger.info("sync_doctors_done", tenant_id=tenant_id, **result)
    return result


def sync_brands(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les marques depuis Cosium."""
    logger.info("sync_brands_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/brands", page_size=100, max_pages=20)
    logger.info("sync_brands_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumBrand] = {}
    existing_rows = db.scalars(
        select(CosiumBrand).where(CosiumBrand.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.name] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_brand(raw)
        name = adapted["name"]
        if not name:
            continue

        if name in existing_map:
            row = existing_map[name]
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumBrand(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[name] = new_row
            created += 1

    db.commit()

    result = {"entity": "brands", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_brands", 0, new_value=result)
    logger.info("sync_brands_done", tenant_id=tenant_id, **result)
    return result


def sync_suppliers(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les fournisseurs depuis Cosium."""
    logger.info("sync_suppliers_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/suppliers", page_size=100, max_pages=10)
    logger.info("sync_suppliers_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumSupplier] = {}
    existing_rows = db.scalars(
        select(CosiumSupplier).where(CosiumSupplier.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.name] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_supplier(raw)
        name = adapted["name"]
        if not name:
            continue

        if name in existing_map:
            row = existing_map[name]
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumSupplier(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[name] = new_row
            created += 1

    db.commit()

    result = {"entity": "suppliers", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_suppliers", 0, new_value=result)
    logger.info("sync_suppliers_done", tenant_id=tenant_id, **result)
    return result


def sync_tags(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les tags depuis Cosium."""
    logger.info("sync_tags_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/tags", page_size=100, max_pages=5)
    logger.info("sync_tags_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[int, CosiumTag] = {}
    existing_rows = db.scalars(
        select(CosiumTag).where(CosiumTag.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_tag(raw)
        cosium_id = adapted["cosium_id"]
        if not cosium_id:
            continue

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumTag(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            created += 1

    db.commit()

    result = {"entity": "tags", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_tags", 0, new_value=result)
    logger.info("sync_tags_done", tenant_id=tenant_id, **result)
    return result


def sync_sites(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les sites/magasins depuis Cosium."""
    logger.info("sync_sites_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    # Sites may use top-level content instead of HAL _embedded
    items = client.get_paginated("/sites", page_size=100, max_pages=5)
    logger.info("sync_sites_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[int, CosiumSite] = {}
    existing_rows = db.scalars(
        select(CosiumSite).where(CosiumSite.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_site(raw)
        cosium_id = adapted["cosium_id"]
        if not cosium_id:
            continue

        if cosium_id in existing_map:
            row = existing_map[cosium_id]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumSite(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            created += 1

    db.commit()

    result = {"entity": "sites", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_sites", 0, new_value=result)
    logger.info("sync_sites_done", tenant_id=tenant_id, **result)
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
