"""Batch processing logic — per-client consolidation, PEC preparation, enriched export.

Extracted from batch_operation_service to keep each file under 300 lines.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.batch_operation import (
    BatchOperationResponse,
    BatchPecResult,
)
from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle
from app.repositories import batch_operation_repo
from app.services import consolidation_service, pec_preparation_service

logger = get_logger("batch_processing_service")


def process_batch(
    db: Session, tenant_id: int, batch_id: int, user_id: int
) -> BatchOperationResponse:
    """Process all items in a batch -- consolidate + pre-control each client."""
    from app.core.exceptions import NotFoundError

    batch = batch_operation_repo.get_batch_by_id(db, batch_id, tenant_id)
    if not batch:
        raise NotFoundError("batch_operation", batch_id)

    items = batch_operation_repo.get_items_by_status(db, batch.id, "en_attente")

    stats = {"prets": 0, "incomplets": 0, "en_conflit": 0, "erreur": 0}

    total_items = len(items)
    for idx, item in enumerate(items, start=1):
        try:
            batch_operation_repo.update_item(db, item.id, status="en_cours")

            profile = consolidation_service.consolidate_client_for_pec(
                db, tenant_id, item.customer_id
            )

            score = profile.score_completude
            errors_count = sum(
                1 for a in (profile.alertes or []) if a.severity == "error"
            )
            warnings_count = sum(
                1 for a in (profile.alertes or []) if a.severity == "warning"
            )

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

            # Update batch progress every 100 items so the frontend can poll
            if idx % 100 == 0 or idx == total_items:
                batch_operation_repo.update_batch(
                    db,
                    batch.id,
                    status="en_cours",
                    clients_prets=stats["prets"],
                    clients_incomplets=stats["incomplets"],
                    clients_en_conflit=stats["en_conflit"],
                    clients_erreur=stats["erreur"],
                )
                db.commit()
                logger.debug(
                    "batch_progress_update",
                    batch_id=batch_id,
                    processed=idx,
                    total=total_items,
                )

        except (SQLAlchemyError, ValueError, KeyError) as exc:
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

            # Update batch progress every 100 items (also after errors)
            if idx % 100 == 0 or idx == total_items:
                batch_operation_repo.update_batch(
                    db,
                    batch.id,
                    status="en_cours",
                    clients_prets=stats["prets"],
                    clients_incomplets=stats["incomplets"],
                    clients_en_conflit=stats["en_conflit"],
                    clients_erreur=stats["erreur"],
                )
                db.commit()

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
    from app.core.exceptions import NotFoundError

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
        except (SQLAlchemyError, ValueError, KeyError) as exc:
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


def get_batch_summary_enriched(
    db: Session, tenant_id: int, batch_id: int
) -> dict:
    """Get batch summary with enriched customer data for Excel export.

    Returns a dict with 'batch' (BatchOperationResponse) and 'items' (list of dicts
    containing customer_name, phone, email, social_security_number, mutuelle_name,
    plus standard item fields).
    """
    from app.core.exceptions import NotFoundError

    batch = batch_operation_repo.get_batch_by_id(db, batch_id, tenant_id)
    if not batch:
        raise NotFoundError("batch_operation", batch_id)

    items = batch_operation_repo.get_items_by_batch(db, batch.id)

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
