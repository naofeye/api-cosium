"""Service de synchronisation des donnees de reference Cosium -> OptiFlow.

SYNCHRONISATION UNIDIRECTIONNELLE : Cosium -> OptiFlow uniquement.

Orchestrator/facade. Individual entity sync functions are in
cosium_reference_sync_entities.py and re-exported here for backward compatibility.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.cosium.client import CosiumClient
from app.services import audit_service

# Re-export all individual sync functions for backward compatibility.
from app.services.cosium_reference_sync_entities import (
    sync_banks,
    sync_brands,
    sync_calendar_categories,
    sync_calendar_events,
    sync_companies,
    sync_customer_tags,
    sync_doctors,
    sync_equipment_types,
    sync_frame_materials,
    sync_lens_focus_categories,
    sync_lens_focus_types,
    sync_lens_materials,
    sync_mutuelles,
    sync_sites,
    sync_suppliers,
    sync_tags,
    sync_users,
)

logger = get_logger("cosium_reference_sync")

__all__ = [
    "sync_calendar_events",
    "sync_mutuelles",
    "sync_doctors",
    "sync_brands",
    "sync_suppliers",
    "sync_tags",
    "sync_sites",
    "sync_banks",
    "sync_companies",
    "sync_users",
    "sync_equipment_types",
    "sync_frame_materials",
    "sync_calendar_categories",
    "sync_lens_focus_types",
    "sync_lens_focus_categories",
    "sync_lens_materials",
    "sync_customer_tags",
    "sync_all_reference",
]


def _get_cosium_client(db: Session, tenant_id: int) -> CosiumClient:
    """Get an authenticated CosiumClient for the given tenant.

    Wrapper retro-compat : delegue a `app.integrations.cosium.factory`.
    Conserve pour ne pas casser les tests qui patchent ce symbole.
    """
    from app.integrations.cosium.factory import get_cosium_client_for_tenant

    return get_cosium_client_for_tenant(db, tenant_id)


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
# Orchestrator — syncs all reference entities
# ---------------------------------------------------------------------------

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
        except (ConnectionError, TimeoutError, OSError, ValueError) as exc:
            entity_name = sync_fn.__name__.replace("sync_", "")
            logger.error(
                "sync_reference_entity_failed",
                entity=entity_name,
                error=str(exc),
                exc_info=True,
            )
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
    logger.info(
        "sync_all_reference_done",
        tenant_id=tenant_id,
        total_created=total_created,
        total_updated=total_updated,
    )
    return combined
