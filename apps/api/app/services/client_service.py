"""Client service -- CRUD operations, quick view, avatar handling.

Import/file and merge/deduplication logic are in dedicated sub-modules.
All public functions are re-exported here so existing callers continue to work.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.clients import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.models.client import Customer
from app.repositories import client_repo
from app.services import audit_service, webhook_emit_helpers
from app.services.client_completeness_service import calculate_client_completeness

# Re-export quick view and avatar functions for backward compatibility
from app.services.client_extras_service import (  # noqa: F401
    get_avatar_url,
    get_client_quick,
    upload_avatar,
)

# Re-export extracted functions so callers using
# ``from app.services import client_service; client_service.merge_clients(...)``
# keep working without changes.
from app.services.client_import_service import (  # noqa: F401
    generate_import_template,
    import_from_file,
)
from app.services.client_merge_service import (  # noqa: F401
    find_duplicates,
    merge_clients,
)

logger = get_logger("client_service")


# ---------------------------------------------------------------------------
# Search / Read
# ---------------------------------------------------------------------------

def search_clients(
    db: Session,
    tenant_id: int,
    query: str,
    page: int,
    page_size: int,
    include_deleted: bool = False,
) -> ClientListResponse:
    items, total = client_repo.search(db, tenant_id, query, page, page_size, include_deleted=include_deleted)
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    client_responses: list[ClientResponse] = []
    for c in items:
        resp = ClientResponse.model_validate(c)
        resp.completeness = calculate_client_completeness(db, c, tenant_id)
        client_responses.append(resp)
    return ClientListResponse(
        items=client_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_client(db: Session, tenant_id: int, client_id: int) -> ClientResponse:
    customer = client_repo.get_by_id_active(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    resp = ClientResponse.model_validate(customer)
    resp.completeness = calculate_client_completeness(db, customer, tenant_id)
    return resp


# ---------------------------------------------------------------------------
# Create / Update / Delete / Restore
# ---------------------------------------------------------------------------

def create_client(db: Session, tenant_id: int, payload: ClientCreate, user_id: int) -> ClientResponse:
    customer = client_repo.create(db, tenant_id=tenant_id, **payload.model_dump(exclude_none=True))
    audit_service.log_action(
        db,
        tenant_id,
        user_id,
        "create",
        "client",
        customer.id,
        new_value=payload.model_dump(exclude_none=True),
    )
    logger.info("client_created", tenant_id=tenant_id, client_id=customer.id, user_id=user_id)
    response = ClientResponse.model_validate(customer)
    webhook_emit_helpers.emit_client_created(db, tenant_id, response)
    return response


def update_client(db: Session, tenant_id: int, client_id: int, payload: ClientUpdate, user_id: int) -> ClientResponse:
    customer = client_repo.get_by_id_active(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    updated = client_repo.update(db, customer, **payload.model_dump(exclude_unset=True))
    audit_service.log_action(
        db,
        tenant_id,
        user_id,
        "update",
        "client",
        client_id,
        new_value=payload.model_dump(exclude_unset=True),
    )
    logger.info("client_updated", tenant_id=tenant_id, client_id=client_id, user_id=user_id)
    response = ClientResponse.model_validate(updated)
    webhook_emit_helpers.emit_client_updated(db, tenant_id, response)
    return response


def delete_client(db: Session, tenant_id: int, client_id: int, user_id: int, force: bool = False) -> None:
    from app.models import Case, Devis, Document, Facture, Payment, PecRequest

    customer = client_repo.get_by_id_active(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)

    if not force:
        # Count active related entities
        active_cases = db.scalar(
            select(func.count(Case.id)).where(
                Case.customer_id == client_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
                Case.status != "archived",
            )
        ) or 0
        documents = db.scalar(
            select(func.count(Document.id))
            .join(Case, Case.id == Document.case_id)
            .where(Case.customer_id == client_id, Document.tenant_id == tenant_id)
        ) or 0
        payments = db.scalar(
            select(func.count(Payment.id))
            .join(Case, Case.id == Payment.case_id)
            .where(Case.customer_id == client_id, Payment.tenant_id == tenant_id)
        ) or 0
        devis_count = db.scalar(
            select(func.count(Devis.id))
            .join(Case, Case.id == Devis.case_id)
            .where(Case.customer_id == client_id, Devis.tenant_id == tenant_id)
        ) or 0
        factures_count = db.scalar(
            select(func.count(Facture.id))
            .join(Case, Case.id == Facture.case_id)
            .where(Case.customer_id == client_id, Facture.tenant_id == tenant_id)
        ) or 0
        pec_count = db.scalar(
            select(func.count(PecRequest.id))
            .join(Case, Case.id == PecRequest.case_id)
            .where(Case.customer_id == client_id, PecRequest.tenant_id == tenant_id)
        ) or 0

        if active_cases > 0:
            raise BusinessError(
                "CLIENT_HAS_ACTIVE_ENTITIES",
                f"Impossible de supprimer ce client : {active_cases} dossiers actifs, "
                f"{documents} documents, {payments} paiements, {devis_count} devis, "
                f"{factures_count} factures, {pec_count} demandes PEC. "
                f"Archivez les dossiers d'abord ou utilisez force=true.",
            )

    client_repo.delete(db, customer)
    audit_service.log_action(
        db, tenant_id, user_id, "delete", "client", client_id,
        new_value={"force": force},
    )
    logger.info("client_deleted", tenant_id=tenant_id, client_id=client_id, user_id=user_id, force=force)


def restore_client(db: Session, tenant_id: int, client_id: int, user_id: int) -> ClientResponse:
    customer = client_repo.get_by_id_including_deleted(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    if customer.deleted_at is None:
        raise NotFoundError("client", client_id)

    # Check for duplicate email before restoring
    if customer.email:
        conflict = db.scalars(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.email == customer.email,
                Customer.deleted_at.is_(None),
                Customer.id != customer.id,
            )
        ).first()
        if conflict:
            raise BusinessError(
                "DUPLICATE_EMAIL",
                f"Un client actif avec l'email {customer.email} existe deja",
            )

    restored = client_repo.restore(db, customer)
    audit_service.log_action(db, tenant_id, user_id, "restore", "client", client_id)
    logger.info("client_restored", tenant_id=tenant_id, client_id=client_id, user_id=user_id)
    return ClientResponse.model_validate(restored)


