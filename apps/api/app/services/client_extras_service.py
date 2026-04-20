"""Client extras -- quick view, avatar handling.

Extracted from client_service.py to keep files under 300 lines.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.repositories import client_repo
from app.services import audit_service

logger = get_logger("client_extras_service")


def get_client_quick(db: Session, tenant_id: int, client_id: int) -> dict:
    """Return a lightweight quick-view of a client (for hover cards)."""
    from app.core.redis_cache import cache_get, cache_set
    from app.models import Case, Facture
    from app.models.cosium_data import CosiumPrescription

    cache_key = f"client:quick:{tenant_id}:{client_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    customer = client_repo.get_by_id_active(db, client_id=client_id, tenant_id=tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)

    # CA total via factures
    ca_total = float(
        db.scalar(
            select(func.coalesce(func.sum(Facture.montant_ttc), 0))
            .join(Case, Case.id == Facture.case_id)
            .where(Case.customer_id == customer.id, Facture.tenant_id == tenant_id)
        ) or 0
    )

    # Latest prescription for correction info
    latest_rx = db.scalar(
        select(CosiumPrescription)
        .where(
            CosiumPrescription.customer_id == customer.id,
            CosiumPrescription.tenant_id == tenant_id,
        )
        .order_by(CosiumPrescription.prescription_date.desc())
        .limit(1)
    )

    correction_od = None
    correction_og = None
    if latest_rx:
        if latest_rx.sphere_right is not None:
            sign = "+" if latest_rx.sphere_right >= 0 else ""
            correction_od = f"{sign}{latest_rx.sphere_right:.2f}"
        if latest_rx.sphere_left is not None:
            sign = "+" if latest_rx.sphere_left >= 0 else ""
            correction_og = f"{sign}{latest_rx.sphere_left:.2f}"

    # Last visit from cosium calendar events
    from app.models.cosium_reference import CosiumCalendarEvent

    last_event = None
    if customer.cosium_id:
        last_event = db.scalar(
            select(CosiumCalendarEvent.start_date)
            .where(
                CosiumCalendarEvent.customer_number == customer.cosium_id,
                CosiumCalendarEvent.tenant_id == tenant_id,
            )
            .order_by(CosiumCalendarEvent.start_date.desc())
            .limit(1)
        )
    last_visit = None
    if last_event:
        try:
            from datetime import datetime
            if isinstance(last_event, str):
                dt = datetime.fromisoformat(last_event.replace("Z", "+00:00"))
                last_visit = dt.strftime("%d/%m/%Y")
            elif isinstance(last_event, datetime):
                last_visit = last_event.strftime("%d/%m/%Y")
            else:
                last_visit = str(last_event)
        except (ValueError, TypeError):
            last_visit = str(last_event)

    result = {
        "id": customer.id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "phone": customer.phone,
        "email": customer.email,
        "correction_od": correction_od,
        "correction_og": correction_og,
        "last_visit": last_visit,
        "ca_total": round(ca_total, 2),
    }
    cache_set(cache_key, result, ttl=120)
    return result


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
