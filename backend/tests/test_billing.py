"""Tests de facturation Stripe (mock) et billing status."""
from unittest.mock import MagicMock, patch

from app.models import Tenant


def _signup_and_get_token(client):
    resp = client.post("/api/v1/onboarding/signup", json={
        "company_name": "Billing Test",
        "owner_email": "billing@test.local",
        "owner_password": "Test1234",
        "owner_first_name": "A",
        "owner_last_name": "B",
    })
    return resp.json()["access_token"], resp.json()["tenant_id"]


def test_billing_status_trial(client, db):
    token, tenant_id = _signup_and_get_token(client)
    resp = client.get("/api/v1/billing/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "trial"
    assert data["plan"] == "trial"
    assert data["trial_days_remaining"] is not None


def test_billing_status_default_tenant(client, auth_headers):
    resp = client.get("/api/v1/billing/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "trial"


@patch("app.integrations.stripe_client.stripe")
@patch("app.services.billing_service.PLAN_PRICE_MAP", {"solo": "price_test_solo", "reseau": "price_test_reseau", "ia_pro": "price_test_ia_pro"})
def test_checkout_creates_session(mock_stripe, client, db):
    token, tenant_id = _signup_and_get_token(client)

    mock_customer = MagicMock()
    mock_customer.id = "cus_test123"
    mock_stripe.Customer.create.return_value = mock_customer

    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test"
    mock_stripe.checkout.Session.create.return_value = mock_session

    resp = client.post(
        "/api/v1/billing/checkout",
        json={"plan": "solo"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "checkout_url" in data
    assert data["checkout_url"] == "https://checkout.stripe.com/test"


def test_checkout_invalid_plan_rejected(client, db):
    token, _ = _signup_and_get_token(client)
    resp = client.post(
        "/api/v1/billing/checkout",
        json={"plan": "invalid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@patch("app.integrations.stripe_client.stripe")
def test_cancel_subscription(mock_stripe, client, db):
    token, tenant_id = _signup_and_get_token(client)

    # Set subscription
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant.stripe_subscription_id = "sub_test123"
    tenant.subscription_status = "active"
    db.commit()

    mock_stripe.Subscription.modify.return_value = MagicMock()

    resp = client.post("/api/v1/billing/cancel", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
