"""Batch PEC operation service — Journees entreprise bulk processing.

Orchestrates batch creation, consolidation, pre-control, and PEC preparation
for all clients linked to a marketing code (Cosium tag).
"""

from datetime import UTC, date, datetime

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
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_reference import CosiumCustomerTag, CosiumTag
from app.repositories import batch_operation_repo
from app.services import consolidation_service, pec_preparation_service

logger = get_logger("batch_operation_service")


def _apply_date_filter(
    stmt,
    tenant_id: int,
    date_from: date | None,
    date_to: date | None,
):
    """Narrow a Customer query by last invoice date or customer creation date.

    Factures link to customers through cases (facture.case_id -> case.customer_id).
    """
    if not date_from and not date_to:
        return stmt

    from app.models.case import Case
    from app.models.facture import Facture

    # Sub-query: customers with an invoice in the date range (via case)
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

    # Also include customers created in the date range (no invoice yet)
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
    """List all marketing codes (tags) with client counts.

    When date_from/date_to are provided, only count clients who had an invoice
    or were created within that date range.
    """
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
    db: Session,
    tenant_id: int,
    marketing_code: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[Customer]:
    """Find all customers linked to a marketing code (Cosium tag).

    When date_from/date_to are provided, only include clients who had an invoice
    or were created within that date range.
    """
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


def get_batch_summary_enriched(
    db: Session, tenant_id: int, batch_id: int
) -> dict:
    """Get batch summary with enriched customer data for Excel export.

    Returns a dict with 'batch' (BatchOperationResponse) and 'items' (list of dicts
    containing customer_name, phone, email, social_security_number, mutuelle_name,
    plus standard item fields).
    """
    batch = batch_operation_repo.get_batch_by_id(db, batch_id, tenant_id)
    if not batch:
        raise NotFoundError("batch_operation", batch_id)

    items = batch_operation_repo.get_items_by_batch(db, batch.id)

    # Fetch customer details
    customer_ids = [i.customer_id for i in items]
    customers_map: dict[int, dict] = {}
    if customer_ids:
        rows = db.execute(
            select(
                Customer.id,
                Customer.first_name,
                Customer.last_name,
                Customer.phone,
                Customer.email,
                Customer.social_security_number,
            ).where(Customer.id.in_(customer_ids))
        ).all()
        for cid, fn, ln, phone, email, ssn in rows:
            customers_map[cid] = {
                "name": f"{fn} {ln}".strip(),
                "phone": phone or "",
                "email": email or "",
                "social_security_number": ssn or "",
            }

    # Fetch mutuelle names
    mutuelle_map: dict[int, str] = {}
    if customer_ids:
        mut_rows = db.execute(
            select(
                ClientMutuelle.customer_id,
                ClientMutuelle.mutuelle_name,
            )
            .where(
                ClientMutuelle.customer_id.in_(customer_ids),
                ClientMutuelle.tenant_id == tenant_id,
                ClientMutuelle.active.is_(True),
            )
            .order_by(ClientMutuelle.customer_id)
        ).all()
        for cust_id, mut_name in mut_rows:
            if cust_id not in mutuelle_map:
                mutuelle_map[cust_id] = mut_name

    enriched_items = []
    for i in items:
        cust = customers_map.get(i.customer_id, {})
        enriched_items.append({
            "id": i.id,
            "batch_id": i.batch_id,
            "customer_id": i.customer_id,
            "customer_name": cust.get("name", f"Client #{i.customer_id}"),
            "phone": cust.get("phone", ""),
            "email": cust.get("email", ""),
            "social_security_number": cust.get("social_security_number", ""),
            "mutuelle_name": mutuelle_map.get(i.customer_id, ""),
            "status": i.status,
            "completude_score": i.completude_score,
            "errors_count": i.errors_count,
            "warnings_count": i.warnings_count,
            "pec_preparation_id": i.pec_preparation_id,
            "error_message": i.error_message,
            "processed_at": (
                i.processed_at.strftime("%d/%m/%Y %H:%M") if i.processed_at else ""
            ),
        })

    return {
        "batch": BatchOperationResponse.model_validate(batch),
        "items": enriched_items,
    }


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
