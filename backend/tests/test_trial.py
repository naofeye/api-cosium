"""Tests de gestion du trial : expiration, jours restants."""
import pytest
from datetime import datetime, timedelta, timezone
from app.models import Organization, Tenant, TenantUser, User
from app.security import hash_password


def test_trial_days_remaining(client, db):
    resp = client.post("/api/v1/onboarding/signup", json={
        "company_name": "Trial Test",
        "owner_email": "trial@test.local",
        "owner_password": "Test1234",
        "owner_first_name": "A",
        "owner_last_name": "B",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    status = client.get(
        "/api/v1/onboarding/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = status.json()
    assert data["trial_days_remaining"] >= 13
    assert data["trial_days_remaining"] <= 14


def test_trial_expired_shows_zero_days(client, db):
    resp = client.post("/api/v1/onboarding/signup", json={
        "company_name": "Expired Trial",
        "owner_email": "expired@test.local",
        "owner_password": "Test1234",
        "owner_first_name": "A",
        "owner_last_name": "B",
    })
    token = resp.json()["access_token"]
    tenant_id = resp.json()["tenant_id"]

    # Force trial to be expired
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    org = db.query(Organization).filter(Organization.id == tenant.organization_id).first()
    org.trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()

    status = client.get(
        "/api/v1/onboarding/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = status.json()
    assert data["trial_days_remaining"] == 0


def test_no_trial_for_solo_plan(client, db):
    # Use the default org (solo plan, no trial_ends_at)
    from app.models import Organization
    org = db.query(Organization).filter(Organization.slug == "test-org").first()
    assert org.trial_ends_at is None  # Solo plan has no trial

    # Login as existing test user
    from tests.conftest import seed_user_fixture
    from app.security import hash_password
    user = User(email="solo@test.local", password_hash=hash_password("Test1234"), role="admin", is_active=True)
    db.add(user)
    db.flush()
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    db.add(TenantUser(user_id=user.id, tenant_id=tenant.id, role="admin"))
    db.commit()

    login_resp = client.post("/api/v1/auth/login", json={
        "email": "solo@test.local", "password": "Test1234",
    })
    token = login_resp.cookies.get("optiflow_token")

    status = client.get(
        "/api/v1/onboarding/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = status.json()
    assert data["trial_days_remaining"] is None
