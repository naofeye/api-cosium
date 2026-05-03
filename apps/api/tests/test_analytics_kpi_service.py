"""Tests analytics_kpi_service : KPIs financiers + aging + performance + operationnel."""
from __future__ import annotations

import pytest

from app.models import Case, Customer, Facture, Payment
from app.services import analytics_kpi_service


@pytest.fixture
def empty_setup(db, default_tenant):
    return default_tenant


@pytest.fixture
def factured_setup(db, default_tenant):
    """Cree 1 client + 1 case + 1 facture + 1 payment partiel."""
    customer = Customer(
        tenant_id=default_tenant.id, first_name="J", last_name="D"
    )
    db.add(customer)
    db.flush()
    case = Case(
        tenant_id=default_tenant.id, customer_id=customer.id, status="en_cours"
    )
    db.add(case)
    db.flush()
    from app.models.devis import Devis
    devis = Devis(
        tenant_id=default_tenant.id,
        case_id=case.id,
        numero="D-001",
        status="signe",
        montant_ht=100,
        tva=20,
        montant_ttc=120,
    )
    db.add(devis)
    db.flush()
    facture = Facture(
        tenant_id=default_tenant.id,
        case_id=case.id,
        devis_id=devis.id,
        numero="F-001",
        status="facturee",
        montant_ht=100,
        tva=20,
        montant_ttc=120,
    )
    db.add(facture)
    db.flush()
    payment = Payment(
        tenant_id=default_tenant.id,
        case_id=case.id,
        facture_id=facture.id,
        payer_type="client",
        amount_due=120,
        amount_paid=50,
        status="partial",
    )
    db.add(payment)
    db.commit()
    return default_tenant


def test_get_financial_kpis_empty_returns_zero(db, empty_setup):
    kpis = analytics_kpi_service.get_financial_kpis(db, empty_setup.id)
    assert float(kpis.ca_total) == 0
    assert float(kpis.montant_encaisse) == 0
    assert float(kpis.reste_a_encaisser) == 0
    assert kpis.taux_recouvrement == 0


def test_get_financial_kpis_factured(db, factured_setup):
    kpis = analytics_kpi_service.get_financial_kpis(db, factured_setup.id)
    assert float(kpis.ca_total) == 120
    assert float(kpis.montant_encaisse) == 50
    assert float(kpis.reste_a_encaisser) == 70
    # Taux recouvrement = 50 / 120 = 41.67
    assert 40 < kpis.taux_recouvrement < 45


def test_get_aging_balance_empty(db, empty_setup):
    aging = analytics_kpi_service.get_aging_balance(db, empty_setup.id)
    assert aging is not None


def test_get_payer_performance_empty(db, empty_setup):
    perf = analytics_kpi_service.get_payer_performance(db, empty_setup.id)
    assert perf is not None


def test_get_operational_kpis_empty(db, empty_setup):
    kpis = analytics_kpi_service.get_operational_kpis(db, empty_setup.id)
    assert kpis is not None


def test_get_financial_kpis_isolated_per_tenant(db, factured_setup):
    """Tenant other ne voit pas les factures du default."""
    from app.models import Organization, Tenant

    other_org = Organization(name="O", slug="o-kpi", plan="solo")
    db.add(other_org)
    db.flush()
    other_tenant = Tenant(
        organization_id=other_org.id,
        name="N",
        slug="n-kpi",
        erp_type="cosium",
        cosium_tenant="o",
        cosium_login="o",
        cosium_password_enc="o",
    )
    db.add(other_tenant)
    db.commit()

    other_kpis = analytics_kpi_service.get_financial_kpis(db, other_tenant.id)
    assert float(other_kpis.ca_total) == 0
    default_kpis = analytics_kpi_service.get_financial_kpis(db, factured_setup.id)
    assert float(default_kpis.ca_total) == 120
