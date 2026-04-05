"""Tests unitaires pour billing_service — checkout, webhook, access check."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.models import Organization, Tenant
from app.services import billing_service


class TestCheckAccess:
    """Tests de verification d'acces (trial / abonnement)."""

    def test_active_subscription_grants_access(self, db: Session, default_tenant: Tenant) -> None:
        default_tenant.subscription_status = "active"
        db.commit()
        assert billing_service.check_access(db, default_tenant.id) is True

    def test_trial_with_valid_date_grants_access(self, db: Session, default_tenant: Tenant) -> None:
        default_tenant.subscription_status = "trial"
        org = db.query(Organization).filter(Organization.id == default_tenant.organization_id).first()
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=7)
        db.commit()
        assert billing_service.check_access(db, default_tenant.id) is True

    def test_trial_expired_denies_access(self, db: Session, default_tenant: Tenant) -> None:
        default_tenant.subscription_status = "trial"
        org = db.query(Organization).filter(Organization.id == default_tenant.organization_id).first()
        org.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
        assert billing_service.check_access(db, default_tenant.id) is False

    def test_canceled_subscription_denies_access(self, db: Session, default_tenant: Tenant) -> None:
        default_tenant.subscription_status = "canceled"
        db.commit()
        assert billing_service.check_access(db, default_tenant.id) is False

    def test_nonexistent_tenant_raises(self, db: Session) -> None:
        with pytest.raises(NotFoundError):
            billing_service.check_access(db, 99999)


class TestGetBillingInfo:
    """Tests de recuperation des infos de facturation."""

    def test_returns_plan_and_status(self, db: Session, default_tenant: Tenant) -> None:
        info = billing_service.get_billing_info(db, default_tenant.id)
        assert "plan" in info
        assert "status" in info
        assert "trial_days_remaining" in info
        assert "stripe_customer_id" in info

    def test_trial_days_computed(self, db: Session, default_tenant: Tenant) -> None:
        default_tenant.subscription_status = "trial"
        org = db.query(Organization).filter(Organization.id == default_tenant.organization_id).first()
        org.trial_ends_at = datetime.now(UTC) + timedelta(days=5)
        db.commit()

        info = billing_service.get_billing_info(db, default_tenant.id)
        assert info["trial_days_remaining"] is not None
        assert info["trial_days_remaining"] >= 4


class TestInitiateCheckout:
    """Tests de creation de session Checkout Stripe."""

    def test_invalid_plan_raises(self, db: Session, default_tenant: Tenant) -> None:
        with pytest.raises(BusinessError):
            billing_service.initiate_checkout(db, default_tenant.id, "nonexistent_plan")


class TestCancelSubscription:
    """Tests d'annulation d'abonnement."""

    def test_no_subscription_raises(self, db: Session, default_tenant: Tenant) -> None:
        default_tenant.stripe_subscription_id = None
        db.commit()
        with pytest.raises(BusinessError):
            billing_service.cancel_subscription_for_tenant(db, default_tenant.id)
