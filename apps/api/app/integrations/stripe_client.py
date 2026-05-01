"""Client Stripe — encapsule toutes les interactions avec l'API Stripe."""

import stripe

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.core.logging import get_logger

logger = get_logger("stripe_client")


def _configure() -> None:
    stripe.api_key = settings.stripe_secret_key


def create_customer(email: str, name: str, tenant_id: int) -> str:
    """Crée un customer Stripe, retourne l'ID."""
    _configure()
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={"tenant_id": str(tenant_id)},
        )
        logger.info("stripe_customer_created", tenant_id=tenant_id, stripe_customer_id=customer.id)
        return customer.id
    except stripe.StripeError as exc:
        logger.error("stripe_customer_create_failed", tenant_id=tenant_id, error=str(exc))
        raise BusinessError(f"Erreur Stripe lors de la creation du client : {exc}", code="STRIPE_ERROR") from exc


def create_checkout_session(
    customer_id: str,
    price_id: str,
    tenant_id: int,
    success_url: str,
    cancel_url: str,
    plan: str | None = None,
) -> str:
    """Crée une session Checkout Stripe, retourne l'URL."""
    _configure()
    metadata: dict[str, str] = {"tenant_id": str(tenant_id)}
    if plan:
        # Le webhook checkout.session.completed lit metadata.plan pour propager
        # le plan choisi sur l'organization. Sans ca, l'org reste sur son ancien plan.
        metadata["plan"] = plan
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )
        logger.info("stripe_checkout_session_created", tenant_id=tenant_id, session_id=session.id)
        return session.url
    except stripe.StripeError as exc:
        logger.error("stripe_checkout_session_failed", tenant_id=tenant_id, error=str(exc))
        raise BusinessError(f"Erreur Stripe lors de la creation de la session : {exc}", code="STRIPE_ERROR") from exc


def cancel_subscription(subscription_id: str) -> bool:
    """Annule un abonnement à la fin de la période en cours."""
    _configure()
    try:
        stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
        logger.info("stripe_subscription_cancel_requested", subscription_id=subscription_id)
        return True
    except stripe.StripeError as exc:
        logger.error("stripe_subscription_cancel_failed", subscription_id=subscription_id, error=str(exc))
        raise BusinessError(f"Erreur Stripe lors de l'annulation : {exc}", code="STRIPE_ERROR") from exc


def get_subscription(subscription_id: str) -> dict:
    """Récupère les informations d'un abonnement Stripe."""
    _configure()
    try:
        sub = stripe.Subscription.retrieve(subscription_id)
        return {
            "status": sub.status,
            "current_period_end": sub.current_period_end,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }
    except stripe.StripeError as exc:
        logger.error("stripe_subscription_get_failed", subscription_id=subscription_id, error=str(exc))
        raise BusinessError(f"Erreur Stripe lors de la recuperation : {exc}", code="STRIPE_ERROR") from exc


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Vérifie et construit un événement webhook Stripe."""
    _configure()
    return stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
