"""Batch PEC operation service — CRUD, orchestration, and listing.

Processing logic delegated to batch_processing_service.
Re-exports process_batch, prepare_batch_pec, get_batch_summary_enriched
for backward compatibility.
"""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.batch_operation import (
    BatchItemResponse,
    BatchOperationResponse,
    BatchSummaryResponse,
    MarketingCodeResponse,
)
from app.models.client import Customer
from app.models.cosium_reference import CosiumCustomerTag, CosiumTag
from app.repositories import batch_operation_repo

# Re-exports for backward compatibility
from app.services.batch_processing_service import (
    get_batch_summary_enriched,
    prepare_batch_pec,
    process_batch,
)

logger = get_logger("batch_operation_service")

# Make re-exports visible to static analysis
__all__ = [
    "get_available_marketing_codes",
    "find_clients_by_marketing_code",
    "get_batch_by_id",
    "create_batch",
    "process_batch",
    "prepare_batch_pec",
    "get_batch_summary",
    "get_batch_summary_enriched",
    "list_batches",
]


def _apply_date_filter(
    stmt,
    tenant_id: int,
    date_from: date | None,
    date_to: date | None,
):
    """Narrow a Customer query by last invoice date or customer creation date."""
    if not date_from and not date_to:
        return stmt

    from app.models.case import Case
    from app.models.facture import Facture

    inv_sq = (
        select(Case.customer_id)
        .join(Facture, Facture.case_id == Case.id)
        .where(Case.tenant_id == tenant_id)
    )
    if date_from:
        inv_sq = inv_sq.where(Facture.date_emission >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        inv_sq = inv_sq.where(Facture.date_emission <= datetime.combine(date_to, datetime.max.time()))
    inv_sq = inv_sq.distinct().subquery()

    cust_created = select(Customer.id).where(Customer.tenant_id == tenant_id)
    if date_from:
        cust_created = cust_created.where(Customer.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        cust_created = cust_created.where(Customer.created_at <= datetime.combine(date_to, datetime.max.time()))
    cust_created = cust_created.subquery()

    stmt = stmt.where(
        Customer.id.in_(select(inv_sq.c.customer_id))
        | Customer.id.in_(select(cust_created.c.id))
    )
    return stmt


def get_available_marketing_codes(
    db: Session,
    tenant_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[MarketingCodeResponse]:
    """List all marketing codes (tags) with client counts."""
    base_stmt = (
        select(
            CosiumCustomerTag.tag_code,
            func.count(CosiumCustomerTag.id).label("cnt"),
        )
        .join(
            Customer,
            (CosiumCustomerTag.customer_id == Customer.id)
            & (CosiumCustomerTag.tenant_id == Customer.tenant_id),
        )
        .where(
            CosiumCustomerTag.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
        )
    )

    if date_from or date_to:
        base_stmt = _apply_date_filter(base_stmt, tenant_id, date_from, date_to)

    base_stmt = base_stmt.group_by(CosiumCustomerTag.tag_code).order_by(
        func.count(CosiumCustomerTag.id).desc()
    )
    rows = db.execute(base_stmt).all()

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
    db: Session,
    tenant_id: int,
    marketing_code: str,
    date_from: date | None = None,
    date_to: date | None = None,
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

    if date_from or date_to:
        stmt = _apply_date_filter(stmt, tenant_id, date_from, date_to)

    return list(db.scalars(stmt).all())


def get_batch_by_id(
    db: Session, tenant_id: int, batch_id: int
) -> BatchOperationResponse:
    """Get a single batch by ID, raising NotFoundError if missing."""
    batch = batch_operation_repo.get_batch_by_id(db, batch_id, tenant_id)
    if not batch:
        raise NotFoundError("batch_operation", batch_id)
    return BatchOperationResponse.model_validate(batch)


def create_batch(
    db: Session,
    tenant_id: int,
    marketing_code: str,
    label: str | None,
    user_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> BatchOperationResponse:
    """Create a batch operation for a marketing code."""
    clients = find_clients_by_marketing_code(
        db, tenant_id, marketing_code, date_from, date_to
    )

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
            db, tenant_id=tenant_id, batch_id=batch.id, customer_id=customer.id
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


def get_batch_summary(
    db: Session, tenant_id: int, batch_id: int
) -> BatchSummaryResponse:
    """Get batch overview with all items and their statuses."""
    batch = batch_operation_repo.get_batch_by_id(db, batch_id, tenant_id)
    if not batch:
        raise NotFoundError("batch_operation", batch_id)

    items = batch_operation_repo.get_items_by_batch(db, batch.id)

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
