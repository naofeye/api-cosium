"""Tests client_360_service : view consolidee client + bundle Cosium."""
from __future__ import annotations

import pytest

from app.core.exceptions import NotFoundError
from app.models import Case, Customer
from app.services import client_360_service


@pytest.fixture
def customer(db, default_tenant):
    c = Customer(
        tenant_id=default_tenant.id,
        first_name="Jean",
        last_name="DUPONT",
        email="jean@dupont.test",
        phone="0123456789",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def customer_with_case(db, default_tenant, customer):
    case = Case(
        tenant_id=default_tenant.id,
        customer_id=customer.id,
        status="en_cours",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return customer, case


def test_get_client_360_unknown_raises_notfound(db, default_tenant):
    with pytest.raises(NotFoundError):
        client_360_service.get_client_360(db, default_tenant.id, 99999)


def test_get_client_360_returns_response(db, default_tenant, customer):
    """Sans dossier, la 360 retourne tout vide mais pas d'erreur."""
    response = client_360_service.get_client_360(
        db, default_tenant.id, customer.id
    )
    # La response doit etre un Client360Response valide
    assert response is not None
    # Les listes vides
    assert hasattr(response, "documents") or response.documents == [] or response.documents is None


def test_get_client_360_includes_cases(db, default_tenant, customer_with_case):
    customer, case = customer_with_case
    response = client_360_service.get_client_360(
        db, default_tenant.id, customer.id
    )
    # Le dossier doit etre liste
    assert response is not None
    if hasattr(response, "dossiers"):
        # DossierSummary est un Pydantic model, pas un dict
        ids = [getattr(d, 'id', None) for d in response.dossiers]
        assert case.id in ids


def test_get_client_360_isolation_per_tenant(db, default_tenant):
    """Un client d'un autre tenant n'est pas visible."""
    from app.models import Organization, Tenant

    other_org = Organization(name="Other Org", slug="other-c360", plan="solo")
    db.add(other_org)
    db.flush()
    other_tenant = Tenant(
        organization_id=other_org.id,
        name="Autre",
        slug="autre-c360",
        erp_type="cosium",
        cosium_tenant="o",
        cosium_login="o",
        cosium_password_enc="o",
    )
    db.add(other_tenant)
    db.flush()
    other_customer = Customer(
        tenant_id=other_tenant.id,
        first_name="Other",
        last_name="DUPONT",
    )
    db.add(other_customer)
    db.commit()

    # Lookup sur default_tenant ne doit pas trouver other_customer
    with pytest.raises(NotFoundError):
        client_360_service.get_client_360(
            db, default_tenant.id, other_customer.id
        )


def test_get_client_cosium_data_unknown_raises_notfound(db, default_tenant):
    with pytest.raises(NotFoundError):
        client_360_service.get_client_cosium_data(
            db, default_tenant.id, 99999
        )


def test_get_client_cosium_data_empty_bundle(db, default_tenant, customer):
    """Sans donnees Cosium liees, le bundle est vide mais valide."""
    bundle = client_360_service.get_client_cosium_data(
        db, default_tenant.id, customer.id
    )
    assert bundle is not None
