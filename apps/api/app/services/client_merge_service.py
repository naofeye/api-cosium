"""Client merge/deduplication service -- find duplicates and merge clients."""

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.clients import (
    ClientMergeResult,
    ClientResponse,
    DuplicateGroup,
)
from app.models.client import Customer
from app.repositories import client_repo
from app.services import audit_service

logger = get_logger("client_merge_service")


def find_duplicates(db: Session, tenant_id: int) -> list[DuplicateGroup]:
    """Find potential duplicate clients by case-insensitive name matching."""
    dupes = db.execute(
        select(
            func.lower(Customer.last_name),
            func.lower(Customer.first_name),
            func.count().label("cnt"),
        )
        .where(Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None))
        .group_by(func.lower(Customer.last_name), func.lower(Customer.first_name))
        .having(func.count() > 1)
    ).all()
    if not dupes:
        return []
    # Optimisation N+1 : 1 seule query qui charge tous les clients dans tous
    # les groupes de doublons, puis on group_by en Python. Avant : 1 query par
    # groupe, soit 200+ round-trips si beaucoup de doublons.
    keys = {(last, first) for last, first, _ in dupes}
    all_clients = db.scalars(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
            tuple_(func.lower(Customer.last_name), func.lower(Customer.first_name)).in_(
                list(keys)
            ),
        )
    ).all()

    grouped: dict[tuple[str, str], list] = {}
    for c in all_clients:
        k = ((c.last_name or "").lower(), (c.first_name or "").lower())
        grouped.setdefault(k, []).append(c)

    results: list[DuplicateGroup] = []
    for last, first, cnt in dupes:
        clients = grouped.get((last, first), [])
        results.append(
            DuplicateGroup(
                name=f"{first} {last}",
                count=cnt,
                clients=[ClientResponse.model_validate(c) for c in clients],
            )
        )
    return results


