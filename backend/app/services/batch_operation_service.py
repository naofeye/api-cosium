"""Batch PEC operation service — OptiSante bulk processing.

Orchestrates batch creation, consolidation, pre-control, and PEC preparation
for all clients linked to a marketing code (Cosium tag).
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.batch_operation import (
    BatchItemResponse,
    BatchOperationResponse,
    BatchPecResult,
    BatchSummaryResponse,
    MarketingCodeResponse,
)
from app.models.batch_operation import BatchOperation, BatchOperationItem
from app.models.client import Customer
from app.models.cosium_reference import CosiumCustomerTag, CosiumTag
from app.repositories import batch_operation_repo
from app.services import consolidation_service, pec_preparation_service

logger = get_logger("batch_operation_service")


def get_available_marketing_codes(
    db: Session, tenant_id: int
) -> list[MarketingCodeResponse]:
    """List all marketing codes (tags) with client counts."""
    stmt = (
        select(
            CosiumCustomerTag.tag_code,
            func.count(CosiumCustomerTag.id).label("cnt"),
        )
        .where(CosiumCustomerTag.tenant_id == tenant_id)
        .group_by(CosiumCustomerTag.tag_code)
        .order_by(func.count(CosiumCustomerTag.id).desc())
    )
    rows = db.execute(stmt).all()

    # Fetch tag descriptions from CosiumTag
    tag_codes = [r[0] for r in rows]
    descriptions: dict[str, str] = {}
    if tag_codes:
        tag_stmt = select(CosiumTag.code, CosiumTag.description).where(
            CosiumTag.tenant_id == tenant_id,
            CosiumTag.code.in_(tag_codes),
        )
        for code, desc in db.execute(tag_stmt).all():
            descriptions[code] = desc

    return [
        MarketingCodeResponse(
            code=tag_code,
            description=descriptions.get(tag_code, ""),
            client_count=count,
        )
        for tag_code, count in rows
    ]


def find_clients_by_marketing_code(
    db: Session, tenant_id: int, marketing_code: str
) -> list[Customer]:
    """Find all customers linked to a marketing code (Cosium tag)."""
    stmt = (
        select(Customer)
        .join(
            CosiumCustomerTag,
            (CosiumCustomerTag.customer_id == Customer.id)
            & (CosiumCustomerTag.tenant_id == Customer.tenant_id),
        )
        .where(
            Customer.tenant_id == tenant_id,
            CosiumCustomerTag.tag_code == marketing_code,
            Customer.deleted_at.is_(None),
        )
    )
    return list(db.scalars(stmt).all())


def create_batch(
    db: Session,
    tenant_id: int,
    marketing_code: str,
    label: str | None,
    user_id: int,
) -> BatchOperationResponse:
    """Create a batch operation for a marketing code."""
    clients = find_clients_by_marketing_code(db, tenant_id, marketing_code)

    batch = batch_operation_repo.create_batch(
        db,
        tenant_id=tenant_id,
        marketing_code=marketing_code,
        label=label,
        created_by=user_id,
        total_clients=len(clients),
    )

    for customer in clients:
        batch_operation_repo.create_item(
            db, batch_id=batch.id, customer_id=customer.id
        )

    db.commit()
    db.refresh(batch)

    logger.info(
        "batch_created",
        tenant_id=tenant_id,
        batch_id=batch.id,
        marketing_code=marketing_code,
        total_clients=len(clients),
    )

    return BatchOperationResponse.model_validate(batch)


def process_batch(
    db: Session, tenant_id: int, batch_id: int, user_id: int
) -> BatchOperationResponse:
    """Process all items in a batch -- consolidate + pre-control each client."""
    batch = batch_operation_repo.get_batch_by_id(db, batch_id, tenant_id)
    if not batch:
        raise NotFoundError("batch_operation", batch_id)

    items = batch_operation_repo.get_items_by_status(db, batch.id, "en_attente")

    stats = {"prets": 0, "incomplets": 0, "en_conflit": 0, "erreur": 0}

    for item in items:
        try:
            batch_operation_repo.update_item(db, item.id, status="en_cours")

            # Consolidate
            profile = consolidation_service.consolidate_client_for_pec(
                db, tenant_id, item.customer_id
            )

            # Calculate scores from profile
            score = profile.score_completude
            errors_count = sum(
                1 for a in (profile.alertes or []) if a.severity == "error"
            )
            warnings_count = sum(
                1 for a in (profile.alertes or []) if a.severity == "warning"
            )

            # Determine item status
            if errors_count > 0:
                item_status = "conflit" if warnings_count > 0 else "incomplet"
            elif score < 70:
                item_status = "incomplet"
            else:
                item_status = "pret"

            batch_operation_repo.update_item(
                db,
                item.id,
                status=item_status,
                completude_score=score,
                errors_count=errors_count,
                warnings_count=warnings_count,
                processed_at=datetime.now(UTC),
            )

            stats_key = {
                "pret": "prets",
                "incomplet": "incomplets",
                "conflit": "en_conflit",
            }.get(item_status, "incomplets")
            stats[stats_key] += 1

        except Exception as exc:
            logger.error(
                "batch_item_processing_error",
                batch_id=batch_id,
                customer_id=item.customer_id,
                error=str(exc),
            )
            batch_operation_repo.update_item(
                db,
                item.id,
                status="erreur",
                error_message=str(exc)[:500],
                processed_at=datetime.now(UTC),
            )
            stats["erreur"] += 1

    # Update batch stats
    batch_operation_repo.update_batch(
        db,
        batch.id,
        status="termine",
        clients_prets=stats["prets"],
        clients_incomplets=stats["incomplets"],
        clients_en_conflit=stats["en_conflit"],
        clients_erreur=stats["erreur"],
        completed_at=datetime.now(UTC),
    )
    db.commit()

    updated_batch = batch_operation_repo.get_batch_by_id(db, batch.id, tenant_id)
    logger.info(
        "batch_processed",
        tenant_id=tenant_id,
        batch_id=batch_id,
        stats=stats,
    )
    return BatchOperationResponse.model_validate(updated_batch)


def prepare_batch_pec(
    db: Session, tenant_id: int, batch_id: int, user_id: int
) -> BatchPecResult:
    """Create PEC preparations for all 'pret' items in a batch."""
    batch = batch_operation_repo.get_batch_by_id(db, batch_id, tenant_id)
    if not batch:
        raise NotFoundError("batch_operation", batch_id)

    pret_items = batch_operation_repo.get_items_by_status(db, batch.id, "pret")
    result = BatchPecResult()

    for item in pret_items:
        try:
            prep_resp = pec_preparation_service.prepare_pec(
                db,
                tenant_id=tenant_id,
                customer_id=item.customer_id,
                user_id=user_id,
            )
            batch_operation_repo.update_item(
                db, item.id, pec_preparation_id=prep_resp.id
            )
            result.prepared += 1
        except Exception as exc:
            logger.error(
                "batch_pec_preparation_error",
                batch_id=batch_id,
                customer_id=item.customer_id,
                error=str(exc),
            )
            batch_operation_repo.update_item(
                db,
                item.id,
                error_message=f"PEC: {str(exc)[:480]}",
            )
            result.errors += 1

    db.commit()
    logger.info(
        "batch_pec_prepared",
        tenant_id=tenant_id,
        batch_id=batch_id,
        prepared=result.prepared,
        errors=result.errors,
    )
    return result


def get_batch_summary(
    db: Session, tenant_id: int, batch_id: int
) -> BatchSummaryResponse:
    """Get batch overview with all items and their statuses."""
    batch = batch_operation_repo.get_batch_by_id(db, batch_id, tenant_id)
    if not batch:
        raise NotFoundError("batch_operation", batch_id)

    items = batch_operation_repo.get_items_by_batch(db, batch.id)

    # Fetch customer names
    customer_ids = [i.customer_id for i in items]
    names_map: dict[int, str] = {}
    if customer_ids:
        rows = db.execute(
            select(Customer.id, Customer.first_name, Customer.last_name).where(
                Customer.id.in_(customer_ids)
            )
        ).all()
        names_map = {r[0]: f"{r[1]} {r[2]}" for r in rows}

    item_responses = [
        BatchItemResponse(
            id=i.id,
            batch_id=i.batch_id,
            customer_id=i.customer_id,
            customer_name=names_map.get(i.customer_id),
            status=i.status,
            pec_preparation_id=i.pec_preparation_id,
            completude_score=i.completude_score,
            errors_count=i.errors_count,
            warnings_count=i.warnings_count,
            error_message=i.error_message,
            processed_at=i.processed_at,
        )
        for i in items
    ]

    return BatchSummaryResponse(
        batch=BatchOperationResponse.model_validate(batch),
        items=item_responses,
    )


def list_batches(
    db: Session, tenant_id: int, page: int = 1, page_size: int = 25
) -> dict:
    """List all batch operations for a tenant."""
    offset = (page - 1) * page_size
    batches = batch_operation_repo.list_batches(
        db, tenant_id, limit=page_size, offset=offset
    )
    total = batch_operation_repo.count_batches(db, tenant_id)
    return {
        "items": [BatchOperationResponse.model_validate(b) for b in batches],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
