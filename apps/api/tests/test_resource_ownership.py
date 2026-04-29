"""Tests pour require_resource_ownership / assert_resource_owned (defense en profondeur)."""

import pytest

from app.core.deps import assert_resource_owned
from app.core.exceptions import ForbiddenError
from app.models import Case, Customer, Tenant, User
from app.security import hash_password


def _seed_other_tenant(db) -> Tenant:
    from app.models import Organization
    org = Organization(name="Other Org", slug="other-org", plan="solo")
    db.add(org)
    db.flush()
    other = Tenant(
        organization_id=org.id, name="Other Magasin", slug="other-magasin",
        erp_type="cosium",
    )
    db.add(other)
    db.commit()
    return other


def test_assert_resource_owned_passes_for_owned_resource(db, default_tenant):
    customer = Customer(tenant_id=default_tenant.id, first_name="A", last_name="B")
    db.add(customer)
    db.commit()
    # Pas d'exception
    assert_resource_owned(db, "client", customer.id, default_tenant.id)


def test_assert_resource_owned_raises_for_other_tenant_resource(db, default_tenant):
    other = _seed_other_tenant(db)
    customer = Customer(tenant_id=other.id, first_name="X", last_name="Y")
    db.add(customer)
    db.commit()

    with pytest.raises(ForbiddenError) as exc_info:
        assert_resource_owned(db, "client", customer.id, default_tenant.id)
    assert str(customer.id) in str(exc_info.value)


def test_assert_resource_owned_raises_for_unknown_resource(db, default_tenant):
    with pytest.raises(ForbiddenError):
        assert_resource_owned(db, "client", 999999, default_tenant.id)


def test_assert_resource_owned_silent_for_unsupported_type(db, default_tenant):
    """Pas de crash pour un type non liste — laisse passer (defense en profondeur,
    les repos filtreront)."""
    assert_resource_owned(db, "unknown_type", 1, default_tenant.id)


def test_assert_resource_owned_works_for_case(db, default_tenant):
    customer = Customer(tenant_id=default_tenant.id, first_name="A", last_name="B")
    db.add(customer)
    db.flush()
    case = Case(tenant_id=default_tenant.id, customer_id=customer.id, status="en_cours", source="manual")
    db.add(case)
    db.commit()
    assert_resource_owned(db, "case", case.id, default_tenant.id)
    with pytest.raises(ForbiddenError):
        assert_resource_owned(db, "case", case.id, default_tenant.id + 999)