def merge_clients(
    db: Session, tenant_id: int, keep_id: int, merge_id: int, user_id: int
) -> ClientMergeResult:
    """Merge merge_id into keep_id. Transfer all related data, then soft-delete merge_id."""
    from app.models.case import Case
    from app.models.client_mutuelle import ClientMutuelle
    from app.models.cosium_data import (
        CosiumDocument,
        CosiumInvoice,
        CosiumPayment,
        CosiumPrescription,
    )
    from app.models.interaction import Interaction
    from app.models.marketing import MarketingConsent, MessageLog, SegmentMembership
    from app.models.pec import PecRequest
    from app.models.pec_preparation import PecPreparation

    if keep_id == merge_id:
        raise BusinessError("Impossible de fusionner un client avec lui-meme", code="MERGE_SAME_CLIENT")

    keep_client = client_repo.get_by_id_active(db, client_id=keep_id, tenant_id=tenant_id)
    if not keep_client:
        raise NotFoundError("client", keep_id)

    merge_client = client_repo.get_by_id_active(db, client_id=merge_id, tenant_id=tenant_id)
    if not merge_client:
        raise NotFoundError("client", merge_id)

    # Fill empty fields on keep_client from merge_client
    fillable_fields = [
        "phone", "email", "birth_date", "address", "street_number",
        "street_name", "city", "postal_code", "social_security_number",
        "optician_name", "ophthalmologist_id", "notes", "cosium_id",
        "customer_number", "mobile_phone_country", "site_id",
    ]
    fields_filled: list[str] = []
    for field in fillable_fields:
        keep_val = getattr(keep_client, field, None)
        merge_val = getattr(merge_client, field, None)
        if not keep_val and merge_val:
            setattr(keep_client, field, merge_val)
            fields_filled.append(field)

    # Count cases BEFORE transfer
    cases_transferred = db.execute(
        select(func.count()).select_from(Case).where(
            Case.customer_id == merge_id, Case.tenant_id == tenant_id
        )
    ).scalar_one()

    # Count PEC records BEFORE transferring cases (bug fix: must count while
    # cases still belong to merge_id, not after they have been moved to keep_id)
    pec_transferred = 0
    if cases_transferred:
        pec_transferred = db.execute(
            select(func.count()).select_from(PecRequest).where(
                PecRequest.case_id.in_(
                    select(Case.id).where(
                        Case.customer_id == merge_id, Case.tenant_id == tenant_id
                    )
                ),
                PecRequest.tenant_id == tenant_id,
            )
        ).scalar_one()

    # Transfer cases
    if cases_transferred:
        db.execute(
            Case.__table__.update()
            .where(Case.customer_id == merge_id, Case.tenant_id == tenant_id)
            .values(customer_id=keep_id)
        )

    # Transfer interactions
    interactions_transferred = db.execute(
        select(func.count()).select_from(Interaction).where(
            Interaction.client_id == merge_id, Interaction.tenant_id == tenant_id
        )
    ).scalar_one()
    if interactions_transferred:
        db.execute(
            Interaction.__table__.update()
            .where(Interaction.client_id == merge_id, Interaction.tenant_id == tenant_id)
            .values(client_id=keep_id)
        )

    # Transfer PEC preparations
    db.execute(
        PecPreparation.__table__.update()
        .where(PecPreparation.customer_id == merge_id, PecPreparation.tenant_id == tenant_id)
        .values(customer_id=keep_id)
    )

    # Transfer client mutuelles
    db.execute(
        ClientMutuelle.__table__.update()
        .where(ClientMutuelle.customer_id == merge_id, ClientMutuelle.tenant_id == tenant_id)
        .values(customer_id=keep_id)
    )

    # Transfer marketing data
    marketing_transferred = 0
    for model in [MarketingConsent, SegmentMembership, MessageLog]:
        cnt = db.execute(
            select(func.count()).select_from(model).where(
                model.client_id == merge_id, model.tenant_id == tenant_id
            )
        ).scalar_one()
        marketing_transferred += cnt
        if cnt:
            db.execute(
                model.__table__.update()
                .where(model.client_id == merge_id, model.tenant_id == tenant_id)
                .values(client_id=keep_id)
            )

    # Transfer cosium data references
    cosium_transferred = 0
    for cosium_model in [CosiumInvoice, CosiumPayment, CosiumDocument, CosiumPrescription]:
        if hasattr(cosium_model, "customer_id") and hasattr(cosium_model, "tenant_id"):
            cnt = db.execute(
                select(func.count()).select_from(cosium_model).where(
                    cosium_model.customer_id == merge_id, cosium_model.tenant_id == tenant_id
                )
            ).scalar_one()
            cosium_transferred += cnt
            if cnt:
                db.execute(
                    cosium_model.__table__.update()
                    .where(cosium_model.customer_id == merge_id, cosium_model.tenant_id == tenant_id)
                    .values(customer_id=keep_id)
                )

    # Soft-delete merged client
    client_repo.delete(db, merge_client)

    db.commit()
    db.refresh(keep_client)

    audit_service.log_action(
        db,
        tenant_id,
        user_id,
        "merge",
        "client",
        keep_id,
        new_value={
            "merged_from": merge_id,
            "cases_transferred": cases_transferred,
            "interactions_transferred": interactions_transferred,
            "pec_transferred": pec_transferred,
            "marketing_transferred": marketing_transferred,
            "fields_filled": fields_filled,
        },
    )
    logger.info(
        "clients_merged",
        tenant_id=tenant_id,
        keep_id=keep_id,
        merge_id=merge_id,
        user_id=user_id,
    )

    return ClientMergeResult(
        kept_client=ClientResponse.model_validate(keep_client),
        cases_transferred=cases_transferred,
        interactions_transferred=interactions_transferred,
        pec_transferred=pec_transferred,
        marketing_transferred=marketing_transferred,
        cosium_data_transferred=cosium_transferred,
        fields_filled=fields_filled,
        merged_client_deleted=True,
    )
