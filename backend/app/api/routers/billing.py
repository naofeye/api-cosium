"""Routes de facturation Stripe — checkout, webhook, statut, annulation."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.services import billing_service

logger = get_logger("billing_router")

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


# --- Schemas request / response ---


class CheckoutRequest(BaseModel):
    plan: str = Field(..., pattern="^(solo|reseau|ia_pro)$", description="Plan choisi")


class CheckoutResponse(BaseModel):
    checkout_url: str


class BillingStatusResponse(BaseModel):
    plan: str
    status: str
    trial_days_remaining: int | None = None
    stripe_customer_id: str | None = None


class MessageResponse(BaseModel):
    message: str


# --- Endpoints ---


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CheckoutResponse:
    """Crée une session Stripe Checkout pour souscrire à un plan."""
    checkout_url = billing_service.initiate_checkout(db, tenant_id=tenant_ctx.tenant_id, plan=payload.plan)
    logger.info("checkout_created", tenant_id=tenant_ctx.tenant_id, plan=payload.plan)
    return CheckoutResponse(checkout_url=checkout_url)


@router.post("/webhook", response_model=MessageResponse)
async def stripe_webhook(request: Request) -> MessageResponse:
    """Reçoit et traite les webhooks Stripe (public, pas d'auth JWT)."""
    from app.db.session import SessionLocal
    from app.integrations.stripe_client import construct_webhook_event

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = construct_webhook_event(payload=payload, sig_header=sig_header)

    db = SessionLocal()
    try:
        billing_service.handle_webhook(db, event=event)
    finally:
        db.close()

    return MessageResponse(message="ok")


@router.get("/status", response_model=BillingStatusResponse)
def get_billing_status(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> BillingStatusResponse:
    """Retourne les informations de facturation du tenant courant."""
    info = billing_service.get_billing_info(db, tenant_id=tenant_ctx.tenant_id)
    return BillingStatusResponse(**info)


@router.post("/cancel", response_model=MessageResponse)
def cancel_subscription(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> MessageResponse:
    """Annule l'abonnement du tenant (prend effet en fin de période)."""
    billing_service.cancel_subscription_for_tenant(db, tenant_id=tenant_ctx.tenant_id)
    logger.info("subscription_cancel_requested", tenant_id=tenant_ctx.tenant_id)
    return MessageResponse(message="Abonnement annulé. Il reste actif jusqu'à la fin de la période en cours.")
