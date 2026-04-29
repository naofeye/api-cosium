"""Web Push subscription management.

Le modele PushSubscription a une unique constraint `(user_id, endpoint)` :
un device (= un endpoint push) ne peut etre associe qu'a une seule
subscription par user. Quand le user change de tenant, on met a jour
`tenant_id` pour suivre le tenant actif — ainsi le device ne recoit que
les notifs du tenant courant.

Les fonctions filtrent aussi par tenant_id sur les operations destructives
(unsubscribe) pour la defense en profondeur : un user qui agit dans tenant
A ne peut pas toucher a une sub appartenant logiquement a tenant B.
"""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.push_subscription import PushSubscription

logger = get_logger("push_service")


def subscribe(
    db: Session,
    tenant_id: int,
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
) -> None:
    """Enregistre ou met a jour une subscription Web Push.

    Si une sub existe deja pour ce (user, endpoint), on met a jour les cles
    cryptographiques ET le `tenant_id` (pour suivre le tenant courant).
    """
    existing = db.scalars(
        select(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
    ).first()
    if existing:
        existing.tenant_id = tenant_id
        existing.p256dh_key = p256dh
        existing.auth_key = auth
    else:
        db.add(
            PushSubscription(
                tenant_id=tenant_id,
                user_id=user_id,
                endpoint=endpoint,
                p256dh_key=p256dh,
                auth_key=auth,
            )
        )
    db.commit()
    logger.info("push_subscribed", tenant_id=tenant_id, user_id=user_id)


def unsubscribe(db: Session, tenant_id: int, user_id: int, endpoint: str) -> None:
    """Supprime la subscription scopee au tenant courant (defense in depth).

    Si la sub appartient a un autre tenant (cas multi-tenant ou l'user a switch
    sans re-subscribe), l'operation est un no-op : pas d'erreur cote client.
    """
    db.execute(
        delete(PushSubscription).where(
            PushSubscription.user_id == user_id,
            PushSubscription.tenant_id == tenant_id,
            PushSubscription.endpoint == endpoint,
        )
    )
    db.commit()
    logger.info("push_unsubscribed", tenant_id=tenant_id, user_id=user_id)
