"""Endpoints CRUD webhooks + listing deliveries.

Tous endpoints scopes par tenant via TenantContext. Roles requis :
- admin/manager : creation, modification, suppression
- viewer : lecture seule (list, get)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.webhook import (
    ALLOWED_EVENT_TYPES,
    AllowedEventsResponse,
    DeliveryListResponse,
    DeliveryResponse,
    SubscriptionCreate,
    SubscriptionCreatedResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from app.repositories import webhook_repo
from app.services.webhook_service import generate_secret, mask_secret

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


def _to_response(sub) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=sub.id,
        tenant_id=sub.tenant_id,
        name=sub.name,
        url=sub.url,
        event_types=sub.event_types or [],
        is_active=sub.is_active,
        description=sub.description,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
        secret_masked=mask_secret(sub.secret),
    )


@router.get(
    "/events",
    response_model=AllowedEventsResponse,
    summary="Liste des event_types disponibles",
)
def list_allowed_events() -> AllowedEventsResponse:
    return AllowedEventsResponse(events=sorted(ALLOWED_EVENT_TYPES))


@router.get(
    "/subscriptions",
    response_model=list[SubscriptionResponse],
    summary="Liste les subscriptions du tenant",
)
def list_subscriptions(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[SubscriptionResponse]:
    rows = webhook_repo.list_subscriptions(db, ctx.tenant_id)
    return [_to_response(r) for r in rows]


@router.post(
    "/subscriptions",
    response_model=SubscriptionCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cree une subscription (genere un secret HMAC)",
    dependencies=[Depends(require_role("admin", "manager"))],
)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> SubscriptionCreatedResponse:
    secret = generate_secret()
    sub = webhook_repo.create_subscription(
        db,
        tenant_id=ctx.tenant_id,
        secret=secret,
        created_by_user_id=ctx.user_id,
        fields={
            "name": payload.name,
            "url": str(payload.url),
            "event_types": payload.event_types,
            "description": payload.description,
        },
    )
    db.commit()
    base = _to_response(sub)
    return SubscriptionCreatedResponse(**base.model_dump(), secret=secret)


@router.get(
    "/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Detail subscription",
)
def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> SubscriptionResponse:
    sub = webhook_repo.get_subscription(db, ctx.tenant_id, subscription_id)
    if sub is None:
        raise HTTPException(
            status_code=404, detail="Subscription introuvable"
        )
    return _to_response(sub)


@router.patch(
    "/subscriptions/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Modifie une subscription",
    dependencies=[Depends(require_role("admin", "manager"))],
)
def update_subscription(
    subscription_id: int,
    payload: SubscriptionUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> SubscriptionResponse:
    sub = webhook_repo.get_subscription(db, ctx.tenant_id, subscription_id)
    if sub is None:
        raise HTTPException(
            status_code=404, detail="Subscription introuvable"
        )
    fields = payload.model_dump(exclude_none=True)
    if "url" in fields:
        fields["url"] = str(fields["url"])
    sub = webhook_repo.update_subscription(db, sub, fields)
    db.commit()
    return _to_response(sub)


@router.delete(
    "/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Supprime une subscription (cascade deliveries)",
    dependencies=[Depends(require_role("admin", "manager"))],
)
def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    sub = webhook_repo.get_subscription(db, ctx.tenant_id, subscription_id)
    if sub is None:
        raise HTTPException(
            status_code=404, detail="Subscription introuvable"
        )
    webhook_repo.delete_subscription(db, sub)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/deliveries",
    response_model=DeliveryListResponse,
    summary="Liste les deliveries (audit / debug)",
)
def list_deliveries(
    subscription_id: int | None = Query(None),
    delivery_status: str | None = Query(None, alias="status"),
    event_type: str | None = Query(None, max_length=80),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> DeliveryListResponse:
    rows, total = webhook_repo.list_deliveries(
        db,
        ctx.tenant_id,
        subscription_id=subscription_id,
        status=delivery_status,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    return DeliveryListResponse(
        items=[DeliveryResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.get(
    "/deliveries/{delivery_id}",
    response_model=DeliveryResponse,
    summary="Detail delivery",
)
def get_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> DeliveryResponse:
    delivery = webhook_repo.get_delivery(db, ctx.tenant_id, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery introuvable")
    return DeliveryResponse.model_validate(delivery)


@router.post(
    "/deliveries/{delivery_id}/replay",
    response_model=DeliveryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Replay une delivery (status reset, re-enqueue)",
    dependencies=[Depends(require_role("admin", "manager"))],
)
def replay_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> DeliveryResponse:
    delivery = webhook_repo.get_delivery(db, ctx.tenant_id, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery introuvable")

    delivery = webhook_repo.update_delivery_status(
        db,
        delivery,
        status="pending",
        attempts=0,
        last_status_code=None,
        last_error=None,
        next_retry_at=None,
        delivered_at=None,
        duration_ms=None,
    )
    db.commit()
    # Lazy import : evite cycle au boot
    from app.tasks.webhook_tasks import deliver_webhook

    deliver_webhook.delay(delivery.id)
    return DeliveryResponse.model_validate(delivery)
