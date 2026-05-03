"""Service action items : list/update/generate.

Generators (logique de detection) extraits dans le package
`_action_items/_generators.py`. Helper de scoring deterministe dans
`_action_items/impact_score.py`.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.notifications import (
    ActionItemListResponse,
    ActionItemResponse,
)
from app.repositories import action_item_repo
from app.services._action_items._generators import (
    generate_incomplete_cases,
    generate_overdue_cosium_invoices,
    generate_overdue_payments,
    generate_renewal_opportunities,
    generate_stale_quotes,
    generate_upcoming_appointments,
)

logger = get_logger("action_item_service")

# Re-exports pour compat tests existants qui patchent
# `app.services.action_item_service._generate_*`
_generate_incomplete_cases = generate_incomplete_cases
_generate_upcoming_appointments = generate_upcoming_appointments
_generate_overdue_cosium_invoices = generate_overdue_cosium_invoices
_generate_stale_quotes = generate_stale_quotes
_generate_renewal_opportunities = generate_renewal_opportunities
_generate_overdue_payments = generate_overdue_payments


def list_action_items(
    db: Session,
    tenant_id: int,
    user_id: int,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ActionItemListResponse:
    items, total = action_item_repo.list_by_user(
        db, user_id=user_id, tenant_id=tenant_id, status=status, priority=priority, limit=limit, offset=offset
    )
    counts = action_item_repo.get_counts_by_type(db, user_id=user_id, tenant_id=tenant_id)
    return ActionItemListResponse(
        items=[ActionItemResponse.model_validate(i) for i in items],
        total=total,
        counts=counts,
    )


def update_status(db: Session, tenant_id: int, item_id: int, status: str) -> None:
    action_item_repo.update_status(db, item_id=item_id, tenant_id=tenant_id, status=status)
    db.commit()
    logger.info("action_item_updated", tenant_id=tenant_id, item_id=item_id, status=status)


def generate_action_items(db: Session, tenant_id: int, user_id: int) -> ActionItemListResponse:
    # Utilise les aliases _generate_* (bindings module-level) pour permettre
    # aux tests de patcher individuellement chaque generator.
    _generate_incomplete_cases(db, tenant_id, user_id)
    _generate_overdue_payments(db, tenant_id, user_id)
    _generate_upcoming_appointments(db, tenant_id, user_id)
    _generate_overdue_cosium_invoices(db, tenant_id, user_id)
    _generate_stale_quotes(db, tenant_id, user_id)
    _generate_renewal_opportunities(db, tenant_id, user_id)
    db.commit()
    logger.info("action_items_generated", tenant_id=tenant_id, user_id=user_id)
    return list_action_items(db, tenant_id, user_id, status="pending")
