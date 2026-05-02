"""Helpers concrets d'emission webhook depuis les services metier.

Centralise la conversion entity -> payload + appel webhook_service.
Tous les helpers sont best-effort : un crash n'interrompt jamais le flux
metier amont (le service webhook_service.emit_webhook_event garantit deja
le swallow d'exception, mais on ajoute une couche).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.services.webhook_service import emit_webhook_event

logger = get_logger("webhook_emit")


def _safe_emit(
    db: Session, tenant_id: int, event_type: str, payload: dict
) -> None:
    """Emit avec swallow defensif. Le service en interne en a deja un, mais
    cet helper protege aussi contre les erreurs d'argument (model.dict()...)."""
    try:
        emit_webhook_event(
            db, tenant_id=tenant_id, event_type=event_type, payload=payload
        )
    except Exception as exc:
        logger.warning(
            "webhook_helper_failed",
            tenant_id=tenant_id,
            event_type=event_type,
            error=str(exc),
            error_type=type(exc).__name__,
        )


def _entity_to_dict(entity: Any) -> dict:
    """Serialise un schema Pydantic ou un dict en dict JSON-safe."""
    if hasattr(entity, "model_dump"):
        return entity.model_dump(mode="json")
    if isinstance(entity, dict):
        return entity
    return {"value": str(entity)}


def emit_client_created(db: Session, tenant_id: int, client) -> None:
    _safe_emit(db, tenant_id, "client.created", _entity_to_dict(client))


def emit_client_updated(db: Session, tenant_id: int, client) -> None:
    _safe_emit(db, tenant_id, "client.updated", _entity_to_dict(client))


def emit_client_deleted(
    db: Session, tenant_id: int, client_id: int, force: bool
) -> None:
    _safe_emit(
        db,
        tenant_id,
        "client.deleted",
        {"client_id": client_id, "force": force},
    )


def emit_facture_created(db: Session, tenant_id: int, facture) -> None:
    _safe_emit(db, tenant_id, "facture.created", _entity_to_dict(facture))


def emit_facture_avoir_created(
    db: Session, tenant_id: int, avoir, original_facture_id: int
) -> None:
    payload = _entity_to_dict(avoir)
    payload["original_facture_id"] = original_facture_id
    _safe_emit(db, tenant_id, "facture.avoir_created", payload)


def emit_devis_created(db: Session, tenant_id: int, devis) -> None:
    _safe_emit(db, tenant_id, "devis.created", _entity_to_dict(devis))


def emit_devis_status_changed(
    db: Session, tenant_id: int, devis, new_status: str
) -> None:
    """Emet l'event derive du nouveau status (signe/refuse) si applicable."""
    mapping = {
        "signe": "devis.signed",
        "refuse": "devis.refused",
    }
    event_type = mapping.get(new_status)
    if not event_type:
        return
    _safe_emit(db, tenant_id, event_type, _entity_to_dict(devis))
