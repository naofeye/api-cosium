"""Helpers internes pour erp_sync_*.py — batch flush, parsing date, lookup customers."""
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import Customer
from app.services import audit_service
from app.services.erp_matching_service import _normalize_name

BATCH_SIZE = 500
logger = get_logger("erp_sync_helpers")


def parse_iso_date(value: Any) -> datetime | None:
    """Parse une date ISO 8601, gere le suffixe Z. None si invalide."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def safe_batch_flush(db: Session, processed: int, batch_errors: int, log_key: str) -> int:
    """Flush la session toutes les BATCH_SIZE operations. Retourne batch_errors mis a jour."""
    if processed % BATCH_SIZE != 0:
        return batch_errors
    try:
        db.flush()
    except SQLAlchemyError as e:
        db.rollback()
        batch_errors += 1
        logger.error(f"{log_key}_batch_error", batch=processed // BATCH_SIZE, error=str(e))
    return batch_errors


def safe_final_commit(db: Session, tenant_id: int, log_key: str) -> None:
    """Commit final, log et re-raise en cas d'erreur."""
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{log_key}_commit_failed", tenant_id=tenant_id, error=str(e))
        raise


def build_customer_name_lookup(db: Session, tenant_id: int) -> tuple[dict[str, int], dict[str, int]]:
    """Construit (name_map, cosium_id_map) pour matcher des paiements aux clients."""
    all_customers = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    name_map: dict[str, int] = {}
    cosium_id_map: dict[str, int] = {}
    for c in all_customers:
        name_map[_normalize_name(f"{c.last_name} {c.first_name}")] = c.id
        name_map[_normalize_name(f"{c.first_name} {c.last_name}")] = c.id
        if c.cosium_id:
            cosium_id_map[str(c.cosium_id)] = c.id
    return name_map, cosium_id_map


def build_cosium_id_to_customer(db: Session, tenant_id: int) -> dict[int, int]:
    """customer.cosium_id (int) -> customer.id pour matcher prescriptions."""
    all_customers = db.scalars(select(Customer).where(Customer.tenant_id == tenant_id)).all()
    mapping: dict[int, int] = {}
    for c in all_customers:
        erp_id = getattr(c, "cosium_id", None) or getattr(c, "erp_id", None)
        if erp_id:
            try:
                mapping[int(erp_id)] = c.id
            except (ValueError, TypeError):
                pass
    return mapping


def audit_sync_completion(
    db: Session, tenant_id: int, user_id: int, action: str, result: dict,
) -> None:
    """Enregistre l'audit log de fin de sync (no-op si user_id=0)."""
    if user_id:
        audit_service.log_action(db, tenant_id, user_id, "create", action, 0, new_value=result)


def warn_if_no_user(action: str, entity: str, user_id: int) -> None:
    if not user_id:
        logger.warning("operation_without_user_id", action=action, entity=entity)
