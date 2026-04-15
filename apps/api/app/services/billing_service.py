"""Service de facturation — gestion des abonnements Stripe."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.integrations import stripe_client
from app.models import Organization, Tenant

logger = get_logger("billing_service")

PLAN_PRICE_MAP: dict[str, str] = {
    "solo": settings.stripe_price_solo,
    "reseau": settings.stripe_price_reseau,
    "ia_pro": settings.stripe_price_ia_pro,
}


def _get_tenant(db: Session, tenant_id: int) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant is None:
        raise NotFoundError("Tenant", tenant_id)
    return tenant


def _get_organization(db: Session, organization_id: int) -> Organization:
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org is None:
        raise NotFoundError("Organization", organization_id)
    return org


def initiate_checkout(db: Session, tenant_id: int, plan: str) -> str:
    """Crée un customer Stripe si nécessaire, puis une session Checkout. Retourne l'URL."""
    if plan not in PLAN_PRICE_MAP:
        raise BusinessError(f"Plan inconnu : {plan}", code="invalid_plan")

    price_id = PLAN_PRICE_MAP[plan]
    if not price_id:
        raise BusinessError(f"Prix Stripe non configuré pour le plan : {plan}", code="missing_price")

    tenant = _get_tenant(db, tenant_id)
    org = _get_organization(db, tenant.organization_id)

    if not tenant.stripe_customer_id:
        customer_id = stripe_client.create_customer(
            email=org.contact_email or f"tenant-{tenant_id}@optiflow.com",
            name=tenant.name,
            tenant_id=tenant_id,
        )
        tenant.stripe_customer_id = customer_id
        db.commit()
        logger.info("stripe_customer_linked", tenant_id=tenant_id, customer_id=customer_id)

    checkout_url = stripe_client.create_checkout_session(
        customer_id=tenant.stripe_customer_id,
        price_id=price_id,
        tenant_id=tenant_id,
        success_url=f"{settings.cors_origins.split(',')[0].strip()}/billing/success",
        cancel_url=f"{settings.cors_origins.split(',')[0].strip()}/billing/cancel",
    )

    logger.info("checkout_initiated", tenant_id=tenant_id, plan=plan)
    return checkout_url


def handle_webhook(db: Session, event: object) -> None:
    """Traite un événement webhook Stripe et met à jour le statut d'abonnement."""
    event_type: str = event.type  # type: ignore[attr-defined]
    data: dict = event.data.object  # type: ignore[attr-defined]

    logger.info("stripe_webhook_received", event_type=event_type)

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(db, data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(db, data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(db, data)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(db, data)
    else:
        logger.info("stripe_webhook_ignored", event_type=event_type)


def _handle_checkout_completed(db: Session, data: dict) -> None:
    tenant_id_str = data.get("metadata", {}).get("tenant_id")
    subscription_id = data.get("subscription")
    if not tenant_id_str or not subscription_id:
        logger.warning("checkout_completed_missing_data", data_keys=list(data.keys()))
        return

    tenant_id = int(tenant_id_str)
    tenant = _get_tenant(db, tenant_id)
    tenant.stripe_subscription_id = subscription_id
    tenant.subscription_status = "active"

    org = _get_organization(db, tenant.organization_id)
    org.plan = data.get("metadata", {}).get("plan", org.plan)

    db.commit()
    logger.info("subscription_activated", tenant_id=tenant_id, subscription_id=subscription_id)


def _handle_payment_failed(db: Session, data: dict) -> None:
    customer_id = data.get("customer")
    if not customer_id:
        return
    tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
    if tenant is None:
        logger.warning("payment_failed_tenant_not_found", customer_id=customer_id)
        return

    tenant.subscription_status = "past_due"
    db.commit()
    logger.warning("subscription_past_due", tenant_id=tenant.id, customer_id=customer_id)


def _handle_subscription_deleted(db: Session, data: dict) -> None:
    subscription_id = data.get("id")
    if not subscription_id:
        return
    tenant = db.query(Tenant).filter(Tenant.stripe_subscription_id == subscription_id).first()
    if tenant is None:
        logger.warning("subscription_deleted_tenant_not_found", subscription_id=subscription_id)
        return

    tenant.subscription_status = "canceled"
    db.commit()
    logger.info("subscription_canceled", tenant_id=tenant.id, subscription_id=subscription_id)


def _handle_subscription_updated(db: Session, data: dict) -> None:
    subscription_id = data.get("id")
    status = data.get("status")
    if not subscription_id or not status:
        return
    tenant = db.query(Tenant).filter(Tenant.stripe_subscription_id == subscription_id).first()
    if tenant is None:
        logger.warning("subscription_updated_tenant_not_found", subscription_id=subscription_id)
        return

    tenant.subscription_status = status
    db.commit()
    logger.info("subscription_status_updated", tenant_id=tenant.id, status=status)


def check_access(db: Session, tenant_id: int) -> bool:
    """Vérifie si le tenant a un accès actif (trial valide ou abonnement actif)."""
    tenant = _get_tenant(db, tenant_id)

    if tenant.subscription_status == "active":
        return True

    if tenant.subscription_status == "trial":
        org = _get_organization(db, tenant.organization_id)
        if org.trial_ends_at:
            ends_at = org.trial_ends_at
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=UTC)
            if ends_at > datetime.now(UTC):
                return True
        return False

    return False


def get_billing_info(db: Session, tenant_id: int) -> dict:
    """Retourne les informations de facturation du tenant."""
    tenant = _get_tenant(db, tenant_id)
    org = _get_organization(db, tenant.organization_id)

    trial_days_remaining: int | None = None
    if tenant.subscription_status == "trial" and org.trial_ends_at:
        ends_at = org.trial_ends_at
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=UTC)
        delta = ends_at - datetime.now(UTC)
        trial_days_remaining = max(0, delta.days)

    return {
        "plan": org.plan,
        "status": tenant.subscription_status,
        "trial_days_remaining": trial_days_remaining,
        "stripe_customer_id": tenant.stripe_customer_id,
    }


def cancel_subscription_for_tenant(db: Session, tenant_id: int) -> None:
    """Annule l'abonnement Stripe du tenant (fin de période)."""
    tenant = _get_tenant(db, tenant_id)

    if not tenant.stripe_subscription_id:
        raise BusinessError("Aucun abonnement actif à annuler", code="no_subscription")

    stripe_client.cancel_subscription(subscription_id=tenant.stripe_subscription_id)
    logger.info("subscription_cancellation_requested", tenant_id=tenant_id)
