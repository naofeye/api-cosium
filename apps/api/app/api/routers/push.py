from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.models import User
from app.models.push_subscription import PushSubscription

router = APIRouter(prefix="/api/v1/push", tags=["push"])


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    endpoint: str
    keys: PushKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


@router.post(
    "/subscribe",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Enregistrer un abonnement push",
    description="Sauvegarde une souscription Web Push pour l'utilisateur connecte.",
)
def subscribe(
    payload: PushSubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> None:
    existing = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.user_id == current_user.id,
            PushSubscription.endpoint == payload.endpoint,
        )
        .first()
    )
    if existing:
        existing.p256dh_key = payload.keys.p256dh
        existing.auth_key = payload.keys.auth
    else:
        subscription = PushSubscription(
            tenant_id=tenant_ctx.tenant_id,
            user_id=current_user.id,
            endpoint=payload.endpoint,
            p256dh_key=payload.keys.p256dh,
            auth_key=payload.keys.auth,
        )
        db.add(subscription)
    db.commit()


@router.delete(
    "/unsubscribe",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un abonnement push",
    description="Supprime la souscription Web Push de l'utilisateur connecte pour l'endpoint donne.",
)
def unsubscribe(
    payload: PushUnsubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    db.query(PushSubscription).filter(
        PushSubscription.user_id == current_user.id,
        PushSubscription.endpoint == payload.endpoint,
    ).delete()
    db.commit()
