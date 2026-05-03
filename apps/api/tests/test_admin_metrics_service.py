"""Tests admin_metrics_service : metrics scope tenant + data quality."""
from __future__ import annotations

import pytest

from app.models import Case, Customer, Facture
from app.services import admin_metrics_service


def test_get_tenant_metrics_empty_tenant(db, default_tenant):
    """Tenant vide : tous les compteurs a 0."""
    metrics = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
    assert metrics["totals"]["users"] == 0
    assert metrics["totals"]["clients"] == 0
    assert metrics["totals"]["dossiers"] == 0
    assert metrics["totals"]["factures"] == 0
    assert metrics["totals"]["paiements"] == 0
    assert metrics["activity"]["actions_last_hour"] == 0
    assert metrics["activity"]["active_users_last_hour"] == 0


def test_get_tenant_metrics_counts_clients(db, default_tenant):
    for i in range(3):
        db.add(
            Customer(
                tenant_id=default_tenant.id,
                first_name=f"Client{i}",
                last_name="TEST",
            )
        )
    db.commit()
    metrics = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
    assert metrics["totals"]["clients"] == 3


def test_get_tenant_metrics_counts_cases(db, default_tenant):
    customer = Customer(
        tenant_id=default_tenant.id, first_name="J", last_name="D"
    )
    db.add(customer)
    db.flush()
    for status in ("en_cours", "complet"):
        db.add(
            Case(
                tenant_id=default_tenant.id,
                customer_id=customer.id,
                status=status,
            )
        )
    db.commit()
    metrics = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
    assert metrics["totals"]["dossiers"] == 2


def test_get_tenant_metrics_isolated_per_tenant(db, default_tenant):
    """Le metric d'un tenant ne pollue pas l'autre."""
    from app.models import Organization, Tenant

    other_org = Organization(name="OO", slug="oo-metric", plan="solo")
    db.add(other_org)
    db.flush()
    other_tenant = Tenant(
        organization_id=other_org.id,
        name="O",
        slug="o-metric",
        erp_type="cosium",
        cosium_tenant="o",
        cosium_login="o",
        cosium_password_enc="o",
    )
    db.add(other_tenant)
    db.flush()
    db.add(
        Customer(
            tenant_id=other_tenant.id, first_name="X", last_name="Y"
        )
    )
    db.commit()

    metrics_default = admin_metrics_service.get_tenant_metrics(
        db, default_tenant.id
    )
    metrics_other = admin_metrics_service.get_tenant_metrics(
        db, other_tenant.id
    )
    assert metrics_default["totals"]["clients"] == 0
    assert metrics_other["totals"]["clients"] == 1



