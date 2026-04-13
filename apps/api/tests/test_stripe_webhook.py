"""Tests Stripe webhook handler — gere 4 events principaux + ignore les autres.

Mock event = SimpleNamespace(type, data=SimpleNamespace(object={...})).
"""
from types import SimpleNamespace

import pytest

from app.models import Organization, Tenant
from app.services.billing_service import handle_webhook


@pytest.fixture(name="tenant_with_stripe")
def tenant_with_stripe_fixture(db):
    """Tenant avec stripe_customer_id et stripe_subscription_id pre-existants."""
    org = db.query(Organization).first()
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    tenant.stripe_customer_id = "cus_test_123"
    tenant.stripe_subscription_id = "sub_test_456"
    tenant.subscription_status = "active"
    db.commit()
    return tenant, org


def _event(event_type: str, data: dict) -> SimpleNamespace:
    """Construit un event Stripe-like a partir d'un dict de payload."""
    return SimpleNamespace(type=event_type, data=SimpleNamespace(object=data))


def test_webhook_checkout_session_completed_activates_subscription(db, tenant_with_stripe):
    tenant, org = tenant_with_stripe
    tenant.subscription_status = "incomplete"
    db.commit()

    event = _event("checkout.session.completed", {
        "metadata": {"tenant_id": str(tenant.id), "plan": "reseau"},
        "subscription": "sub_new_999",
    })
    handle_webhook(db, event=event)
    db.refresh(tenant)
    db.refresh(org)
    assert tenant.subscription_status == "active"
    assert tenant.stripe_subscription_id == "sub_new_999"
    assert org.plan == "reseau"


def test_webhook_checkout_completed_missing_metadata_is_noop(db, tenant_with_stripe):
    tenant, _ = tenant_with_stripe
    original_status = tenant.subscription_status

    event = _event("checkout.session.completed", {})  # pas de metadata, pas de subscription
    handle_webhook(db, event=event)
    db.refresh(tenant)
    assert tenant.subscription_status == original_status


def test_webhook_payment_failed_marks_past_due(db, tenant_with_stripe):
    tenant, _ = tenant_with_stripe
    event = _event("invoice.payment_failed", {"customer": "cus_test_123"})
    handle_webhook(db, event=event)
    db.refresh(tenant)
    assert tenant.subscription_status == "past_due"


def test_webhook_payment_failed_unknown_customer_is_noop(db, tenant_with_stripe):
    tenant, _ = tenant_with_stripe
    event = _event("invoice.payment_failed", {"customer": "cus_unknown"})
    handle_webhook(db, event=event)
    db.refresh(tenant)
    assert tenant.subscription_status == "active"  # inchange


def test_webhook_subscription_deleted_cancels(db, tenant_with_stripe):
    tenant, _ = tenant_with_stripe
    event = _event("customer.subscription.deleted", {"id": "sub_test_456"})
    handle_webhook(db, event=event)
    db.refresh(tenant)
    assert tenant.subscription_status == "canceled"


def test_webhook_subscription_updated_propagates_status(db, tenant_with_stripe):
    tenant, _ = tenant_with_stripe
    event = _event("customer.subscription.updated", {
        "id": "sub_test_456", "status": "trialing",
    })
    handle_webhook(db, event=event)
    db.refresh(tenant)
    assert tenant.subscription_status == "trialing"


def test_webhook_unknown_event_is_ignored(db, tenant_with_stripe):
    """Un event inconnu doit etre logue et ignore (pas d'exception)."""
    tenant, _ = tenant_with_stripe
    event = _event("customer.created", {"id": "cus_random"})
    handle_webhook(db, event=event)  # ne doit pas crasher
    db.refresh(tenant)
    assert tenant.subscription_status == "active"  # inchange
