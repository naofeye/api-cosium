from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.notifications import (
    ActionItemListResponse,
    ActionItemResponse,
)
from app.models import Case, Customer, Document, DocumentType, Payment
from app.repositories import action_item_repo

logger = get_logger("action_item_service")


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
    _generate_incomplete_cases(db, tenant_id, user_id)
    _generate_overdue_payments(db, tenant_id, user_id)
    db.commit()
    logger.info("action_items_generated", tenant_id=tenant_id, user_id=user_id)
    return list_action_items(db, tenant_id, user_id, status="pending")


def _generate_incomplete_cases(db: Session, tenant_id: int, user_id: int) -> None:
    required_count = (
        db.scalar(select(func.count()).select_from(DocumentType).where(DocumentType.is_required.is_(True))) or 0
    )
    if required_count == 0:
        return

    required_codes = [
        code for (code,) in db.execute(select(DocumentType.code).where(DocumentType.is_required.is_(True))).all()
    ]

    cases = db.execute(
        select(Case.id, Customer.first_name, Customer.last_name)
        .join(Customer, Customer.id == Case.customer_id)
        .where(Case.tenant_id == tenant_id)
    ).all()

    for case_row in cases:
        present = (
            db.scalar(
                select(func.count(func.distinct(Document.type))).where(
                    Document.case_id == case_row.id, Document.type.in_(required_codes)
                )
            )
            or 0
        )
        missing = required_count - present
        if missing > 0:
            existing = action_item_repo.find_existing(
                db,
                user_id=user_id,
                tenant_id=tenant_id,
                type="dossier_incomplet",
                entity_type="case",
                entity_id=case_row.id,
            )
            if not existing:
                action_item_repo.create(
                    db,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    type="dossier_incomplet",
                    title=f"Dossier incomplet -{case_row.first_name} {case_row.last_name}",
                    description=f"{missing} piece(s) obligatoire(s) manquante(s)",
                    entity_type="case",
                    entity_id=case_row.id,
                    priority="high" if missing >= 3 else "medium",
                )
        else:
            action_item_repo.delete_resolved(
                db,
                user_id=user_id,
                tenant_id=tenant_id,
                type="dossier_incomplet",
                entity_type="case",
                entity_id=case_row.id,
            )


def _generate_overdue_payments(db: Session, tenant_id: int, user_id: int) -> None:
    overdue = db.execute(
        select(Payment.id, Payment.case_id, Payment.amount_due, Payment.amount_paid, Payment.payer_type)
        .where(Payment.tenant_id == tenant_id)
        .where(Payment.status.in_(["pending", "partial"]))
        .where(Payment.amount_paid < Payment.amount_due)
    ).all()

    for p in overdue:
        remaining = float(p.amount_due) - float(p.amount_paid)
        existing = action_item_repo.find_existing(
            db, user_id=user_id, tenant_id=tenant_id, type="paiement_retard", entity_type="payment", entity_id=p.id
        )
        if not existing:
            action_item_repo.create(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                type="paiement_retard",
                title=f"Paiement en attente -{p.payer_type}",
                description=f"Reste a payer : {remaining:.2f} EUR",
                entity_type="payment",
                entity_id=p.id,
                priority="high",
            )
