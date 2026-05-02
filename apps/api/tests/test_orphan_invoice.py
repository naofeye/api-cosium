"""Tests reconciliation factures orphelines."""
from __future__ import annotations

import pytest

from app.models import Customer
from app.models.cosium_data import CosiumInvoice
from app.services.orphan_invoice_service import (
    count_orphan_invoices,
    reconcile_orphan_invoices,
)


@pytest.fixture
def with_customers_and_orphan_invoices(db, default_tenant):
    """Cree 2 clients + 4 factures (2 lies, 2 orphelines)."""
    c1 = Customer(
        tenant_id=default_tenant.id,
        first_name="Jean",
        last_name="DUPONT",
        cosium_id=12345,
    )
    c2 = Customer(
        tenant_id=default_tenant.id,
        first_name="Marie",
        last_name="MARTIN",
        cosium_id=67890,
    )
    db.add_all([c1, c2])
    db.flush()

    # 1) Linked via cosium_id (already)
    linked1 = CosiumInvoice(
        tenant_id=default_tenant.id,
        cosium_id=1001,
        invoice_number="F-001",
        type="INVOICE",
        customer_id=c1.id,
        customer_cosium_id="12345",
        customer_name="M. DUPONT Jean",
    )
    # 2) Orphan but matchable via cosium_id
    orphan_cosium = CosiumInvoice(
        tenant_id=default_tenant.id,
        cosium_id=1002,
        invoice_number="F-002",
        type="INVOICE",
        customer_id=None,
        customer_cosium_id="67890",
        customer_name="MME MARTIN Marie",
    )
    # 3) Orphan but matchable via name
    orphan_name = CosiumInvoice(
        tenant_id=default_tenant.id,
        cosium_id=1003,
        invoice_number="F-003",
        type="INVOICE",
        customer_id=None,
        customer_cosium_id=None,
        customer_name="MME MARTIN Marie",
    )
    # 4) Truly orphan (unknown customer)
    truly_orphan = CosiumInvoice(
        tenant_id=default_tenant.id,
        cosium_id=1004,
        invoice_number="F-004",
        type="INVOICE",
        customer_id=None,
        customer_cosium_id="99999",
        customer_name="M. INCONNU Test",
    )
    db.add_all([linked1, orphan_cosium, orphan_name, truly_orphan])
    db.commit()
    return {
        "customer_1_id": c1.id,
        "customer_2_id": c2.id,
        "linked_id": linked1.id,
        "orphan_cosium_id": orphan_cosium.id,
        "orphan_name_id": orphan_name.id,
        "truly_orphan_id": truly_orphan.id,
    }


def test_count_orphans_reflects_state(db, default_tenant, with_customers_and_orphan_invoices):
    stats = count_orphan_invoices(db, default_tenant.id)
    assert stats["total_invoices"] == 4
    assert stats["orphans"] == 3
    assert stats["linked_pct"] == 25.0  # 1/4 lie


def test_reconcile_matches_via_cosium_id(db, default_tenant, with_customers_and_orphan_invoices):
    ids = with_customers_and_orphan_invoices
    result = reconcile_orphan_invoices(db, default_tenant.id)
    assert result["processed"] == 3  # 3 orphelines initialement
    # cosium_id match (orphan_cosium) + name match (orphan_name) = 2
    assert result["matched"] == 2
    assert result["still_orphan"] == 1

    # Verifier les liens BDD
    orphan_cosium = db.get(CosiumInvoice, ids["orphan_cosium_id"])
    orphan_name = db.get(CosiumInvoice, ids["orphan_name_id"])
    truly_orphan = db.get(CosiumInvoice, ids["truly_orphan_id"])

    assert orphan_cosium.customer_id == ids["customer_2_id"]
    assert orphan_name.customer_id == ids["customer_2_id"]
    assert truly_orphan.customer_id is None


def test_reconcile_no_op_when_nothing_to_match(db, default_tenant):
    result = reconcile_orphan_invoices(db, default_tenant.id)
    assert result == {"processed": 0, "matched": 0, "still_orphan": 0}


def test_reconcile_isolated_per_tenant(
    db, default_tenant, with_customers_and_orphan_invoices
):
    """Le matching doit etre isole : un client d'un autre tenant ne doit
    pas etre utilise pour matcher."""
    from app.models import Organization, Tenant

    other_org = Organization(name="Other Org", slug="other-org-pec", plan="solo")
    db.add(other_org)
    db.flush()
    other_tenant = Tenant(
        organization_id=other_org.id,
        name="Autre",
        slug="autre",
        erp_type="cosium",
        cosium_tenant="other",
        cosium_login="other",
        cosium_password_enc="other",
    )
    db.add(other_tenant)
    db.flush()

    # Reconcile le tenant_id par defaut : doit toucher uniquement les factures du tenant
    result = reconcile_orphan_invoices(db, default_tenant.id)
    assert result["matched"] == 2

    # Reconcile other_tenant : aucune facture chez lui, donc no-op
    other_result = reconcile_orphan_invoices(db, other_tenant.id)
    assert other_result == {"processed": 0, "matched": 0, "still_orphan": 0}


def test_reconcile_respects_limit(db, default_tenant, with_customers_and_orphan_invoices):
    """Limite a 1 facture, doit traiter seulement 1."""
    result = reconcile_orphan_invoices(db, default_tenant.id, limit=1)
    assert result["processed"] == 1
    assert result["matched"] in (0, 1)
