"""Service de synchronisation des donnees de reference Cosium -> OptiFlow.

SYNCHRONISATION UNIDIRECTIONNELLE : Cosium -> OptiFlow uniquement.
Gere : calendrier, mutuelles, medecins, marques, fournisseurs, tags, sites,
       banques, societes, utilisateurs, types equipement, materiaux monture,
       categories calendrier, types/categories foyer, materiaux verre,
       tags par client.
"""

import time
from datetime import UTC, datetime

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


def sync_banks(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les banques depuis Cosium."""
    logger.info("sync_banks_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/banks", page_size=100, max_pages=5)
    logger.info("sync_banks_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumBank] = {}
    existing_rows = db.scalars(
        select(CosiumBank).where(CosiumBank.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.name] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_bank(raw)
        name = adapted["name"]
        if not name:
            continue

        if name in existing_map:
            row = existing_map[name]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumBank(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[name] = new_row
            created += 1

    db.commit()

    result = {"entity": "banks", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_banks", 0, new_value=result)
    logger.info("sync_banks_done", tenant_id=tenant_id, **result)
    return result


def sync_companies(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les societes depuis Cosium."""
    logger.info("sync_companies_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/companies", page_size=100, max_pages=5)
    logger.info("sync_companies_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumCompany] = {}
    existing_rows = db.scalars(
        select(CosiumCompany).where(CosiumCompany.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.name] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_company(raw)
        name = adapted["name"]
        if not name:
            continue

        if name in existing_map:
            row = existing_map[name]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumCompany(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[name] = new_row
            created += 1

    db.commit()

    result = {"entity": "companies", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_companies", 0, new_value=result)
    logger.info("sync_companies_done", tenant_id=tenant_id, **result)
    return result


def sync_users(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les utilisateurs/employes depuis Cosium."""
    logger.info("sync_users_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/users", page_size=100, max_pages=5)
    logger.info("sync_users_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[int, CosiumUser] = {}
    existing_rows = db.scalars(
        select(CosiumUser).where(CosiumUser.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.cosium_id] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_cosium_user(raw)
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
            new_row = CosiumUser(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            created += 1

    db.commit()

    result = {"entity": "users", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_users", 0, new_value=result)
    logger.info("sync_users_done", tenant_id=tenant_id, **result)
    return result


def sync_equipment_types(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les types de famille d'equipement depuis Cosium."""
    logger.info("sync_equipment_types_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/equipment-family-types", page_size=100, max_pages=5)
    logger.info("sync_equipment_types_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumEquipmentType] = {}
    existing_rows = db.scalars(
        select(CosiumEquipmentType).where(CosiumEquipmentType.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.label_code] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_equipment_type(raw)
        code = adapted["label_code"]
        if not code:
            continue

        if code in existing_map:
            row = existing_map[code]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumEquipmentType(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[code] = new_row
            created += 1

    db.commit()

    result = {"entity": "equipment_types", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_equipment_types", 0, new_value=result)
    logger.info("sync_equipment_types_done", tenant_id=tenant_id, **result)
    return result


def sync_frame_materials(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les materiaux de monture depuis Cosium."""
    logger.info("sync_frame_materials_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/eyewear-frame-materials", page_size=100, max_pages=5)
    logger.info("sync_frame_materials_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumFrameMaterial] = {}
    existing_rows = db.scalars(
        select(CosiumFrameMaterial).where(CosiumFrameMaterial.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.code] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_frame_material(raw)
        code = adapted["code"]
        if not code:
            continue

        if code in existing_map:
            row = existing_map[code]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumFrameMaterial(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[code] = new_row
            created += 1

    db.commit()

    result = {"entity": "frame_materials", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_frame_materials", 0, new_value=result)
    logger.info("sync_frame_materials_done", tenant_id=tenant_id, **result)
    return result


def sync_calendar_categories(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les categories d'evenements calendrier depuis Cosium."""
    logger.info("sync_calendar_categories_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/calendar-event-categories", page_size=100, max_pages=5)
    logger.info("sync_calendar_categories_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumCalendarCategory] = {}
    existing_rows = db.scalars(
        select(CosiumCalendarCategory).where(CosiumCalendarCategory.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.name] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_calendar_category(raw)
        name = adapted["name"]
        if not name:
            continue

        if name in existing_map:
            row = existing_map[name]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumCalendarCategory(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[name] = new_row
            created += 1

    db.commit()

    result = {"entity": "calendar_categories", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_calendar_categories", 0, new_value=result)
    logger.info("sync_calendar_categories_done", tenant_id=tenant_id, **result)
    return result


def sync_lens_focus_types(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les types de foyer de verre depuis Cosium."""
    logger.info("sync_lens_focus_types_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/lens-focus-types", page_size=100, max_pages=5)
    logger.info("sync_lens_focus_types_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumLensFocusType] = {}
    existing_rows = db.scalars(
        select(CosiumLensFocusType).where(CosiumLensFocusType.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.code] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_lens_focus_type(raw)
        code = adapted["code"]
        if not code:
            continue

        if code in existing_map:
            row = existing_map[code]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumLensFocusType(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[code] = new_row
            created += 1

    db.commit()

    result = {"entity": "lens_focus_types", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_lens_focus_types", 0, new_value=result)
    logger.info("sync_lens_focus_types_done", tenant_id=tenant_id, **result)
    return result


def sync_lens_focus_categories(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les categories de foyer de verre depuis Cosium."""
    logger.info("sync_lens_focus_categories_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/lens-focus-categories", page_size=100, max_pages=5)
    logger.info("sync_lens_focus_categories_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumLensFocusCategory] = {}
    existing_rows = db.scalars(
        select(CosiumLensFocusCategory).where(CosiumLensFocusCategory.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.code] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_lens_focus_category(raw)
        code = adapted["code"]
        if not code:
            continue

        if code in existing_map:
            row = existing_map[code]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumLensFocusCategory(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[code] = new_row
            created += 1

    db.commit()

    result = {"entity": "lens_focus_categories", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_lens_focus_categories", 0, new_value=result)
    logger.info("sync_lens_focus_categories_done", tenant_id=tenant_id, **result)
    return result


def sync_lens_materials(db: Session, tenant_id: int, user_id: int = 0) -> dict:
    """Synchronise les materiaux de verre depuis Cosium."""
    logger.info("sync_lens_materials_start", tenant_id=tenant_id)
    client = _get_cosium_client(db, tenant_id)

    items = client.get_paginated("/lens-materials", page_size=100, max_pages=5)
    logger.info("sync_lens_materials_fetched", tenant_id=tenant_id, count=len(items))

    existing_map: dict[str, CosiumLensMaterial] = {}
    existing_rows = db.scalars(
        select(CosiumLensMaterial).where(CosiumLensMaterial.tenant_id == tenant_id)
    ).all()
    for row in existing_rows:
        existing_map[row.code] = row

    created = 0
    updated = 0

    for raw in items:
        adapted = adapt_lens_material(raw)
        code = adapted["code"]
        if not code:
            continue

        if code in existing_map:
            row = existing_map[code]
            for key, val in adapted.items():
                setattr(row, key, val)
            row.synced_at = datetime.now(UTC)
            updated += 1
        else:
            new_row = CosiumLensMaterial(tenant_id=tenant_id, **adapted)
            db.add(new_row)
            existing_map[code] = new_row
            created += 1

    db.commit()

    result = {"entity": "lens_materials", "created": created, "updated": updated, "total_fetched": len(items)}
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", "sync_lens_materials", 0, new_value=result)
    logger.info("sync_lens_materials_done", tenant_id=tenant_id, **result)
    return result


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
