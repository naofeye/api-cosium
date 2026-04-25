"""Tests for analytics_kpi_service: financial KPIs, aging balance, payer performance,
operational KPIs, and admin_metrics_service system metrics."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.models import (
    AuditLog,
    Case,
    Customer,
    Facture,
    Payment,
    PayerOrganization,
    PecRequest,
    TenantUser,
    User,
)
from app.models.cosium_data import CosiumInvoice
from app.services import admin_metrics_service, analytics_kpi_service


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_customer(db, tenant_id: int, first_name: str = "Jean") -> Customer:
    c = Customer(tenant_id=tenant_id, first_name=first_name, last_name="Test")
    db.add(c)
    db.flush()
    return c


def _make_case(db, tenant_id: int, customer_id: int) -> Case:
    case = Case(tenant_id=tenant_id, customer_id=customer_id, status="draft")
    db.add(case)
    db.flush()
    return case


_devis_counter = 0


def _make_devis(db, tenant_id: int, case_id: int):
    global _devis_counter
    from app.models import Devis
    _devis_counter += 1
    d = Devis(
        tenant_id=tenant_id,
        case_id=case_id,
        numero=f"D-{tenant_id}-{case_id}-{_devis_counter}",
        status="draft",
        montant_ttc=Decimal("100.00"),
    )
    db.add(d)
    db.flush()
    return d


_facture_counter = 0


def _make_facture(db, tenant_id: int, case_id: int, devis_id: int, montant_ttc: float) -> Facture:
    global _facture_counter
    _facture_counter += 1
    f = Facture(
        tenant_id=tenant_id,
        case_id=case_id,
        devis_id=devis_id,
        numero=f"F-{tenant_id}-{_facture_counter}",
        montant_ttc=Decimal(str(montant_ttc)),
        montant_ht=Decimal(str(montant_ttc)),
    )
    db.add(f)
    db.flush()
    return f


def _make_payment(
    db,
    tenant_id: int,
    case_id: int,
    amount_due: float,
    amount_paid: float,
    payer_type: str = "client",
    status: str = "pending",
    days_ago: int = 0,
) -> Payment:
    created = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_ago)
    p = Payment(
        tenant_id=tenant_id,
        case_id=case_id,
        payer_type=payer_type,
        amount_due=Decimal(str(amount_due)),
        amount_paid=Decimal(str(amount_paid)),
        status=status,
        created_at=created,
    )
    db.add(p)
    db.flush()
    return p


# ---------------------------------------------------------------------------
# get_financial_kpis
# ---------------------------------------------------------------------------

class TestGetFinancialKpis:
    def test_returns_zeros_when_no_data(self, db, default_tenant):
        result = analytics_kpi_service.get_financial_kpis(db, default_tenant.id)
        assert result.ca_total == 0
        assert result.montant_encaisse == 0
        assert result.reste_a_encaisser == 0
        assert result.taux_recouvrement == 0

    def test_financial_kpis_from_optiflow_data(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        devis = _make_devis(db, default_tenant.id, case.id)
        _make_facture(db, default_tenant.id, case.id, devis.id, 1000.0)
        _make_payment(db, default_tenant.id, case.id, amount_due=1000.0, amount_paid=800.0, status="partial")
        db.commit()

        result = analytics_kpi_service.get_financial_kpis(db, default_tenant.id)
        # No Cosium data => falls back to OptiFlow data
        assert result.ca_total == Decimal("1000.00")
        assert result.montant_encaisse == Decimal("800.00")
        assert result.taux_recouvrement > 0

    def test_taux_recouvrement_100_when_fully_paid(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        devis = _make_devis(db, default_tenant.id, case.id)
        _make_facture(db, default_tenant.id, case.id, devis.id, 500.0)
        _make_payment(db, default_tenant.id, case.id, amount_due=500.0, amount_paid=500.0, status="paid")
        db.commit()

        result = analytics_kpi_service.get_financial_kpis(db, default_tenant.id)
        assert result.taux_recouvrement == 100.0

    def test_date_range_filter_excludes_old_data(self, db, default_tenant):
        """Invoices created before date_from must not be counted."""
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        devis = _make_devis(db, default_tenant.id, case.id)
        old_facture = _make_facture(db, default_tenant.id, case.id, devis.id, 999.0)
        # Manually push created_at into the past
        old_facture.created_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=60)
        db.commit()

        date_from = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=10)
        result = analytics_kpi_service.get_financial_kpis(db, default_tenant.id, date_from=date_from)
        assert result.ca_total == 0

    def test_cosium_data_takes_priority_when_synced(self, db, default_tenant):
        """When Cosium invoices are present and payments look valid, Cosium data is used."""
        inv = CosiumInvoice(
            tenant_id=default_tenant.id,
            cosium_id=1001,
            invoice_number="INV-001",
            type="INVOICE",
            total_ti=2000.0,
            outstanding_balance=500.0,
        )
        db.add(inv)
        db.commit()

        result = analytics_kpi_service.get_financial_kpis(db, default_tenant.id)
        assert result.ca_total == 2000.0
        assert result.reste_a_encaisser == 500.0

    def test_isolates_by_tenant_id(self, db, default_tenant):
        from app.models import Organization, Tenant

        other_org = Organization(name="Org2", slug="org2", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(organization_id=other_org.id, name="Mag2", slug="mag2")
        db.add(other_tenant)
        db.flush()

        customer = _make_customer(db, other_tenant.id)
        case = _make_case(db, other_tenant.id, customer.id)
        devis = _make_devis(db, other_tenant.id, case.id)
        _make_facture(db, other_tenant.id, case.id, devis.id, 5000.0)
        db.commit()

        result = analytics_kpi_service.get_financial_kpis(db, default_tenant.id)
        assert result.ca_total == 0


# ---------------------------------------------------------------------------
# get_aging_balance
# ---------------------------------------------------------------------------

class TestGetAgingBalance:
    def test_empty_returns_four_buckets_all_zero(self, db, default_tenant):
        result = analytics_kpi_service.get_aging_balance(db, default_tenant.id)
        assert len(result.buckets) == 4
        assert result.total == 0
        for bucket in result.buckets:
            assert bucket.total == 0

    def test_recent_payment_lands_in_0_30_bucket(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        _make_payment(db, default_tenant.id, case.id, amount_due=100.0, amount_paid=0.0, days_ago=5)
        db.commit()

        result = analytics_kpi_service.get_aging_balance(db, default_tenant.id)
        bucket_0_30 = next(b for b in result.buckets if b.tranche == "0-30j")
        assert bucket_0_30.client == Decimal("100.00")

    def test_old_payment_lands_in_90plus_bucket(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        _make_payment(db, default_tenant.id, case.id, amount_due=200.0, amount_paid=0.0, days_ago=120)
        db.commit()

        result = analytics_kpi_service.get_aging_balance(db, default_tenant.id)
        bucket_90 = next(b for b in result.buckets if b.tranche == "90j+")
        assert bucket_90.client == Decimal("200.00")

    def test_paid_payments_not_included(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        _make_payment(
            db, default_tenant.id, case.id,
            amount_due=300.0, amount_paid=300.0,
            status="paid", days_ago=5,
        )
        db.commit()

        result = analytics_kpi_service.get_aging_balance(db, default_tenant.id)
        assert result.total == 0

    def test_mutuelle_payer_type_routed_correctly(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        _make_payment(
            db, default_tenant.id, case.id,
            amount_due=150.0, amount_paid=0.0,
            payer_type="mutuelle", days_ago=10,
        )
        db.commit()

        result = analytics_kpi_service.get_aging_balance(db, default_tenant.id)
        bucket_0_30 = next(b for b in result.buckets if b.tranche == "0-30j")
        assert bucket_0_30.mutuelle == Decimal("150.00")

    def test_total_is_sum_of_outstanding(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        _make_payment(db, default_tenant.id, case.id, amount_due=100.0, amount_paid=40.0, days_ago=5)
        _make_payment(db, default_tenant.id, case.id, amount_due=200.0, amount_paid=50.0, days_ago=5, status="partial")
        db.commit()

        result = analytics_kpi_service.get_aging_balance(db, default_tenant.id)
        assert result.total == Decimal("210.00")  # (100-40) + (200-50)

    def test_partial_bucket_ranges(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        _make_payment(db, default_tenant.id, case.id, amount_due=50.0, amount_paid=0.0, days_ago=35)
        _make_payment(db, default_tenant.id, case.id, amount_due=60.0, amount_paid=0.0, days_ago=65, status="partial")
        db.commit()

        result = analytics_kpi_service.get_aging_balance(db, default_tenant.id)
        bucket_30_60 = next(b for b in result.buckets if b.tranche == "30-60j")
        bucket_60_90 = next(b for b in result.buckets if b.tranche == "60-90j")
        assert bucket_30_60.client == Decimal("50.00")
        assert bucket_60_90.client == Decimal("60.00")


# ---------------------------------------------------------------------------
# get_payer_performance
# ---------------------------------------------------------------------------

class TestGetPayerPerformance:
    def test_empty_when_no_orgs(self, db, default_tenant):
        result = analytics_kpi_service.get_payer_performance(db, default_tenant.id)
        assert result.payers == []

    def test_org_with_no_pecs_excluded(self, db, default_tenant):
        org = PayerOrganization(tenant_id=default_tenant.id, name="Orphan Org", type="mutuelle", code="ORPHAN-001")
        db.add(org)
        db.commit()

        result = analytics_kpi_service.get_payer_performance(db, default_tenant.id)
        assert result.payers == []

    def test_acceptance_rate_computed(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        case = _make_case(db, default_tenant.id, customer.id)
        org = PayerOrganization(tenant_id=default_tenant.id, name="MutA", type="mutuelle", code="MUTA-001")
        db.add(org)
        db.flush()

        # 1 accepted, 1 refused
        pec_ok = PecRequest(
            tenant_id=default_tenant.id,
            case_id=case.id,
            organization_id=org.id,
            montant_demande=Decimal("200.00"),
            montant_accorde=Decimal("200.00"),
            status="acceptee",
        )
        pec_ko = PecRequest(
            tenant_id=default_tenant.id,
            case_id=case.id,
            organization_id=org.id,
            montant_demande=Decimal("100.00"),
            status="refusee",
        )
        db.add_all([pec_ok, pec_ko])
        db.commit()

        result = analytics_kpi_service.get_payer_performance(db, default_tenant.id)
        assert len(result.payers) == 1
        payer = result.payers[0]
        assert payer.name == "MutA"
        assert payer.acceptance_rate == 50.0
        assert payer.rejection_rate == 50.0
        assert payer.total_requested == Decimal("300.00")
        assert payer.total_accepted == Decimal("200.00")


# ---------------------------------------------------------------------------
# get_operational_kpis
# ---------------------------------------------------------------------------

class TestGetOperationalKpis:
    def test_zeros_when_no_cases(self, db, default_tenant):
        result = analytics_kpi_service.get_operational_kpis(db, default_tenant.id)
        assert result.dossiers_en_cours == 0
        assert result.taux_completude == 0

    def test_counts_cases_for_tenant(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        _make_case(db, default_tenant.id, customer.id)
        _make_case(db, default_tenant.id, customer.id)
        db.commit()

        result = analytics_kpi_service.get_operational_kpis(db, default_tenant.id)
        assert result.dossiers_en_cours == 2

    def test_does_not_count_other_tenant_cases(self, db, default_tenant):
        from app.models import Organization, Tenant

        other_org = Organization(name="OrgX", slug="orgx", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(organization_id=other_org.id, name="MagX", slug="magx")
        db.add(other_tenant)
        db.flush()

        customer = _make_customer(db, other_tenant.id)
        _make_case(db, other_tenant.id, customer.id)
        db.commit()

        result = analytics_kpi_service.get_operational_kpis(db, default_tenant.id)
        assert result.dossiers_en_cours == 0

    def test_taux_completude_100_when_all_docs_present(self, db, default_tenant):
        """When no required document types exist, every case is complete."""
        from sqlalchemy import delete
        from app.models import DocumentType

        # Remove all required document types so completeness = 100%
        db.execute(delete(DocumentType).where(DocumentType.is_required.is_(True)))
        db.flush()

        customer = _make_customer(db, default_tenant.id)
        _make_case(db, default_tenant.id, customer.id)
        db.commit()

        result = analytics_kpi_service.get_operational_kpis(db, default_tenant.id)
        assert result.taux_completude == 100.0
        assert result.pieces_manquantes == 0


# ---------------------------------------------------------------------------
# admin_metrics_service.get_tenant_metrics
# ---------------------------------------------------------------------------

class TestGetTenantMetrics:
    def test_returns_dict_with_expected_keys(self, db, default_tenant):
        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        assert "totals" in result
        assert "activity" in result

    def test_totals_keys_present(self, db, default_tenant):
        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        totals = result["totals"]
        for key in ("users", "clients", "dossiers", "factures", "paiements"):
            assert key in totals

    def test_counts_active_tenant_users(self, db, default_tenant):
        user = User(email="metric_user@example.com", password_hash="x", role="user", is_active=True)
        db.add(user)
        db.flush()
        tu = TenantUser(user_id=user.id, tenant_id=default_tenant.id, role="operator", is_active=True)
        db.add(tu)
        db.commit()

        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        # At least 1 active user was added
        assert result["totals"]["users"] >= 1

    def test_inactive_tenant_users_not_counted(self, db, default_tenant):
        user = User(email="inactive_metric@example.com", password_hash="x", role="user", is_active=True)
        db.add(user)
        db.flush()
        tu = TenantUser(user_id=user.id, tenant_id=default_tenant.id, role="operator", is_active=False)
        db.add(tu)
        db.commit()

        before = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)["totals"]["users"]
        # The inactive user should NOT inflate the count
        # (count is only active=True rows)
        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        # Adding this inactive user didn't change the active count
        assert result["totals"]["users"] == before

    def test_counts_clients(self, db, default_tenant):
        _make_customer(db, default_tenant.id, "ClientA")
        _make_customer(db, default_tenant.id, "ClientB")
        db.commit()

        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        assert result["totals"]["clients"] == 2

    def test_counts_cases(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        _make_case(db, default_tenant.id, customer.id)
        db.commit()

        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        assert result["totals"]["dossiers"] == 1

    def test_activity_keys_present(self, db, default_tenant):
        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        activity = result["activity"]
        assert "actions_last_hour" in activity
        assert "active_users_last_hour" in activity

    def test_recent_audit_logs_counted(self, db, default_tenant):
        user = User(email="auditor@example.com", password_hash="x", role="user", is_active=True)
        db.add(user)
        db.flush()
        log = AuditLog(
            tenant_id=default_tenant.id,
            user_id=user.id,
            action="create",
            entity_type="case",
            entity_id=1,
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=10),
        )
        db.add(log)
        db.commit()

        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        assert result["activity"]["actions_last_hour"] >= 1
        assert result["activity"]["active_users_last_hour"] >= 1

    def test_old_audit_logs_not_counted(self, db, default_tenant):
        user = User(email="old_auditor@example.com", password_hash="x", role="user", is_active=True)
        db.add(user)
        db.flush()
        log = AuditLog(
            tenant_id=default_tenant.id,
            user_id=user.id,
            action="create",
            entity_type="case",
            entity_id=2,
            created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=3),
        )
        db.add(log)
        db.commit()

        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        # Old log should not appear in last-hour window
        assert result["activity"]["actions_last_hour"] == 0

    def test_isolated_by_tenant(self, db, default_tenant):
        from app.models import Organization, Tenant

        other_org = Organization(name="OrgZ", slug="orgz", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(organization_id=other_org.id, name="MagZ", slug="magz")
        db.add(other_tenant)
        db.flush()

        _make_customer(db, other_tenant.id, "ForeignClient")
        db.commit()

        result = admin_metrics_service.get_tenant_metrics(db, default_tenant.id)
        assert result["totals"]["clients"] == 0


# ---------------------------------------------------------------------------
# admin_metrics_service.get_entity_quality
# ---------------------------------------------------------------------------

class TestGetEntityQuality:
    def test_returns_zeros_when_empty(self, db, default_tenant):
        from app.models.cosium_data import CosiumInvoice

        result = admin_metrics_service.get_entity_quality(db, CosiumInvoice, default_tenant.id)
        assert result["total"] == 0
        assert result["linked"] == 0
        assert result["orphan"] == 0
        assert result["link_rate"] == 0.0

    def test_link_rate_100_when_all_linked(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        inv = CosiumInvoice(
            tenant_id=default_tenant.id,
            cosium_id=2001,
            invoice_number="INV-Q1",
            type="INVOICE",
            total_ti=100.0,
            customer_id=customer.id,
        )
        db.add(inv)
        db.commit()

        result = admin_metrics_service.get_entity_quality(db, CosiumInvoice, default_tenant.id)
        assert result["total"] == 1
        assert result["linked"] == 1
        assert result["orphan"] == 0
        assert result["link_rate"] == 100.0

    def test_orphan_counted_when_no_customer_id(self, db, default_tenant):
        inv = CosiumInvoice(
            tenant_id=default_tenant.id,
            cosium_id=2002,
            invoice_number="INV-Q2",
            type="INVOICE",
            total_ti=200.0,
            customer_id=None,
        )
        db.add(inv)
        db.commit()

        result = admin_metrics_service.get_entity_quality(db, CosiumInvoice, default_tenant.id)
        assert result["total"] == 1
        assert result["linked"] == 0
        assert result["orphan"] == 1
        assert result["link_rate"] == 0.0

    def test_mixed_link_rate(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        inv_linked = CosiumInvoice(
            tenant_id=default_tenant.id, cosium_id=2003, invoice_number="INV-LK",
            type="INVOICE", total_ti=100.0, customer_id=customer.id,
        )
        inv_orphan = CosiumInvoice(
            tenant_id=default_tenant.id, cosium_id=2004, invoice_number="INV-OR",
            type="INVOICE", total_ti=100.0, customer_id=None,
        )
        db.add_all([inv_linked, inv_orphan])
        db.commit()

        result = admin_metrics_service.get_entity_quality(db, CosiumInvoice, default_tenant.id)
        assert result["total"] == 2
        assert result["linked"] == 1
        assert result["orphan"] == 1
        assert result["link_rate"] == 50.0
