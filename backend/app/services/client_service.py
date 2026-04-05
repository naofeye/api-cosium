import csv
import io

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.clients import (
    ClientCreate,
    ClientImportResult,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
    DuplicateGroup,
)
from app.models.client import Customer
from app.repositories import client_repo
from app.services import audit_service

logger = get_logger("client_service")


def search_clients(
    db: Session,
    tenant_id: int,
    query: str,
    page: int,
    page_size: int,
    include_deleted: bool = False,
) -> ClientListResponse:
    items, total = client_repo.search(db, tenant_id, query, page, page_size, include_deleted=include_deleted)
    return ClientListResponse(
        items=[ClientResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_client(db: Session, tenant_id: int, client_id: int) -> ClientResponse:
    customer = client_repo.get_by_id_active(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    return ClientResponse.model_validate(customer)


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
    return ClientResponse.model_validate(customer)


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
    return ClientResponse.model_validate(updated)


def delete_client(db: Session, tenant_id: int, client_id: int, user_id: int) -> None:
    customer = client_repo.get_by_id_active(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    client_repo.delete(db, customer)
    audit_service.log_action(db, tenant_id, user_id, "delete", "client", client_id)
    logger.info("client_deleted", tenant_id=tenant_id, client_id=client_id, user_id=user_id)


def restore_client(db: Session, tenant_id: int, client_id: int, user_id: int) -> ClientResponse:
    customer = client_repo.get_by_id(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    if customer.deleted_at is None:
        raise NotFoundError("client", client_id)
    restored = client_repo.restore(db, customer)
    audit_service.log_action(db, tenant_id, user_id, "restore", "client", client_id)
    logger.info("client_restored", tenant_id=tenant_id, client_id=client_id, user_id=user_id)
    return ClientResponse.model_validate(restored)


def import_from_csv(db: Session, tenant_id: int, file_content: bytes, user_id: int) -> ClientImportResult:
    """Import clients from a CSV file (semicolon-delimited, UTF-8/BOM)."""
    reader = csv.DictReader(io.StringIO(file_content.decode("utf-8-sig")), delimiter=";")
    imported = 0
    skipped = 0
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):
        try:
            last_name = row.get("nom", "").strip()
            first_name = row.get("prenom", "").strip()
            if not last_name:
                skipped += 1
                continue
            customer = Customer(
                tenant_id=tenant_id,
                first_name=first_name,
                last_name=last_name,
                email=row.get("email", "").strip() or None,
                phone=row.get("telephone", "").strip() or None,
                address=row.get("adresse", "").strip() or None,
                city=row.get("ville", "").strip() or None,
                postal_code=row.get("code_postal", "").strip() or None,
            )
            db.add(customer)
            imported += 1
        except Exception as e:
            errors.append(f"Ligne {i}: {str(e)}")
            skipped += 1
    db.commit()
    audit_service.log_action(
        db,
        tenant_id,
        user_id,
        "create",
        "client_import",
        0,
        new_value={"imported": imported, "skipped": skipped},
    )
    logger.info("csv_import_completed", tenant_id=tenant_id, imported=imported, skipped=skipped)
    return ClientImportResult(imported=imported, skipped=skipped, errors=errors[:10])


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
    results: list[DuplicateGroup] = []
    for last, first, cnt in dupes:
        clients = db.scalars(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                func.lower(Customer.last_name) == last,
                func.lower(Customer.first_name) == first,
                Customer.deleted_at.is_(None),
            )
        ).all()
        results.append(
            DuplicateGroup(
                name=f"{first} {last}",
                count=cnt,
                clients=[ClientResponse.model_validate(c) for c in clients],
            )
        )
    return results


def upload_avatar(
    db: Session, tenant_id: int, client_id: int, file_data: bytes, content_type: str, user_id: int
) -> str:
    """Upload a client avatar to MinIO and store the URL."""
    import uuid

    from app.core.config import settings
    from app.integrations.storage import storage

    customer = client_repo.get_by_id_active(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)

    ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "png"
    storage_key = f"tenants/{tenant_id}/avatars/{client_id}/{uuid.uuid4().hex}.{ext}"

    storage.upload_file(
        bucket=settings.s3_bucket,
        key=storage_key,
        file_data=file_data,
        content_type=content_type,
    )

    avatar_url = f"/api/v1/clients/{client_id}/avatar"
    customer.avatar_url = storage_key
    db.commit()
    db.refresh(customer)

    audit_service.log_action(
        db,
        tenant_id,
        user_id,
        "update",
        "client_avatar",
        client_id,
        new_value={"avatar_key": storage_key},
    )
    logger.info("avatar_uploaded", tenant_id=tenant_id, client_id=client_id)
    return avatar_url


def get_avatar_url(db: Session, tenant_id: int, client_id: int) -> str:
    """Get the MinIO presigned URL for a client avatar."""
    from app.core.config import settings
    from app.integrations.storage import storage

    customer = client_repo.get_by_id_active(db, client_id=client_id, tenant_id=tenant_id)
    if not customer or not customer.avatar_url:
        raise NotFoundError("avatar", client_id)

    url = storage.get_download_url(
        bucket=settings.s3_bucket,
        key=customer.avatar_url,
        expires=3600,
    )
    return url
