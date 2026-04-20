"""Unit tests for reconciliation_service.

Covers: reconcile_customer_dossier, anomaly detection (overpayment,
underpayment, missing payment, unmatched payments), batch reconciliation,
reconciliation summary statistics, get_customer_reconciliation.

These tests complement test_reconciliation.py which covers link_payments,
settled/partial/en_attente status, payment type categorisation, and
multi-invoice scenarios.
Focus here: anomaly paths, global overpayment, avoir category,
batch result aggregation, stored reconciliation retrieval.
"""

from datetime import UTC, datetime

import pytest

from app.core.constants import (
    CONFIDENCE_CERTAIN,
    CONFIDENCE_INCERTAIN,
    RECON_EN_ATTENTE,
    RECON_INCOHERENT,
    RECON_PARTIELLEMENT_PAYE,
    RECON_SOLDE,
)
from app.models import Customer, Tenant
from app.models.cosium_data import CosiumInvoice, CosiumPayment
from app.models.reconciliation import DossierReconciliation
from app.services.reconciliation_service import (
    get_customer_reconciliation,
    get_reconciliation_summary,
    get_unsettled_reconciliations,
    reconcile_all_customers,
    reconcile_customer_dossier,
)
from app.services._reconciliation_helpers import (
    build_explanation,
    classify_payment,
    detect_overpayment_anomaly,
    determine_invoice_status,
    determine_pec_status,
    determine_reconciliation_status,
    names_match,
    normalize_name,
)

# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _customer(
    db,
    tenant_id: int,
    first_name: str = "Sophie",
    last_name: str = "Lemaire",
    cosium_id: str = "CX01",
) -> Customer:
    c = Customer(tenant_id=tenant_id, first_name=first_name, last_name=last_name, cosium_id=cosium_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _invoice(
    db,
    tenant_id: int,
    cosium_id: int,
    customer_id: int,
    customer_cosium_id: str = "CX01",
    total_ti: float = 400.0,
    outstanding: float = 0.0,
    settled: bool = True,
    inv_type: str = "INVOICE",
    share_ss: float = 0.0,
    share_pi: float = 0.0,
) -> CosiumInvoice:
    inv = CosiumInvoice(
        tenant_id=tenant_id,
        cosium_id=cosium_id,
        invoice_number=f"INV-{cosium_id}",
        invoice_date=datetime(2026, 1, 20, tzinfo=UTC),
        customer_name="Lemaire Sophie",
        customer_cosium_id=customer_cosium_id,
        customer_id=customer_id,
        type=inv_type,
        total_ti=total_ti,
        outstanding_balance=outstanding,
        share_social_security=share_ss,
        share_private_insurance=share_pi,
        settled=settled,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def _payment(
    db,
    tenant_id: int,
    cosium_id: int,
    amount: float = 100.0,
    ptype: str = "CB",
    customer_id: int | None = None,
    customer_cosium_id: str | None = None,
    invoice_cosium_id: int | None = None,
    issuer_name: str = "LEMAIRE SOPHIE",
) -> CosiumPayment:
    p = CosiumPayment(
        tenant_id=tenant_id,
        cosium_id=cosium_id,
        amount=amount,
        type=ptype,
        issuer_name=issuer_name,
        customer_id=customer_id,
        customer_cosium_id=customer_cosium_id,
        invoice_cosium_id=invoice_cosium_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Tests: reconcile_customer_dossier
# ---------------------------------------------------------------------------


class TestReconcileCustomerDossier:
    """Core scenarios for reconcile_customer_dossier."""

    def test_customer_not_found_raises(self, db, default_tenant):
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            reconcile_customer_dossier(db, default_tenant.id, 99999)

    def test_no_invoices_info_insuffisante(self, db, default_tenant):
        """Customer with no invoices gets info_insuffisante status."""
        cust = _customer(db, default_tenant.id, "No", "Invoice", "NI01")

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        assert result.status == "info_insuffisante"
        assert result.invoice_count == 0

    def test_credit_note_counted_separately(self, db, default_tenant):
        """CREDIT_NOTE type invoices are counted in credit_note_count, not invoice_count."""
        cust = _customer(db, default_tenant.id, "Avoir", "Dupont", "AV01")
        _invoice(db, default_tenant.id, 8001, cust.id, "AV01", total_ti=100, inv_type="CREDIT_NOTE")
        _invoice(db, default_tenant.id, 8002, cust.id, "AV01", total_ti=200, settled=True)

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        assert result.credit_note_count == 1
        assert result.invoice_count == 1

    def test_avoir_payment_category(self, db, default_tenant):
        """AV type payment is classified in avoir category."""
        cust = _customer(db, default_tenant.id, "Rem", "Bourse", "RB01")
        _invoice(db, default_tenant.id, 9001, cust.id, "RB01", total_ti=100, outstanding=0, settled=True)
        _payment(db, default_tenant.id, 900, amount=100, ptype="AV",
                 customer_id=cust.id, customer_cosium_id="RB01", invoice_cosium_id=9001)

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        assert result.total_avoir == 100.0
        assert result.total_client == 0.0

    def test_has_pec_false_when_no_ss_shares(self, db, default_tenant):
        """Invoice without social security/mutuelle shares → has_pec is False."""
        cust = _customer(db, default_tenant.id, "Hors", "PEC", "HP01")
        _invoice(db, default_tenant.id, 10001, cust.id, "HP01", total_ti=300, outstanding=0, settled=True)
        _payment(db, default_tenant.id, 1000, amount=300, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=10001)

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        assert result.has_pec is False
        assert result.pec_status is None

    def test_pec_secu_only(self, db, default_tenant):
        """Invoice with secu share + only TPSV payment → pec_status secu_uniquement."""
        cust = _customer(db, default_tenant.id, "Secu", "Only", "SO01")
        _invoice(db, default_tenant.id, 11001, cust.id, "SO01",
                 total_ti=200, outstanding=0, settled=True, share_ss=150)
        _payment(db, default_tenant.id, 1100, amount=150, ptype="TPSV",
                 customer_id=cust.id, invoice_cosium_id=11001)
        _payment(db, default_tenant.id, 1101, amount=50, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=11001)

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        assert result.has_pec is True
        assert result.pec_status == "secu_uniquement"

    def test_result_persisted_in_db(self, db, default_tenant):
        """reconcile_customer_dossier must upsert a DossierReconciliation row."""
        cust = _customer(db, default_tenant.id, "Persist", "Test", "PT01")
        _invoice(db, default_tenant.id, 12001, cust.id, "PT01", total_ti=100, outstanding=0, settled=True)
        _payment(db, default_tenant.id, 1200, amount=100, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=12001)

        reconcile_customer_dossier(db, default_tenant.id, cust.id)

        row = db.query(DossierReconciliation).filter(
            DossierReconciliation.tenant_id == default_tenant.id,
            DossierReconciliation.customer_id == cust.id,
        ).first()
        assert row is not None
        assert row.status == RECON_SOLDE

    def test_upsert_overwrites_previous_result(self, db, default_tenant):
        """Reconciling the same customer twice updates the existing row."""
        cust = _customer(db, default_tenant.id, "Update", "Me", "UM01")
        _invoice(db, default_tenant.id, 13001, cust.id, "UM01", total_ti=100, outstanding=100, settled=False)

        first = reconcile_customer_dossier(db, default_tenant.id, cust.id)
        assert first.status == RECON_EN_ATTENTE

        # Pay the invoice
        _payment(db, default_tenant.id, 1300, amount=100, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=13001)
        inv = db.query(CosiumInvoice).filter(CosiumInvoice.cosium_id == 13001).first()
        inv.outstanding_balance = 0
        inv.settled = True
        db.commit()

        second = reconcile_customer_dossier(db, default_tenant.id, cust.id)
        assert second.status == RECON_SOLDE

        row_count = db.query(DossierReconciliation).filter(
            DossierReconciliation.tenant_id == default_tenant.id,
            DossierReconciliation.customer_id == cust.id,
        ).count()
        assert row_count == 1  # still one row


# ---------------------------------------------------------------------------
# Tests: anomaly detection
# ---------------------------------------------------------------------------


class TestAnomalyDetection:
    """Anomaly scenarios: overpayment per invoice, global overpayment, unmatched payments."""

    def test_invoice_level_overpayment_detected(self, db, default_tenant):
        """Payment exceeding invoice TTC triggers surpaiement anomaly."""
        cust = _customer(db, default_tenant.id, "Over", "Pay", "OP01")
        _invoice(db, default_tenant.id, 20001, cust.id, "OP01", total_ti=100, outstanding=0, settled=True)
        _payment(db, default_tenant.id, 2000, amount=180, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=20001)

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        anomaly_types = [a.type for a in result.anomalies]
        assert any("surpaiement" in t for t in anomaly_types)
        assert result.status == RECON_INCOHERENT

    def test_global_overpayment_anomaly(self, db, default_tenant):
        """Global total_paid > total_facture triggers surpaiement_global anomaly."""
        cust = _customer(db, default_tenant.id, "Global", "Over", "GO01")
        _invoice(db, default_tenant.id, 21001, cust.id, "GO01", total_ti=200, outstanding=0, settled=True)
        # Two payments that together exceed the invoice total
        _payment(db, default_tenant.id, 2100, amount=150, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=21001)
        _payment(db, default_tenant.id, 2101, amount=100, ptype="CHQ",
                 customer_id=cust.id)  # unmatched but counted in total

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        anomaly_types = [a.type for a in result.anomalies]
        # Surpaiement global must be present (total_paid 250 > total_facture 200)
        assert "surpaiement_global" in anomaly_types

    def test_unmatched_payments_create_info_anomaly(self, db, default_tenant):
        """Payments with no matching invoice cosium_id appear as paiements_non_rapproches."""
        cust = _customer(db, default_tenant.id, "Unmatch", "Ed", "UE01")
        _invoice(db, default_tenant.id, 22001, cust.id, "UE01", total_ti=300, outstanding=0, settled=True)
        _payment(db, default_tenant.id, 2200, amount=300, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=22001)
        # Orphan payment with no invoice_cosium_id match
        _payment(db, default_tenant.id, 2201, amount=50, ptype="CHQ",
                 customer_id=cust.id, invoice_cosium_id=None)

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        anomaly_types = [a.type for a in result.anomalies]
        assert "paiements_non_rapproches" in anomaly_types

    def test_full_payment_no_anomalies(self, db, default_tenant):
        """Exactly matched payment produces zero anomalies."""
        cust = _customer(db, default_tenant.id, "Clean", "Slate", "CS01")
        _invoice(db, default_tenant.id, 23001, cust.id, "CS01", total_ti=150, outstanding=0, settled=True)
        _payment(db, default_tenant.id, 2300, amount=150, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=23001)

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        assert result.anomalies == []
        assert result.status == RECON_SOLDE

    def test_missing_payment_no_anomaly_object_but_en_attente(self, db, default_tenant):
        """No payment for an unpaid invoice → en_attente status, no anomaly row."""
        cust = _customer(db, default_tenant.id, "Miss", "Pay", "MP01")
        _invoice(db, default_tenant.id, 24001, cust.id, "MP01", total_ti=500, outstanding=500, settled=False)

        result = reconcile_customer_dossier(db, default_tenant.id, cust.id)

        assert result.status == RECON_EN_ATTENTE
        # No surpaiement anomaly — there simply is no payment
        anomaly_types = [a.type for a in result.anomalies]
        assert "surpaiement" not in anomaly_types
        assert "surpaiement_global" not in anomaly_types


# ---------------------------------------------------------------------------
# Tests: batch reconciliation
# ---------------------------------------------------------------------------


class TestBatchReconciliation:
    """reconcile_all_customers processes multiple customers and aggregates."""

    def test_batch_processes_customers_with_invoices(self, db, default_tenant):
        """Customers linked to invoices via cosium_id are reconciled."""
        cust1 = _customer(db, default_tenant.id, "Batch", "One", "BT01")
        cust2 = _customer(db, default_tenant.id, "Batch", "Two", "BT02")
        _invoice(db, default_tenant.id, 30001, cust1.id, "BT01", total_ti=100, outstanding=0, settled=True)
        _invoice(db, default_tenant.id, 30002, cust2.id, "BT02", total_ti=200, outstanding=200, settled=False)
        _payment(db, default_tenant.id, 3000, amount=100, ptype="CB",
                 customer_id=cust1.id, invoice_cosium_id=30001)

        result = reconcile_all_customers(db, default_tenant.id)

        assert result.total_processed >= 2
        assert result.summary.total_customers >= 2

    def test_batch_counts_anomalies(self, db, default_tenant):
        """Batch result includes total anomaly count across all customers."""
        cust = _customer(db, default_tenant.id, "Anomal", "Batch", "AB01")
        _invoice(db, default_tenant.id, 31001, cust.id, "AB01", total_ti=100, outstanding=0, settled=True)
        _payment(db, default_tenant.id, 3100, amount=250, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=31001)

        result = reconcile_all_customers(db, default_tenant.id)

        assert result.anomaly_count > 0

    def test_batch_returns_summary(self, db, default_tenant):
        """Batch result summary has meaningful financial totals."""
        cust = _customer(db, default_tenant.id, "Sum", "Mary", "SM01")
        _invoice(db, default_tenant.id, 32001, cust.id, "SM01", total_ti=500, outstanding=0, settled=True)
        _payment(db, default_tenant.id, 3200, amount=500, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=32001)

        result = reconcile_all_customers(db, default_tenant.id)

        assert result.summary.total_facture >= 500

    def test_batch_empty_tenant_processes_zero(self, db):
        """Batch on a tenant with no invoiced customers processes nothing."""
        from app.models import Organization

        org = Organization(name="Batch Empty", slug="batch-empty", plan="solo")
        db.add(org)
        db.flush()
        t = Tenant(
            organization_id=org.id, name="Batch Empty Store", slug="batch-empty-store",
            cosium_tenant="be", cosium_login="be", cosium_password_enc="be",
        )
        db.add(t)
        db.commit()

        result = reconcile_all_customers(db, t.id)

        assert result.total_processed == 0

    def test_batch_skips_failed_customer_and_continues(self, db, default_tenant):
        """Even if one customer reconciliation fails, batch does not crash."""
        from unittest.mock import patch

        cust1 = _customer(db, default_tenant.id, "Good", "Cust", "GC01")
        _invoice(db, default_tenant.id, 33001, cust1.id, "GC01", total_ti=100, outstanding=0, settled=True)

        original_reconcile = reconcile_customer_dossier

        call_count = 0

        def flaky_reconcile(db, tenant_id, customer_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("simulated failure")
            return original_reconcile(db, tenant_id, customer_id)

        with patch(
            "app.services.reconciliation_service.reconcile_customer_dossier",
            side_effect=flaky_reconcile,
        ):
            result = reconcile_all_customers(db, default_tenant.id)

        # Must not raise; total_processed counts only successful ones
        assert isinstance(result.total_processed, int)


# ---------------------------------------------------------------------------
# Tests: summary statistics
# ---------------------------------------------------------------------------


class TestReconciliationSummary:
    """get_reconciliation_summary aggregates persisted reconciliation rows."""

    def test_summary_correct_totals(self, db, default_tenant):
        tid = default_tenant.id
        cust1 = _customer(db, tid, "Tot", "A", "TA01")
        cust2 = _customer(db, tid, "Tot", "B", "TB01")
        _invoice(db, tid, 40001, cust1.id, "TA01", total_ti=300, outstanding=0, settled=True)
        _payment(db, tid, 4000, amount=300, ptype="CB",
                 customer_id=cust1.id, invoice_cosium_id=40001)
        _invoice(db, tid, 40002, cust2.id, "TB01", total_ti=700, outstanding=700, settled=False)

        reconcile_customer_dossier(db, tid, cust1.id)
        reconcile_customer_dossier(db, tid, cust2.id)

        summary = get_reconciliation_summary(db, tid)

        assert summary.total_customers == 2
        assert summary.total_facture >= 1000

    def test_summary_statuses_counted(self, db, default_tenant):
        """Each reconciliation status is reflected in the summary counter."""
        tid = default_tenant.id
        cust_solde = _customer(db, tid, "Solde", "S1", "SL01")
        cust_attente = _customer(db, tid, "Attente", "A1", "AT01")
        _invoice(db, tid, 41001, cust_solde.id, "SL01", total_ti=100, outstanding=0, settled=True)
        _payment(db, tid, 4100, amount=100, ptype="CB",
                 customer_id=cust_solde.id, invoice_cosium_id=41001)
        _invoice(db, tid, 41002, cust_attente.id, "AT01", total_ti=100, outstanding=100, settled=False)

        reconcile_customer_dossier(db, tid, cust_solde.id)
        reconcile_customer_dossier(db, tid, cust_attente.id)

        summary = get_reconciliation_summary(db, tid)

        assert summary.solde >= 1
        assert summary.en_attente >= 1

    def test_summary_empty_tenant(self, db):
        from app.models import Organization

        org = Organization(name="Empty Summ", slug="empty-summ", plan="solo")
        db.add(org)
        db.flush()
        t = Tenant(
            organization_id=org.id, name="Empty Summ Store", slug="empty-summ-store",
            cosium_tenant="es", cosium_login="es", cosium_password_enc="es",
        )
        db.add(t)
        db.commit()

        summary = get_reconciliation_summary(db, t.id)

        assert summary.total_customers == 0
        assert summary.total_facture == 0.0


# ---------------------------------------------------------------------------
# Tests: get_customer_reconciliation (stored vs. live)
# ---------------------------------------------------------------------------


class TestGetCustomerReconciliation:
    """get_customer_reconciliation: returns stored data or computes on the fly."""

    def test_returns_stored_reconciliation(self, db, default_tenant):
        """If a persisted row exists, it is returned without re-computing."""
        tid = default_tenant.id
        cust = _customer(db, tid, "Store", "D", "SD01")
        # Reconcile once to persist
        _invoice(db, tid, 50001, cust.id, "SD01", total_ti=200, outstanding=0, settled=True)
        _payment(db, tid, 5000, amount=200, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=50001)
        reconcile_customer_dossier(db, tid, cust.id)

        result = get_customer_reconciliation(db, tid, cust.id)

        assert result is not None
        assert result.customer_id == cust.id
        assert result.status == RECON_SOLDE

    def test_computes_on_the_fly_when_not_stored(self, db, default_tenant):
        """If no persisted row exists, reconciliation is computed on the fly."""
        tid = default_tenant.id
        cust = _customer(db, tid, "Fly", "Compute", "FC01")
        _invoice(db, tid, 51001, cust.id, "FC01", total_ti=300, outstanding=300, settled=False)

        result = get_customer_reconciliation(db, tid, cust.id)

        assert result is not None
        assert result.customer_id == cust.id
        assert result.status == RECON_EN_ATTENTE


# ---------------------------------------------------------------------------
# Tests: get_unsettled_reconciliations
# ---------------------------------------------------------------------------


class TestGetUnsettledReconciliations:
    """get_unsettled_reconciliations returns non-settled entries paginated."""

    def test_includes_partiellement_paye(self, db, default_tenant):
        tid = default_tenant.id
        cust = _customer(db, tid, "Part", "Pay2", "PP02")
        _invoice(db, tid, 60001, cust.id, "PP02", total_ti=400, outstanding=150, settled=False)
        _payment(db, tid, 6000, amount=250, ptype="CB",
                 customer_id=cust.id, invoice_cosium_id=60001)
        reconcile_customer_dossier(db, tid, cust.id)

        result = get_unsettled_reconciliations(db, tid)

        statuses = [item["status"] for item in result["items"]]
        assert RECON_PARTIELLEMENT_PAYE in statuses or RECON_EN_ATTENTE in statuses

    def test_settled_customers_excluded(self, db, default_tenant):
        tid = default_tenant.id
        cust_settled = _customer(db, tid, "Paid", "Full", "PF01")
        _invoice(db, tid, 61001, cust_settled.id, "PF01", total_ti=100, outstanding=0, settled=True)
        _payment(db, tid, 6100, amount=100, ptype="CB",
                 customer_id=cust_settled.id, invoice_cosium_id=61001)
        reconcile_customer_dossier(db, tid, cust_settled.id)

        result = get_unsettled_reconciliations(db, tid)

        customer_ids = [item["customer_id"] for item in result["items"]]
        assert cust_settled.id not in customer_ids


# ---------------------------------------------------------------------------
# Tests: helper functions (pure unit)
# ---------------------------------------------------------------------------


class TestHelperFunctions:
    """Pure-unit tests for helper functions re-exported from reconciliation_service."""

    # normalize_name
    def test_normalize_name_strips_accents(self):
        assert normalize_name("Hélène Élodie") == "helene elodie"

    def test_normalize_name_removes_punctuation(self):
        assert normalize_name("O'Brien") == "obrien"

    def test_normalize_name_empty(self):
        assert normalize_name("") == ""

    # names_match
    def test_names_match_exact(self):
        assert names_match("DUPONT JEAN", "dupont jean") is True

    def test_names_match_token_subset(self):
        assert names_match("Jean-Paul Dupont", "dupont jean paul") is True

    def test_names_match_no_match(self):
        assert names_match("Dupont Jean", "Martin Claire") is False

    # classify_payment
    def test_classify_tpsv(self):
        assert classify_payment("TPSV") == "secu"

    def test_classify_tpmv(self):
        assert classify_payment("TPMV") == "mutuelle"

    def test_classify_av(self):
        assert classify_payment("AV") == "avoir"

    def test_classify_vir(self):
        assert classify_payment("VIR") == "client"

    def test_classify_alma(self):
        assert classify_payment("ALMA") == "client"

    # determine_reconciliation_status
    def test_status_solde_when_outstanding_zero(self):
        status, confidence = determine_reconciliation_status(
            total_facture=100, total_paid=100, total_outstanding=0,
            has_invoices=True, has_payments=True,
            has_unmatched=False, has_anomalies=False,
        )
        assert status == RECON_SOLDE
        assert confidence == CONFIDENCE_CERTAIN

    def test_status_en_attente_when_no_payment(self):
        status, _ = determine_reconciliation_status(
            total_facture=200, total_paid=0, total_outstanding=200,
            has_invoices=True, has_payments=False,
            has_unmatched=False, has_anomalies=False,
        )
        assert status == RECON_EN_ATTENTE

    def test_status_partiellement_paye(self):
        status, _ = determine_reconciliation_status(
            total_facture=300, total_paid=100, total_outstanding=200,
            has_invoices=True, has_payments=True,
            has_unmatched=False, has_anomalies=False,
        )
        assert status == RECON_PARTIELLEMENT_PAYE

    def test_status_info_insuffisante_when_no_invoices(self):
        status, confidence = determine_reconciliation_status(
            total_facture=0, total_paid=0, total_outstanding=0,
            has_invoices=False, has_payments=False,
            has_unmatched=False, has_anomalies=False,
        )
        assert status == "info_insuffisante"
        assert confidence == CONFIDENCE_INCERTAIN

    # detect_overpayment_anomaly
    def test_detect_no_anomaly_when_payment_equals_tti(self):
        result = detect_overpayment_anomaly(paid=100.0, total_ti=100.0, invoice_number="F001")
        assert result is None

    def test_detect_no_anomaly_within_tolerance(self):
        result = detect_overpayment_anomaly(paid=100.01, total_ti=100.0, invoice_number="F001")
        assert result is None

    def test_detect_anomaly_when_payment_exceeds_tti(self):
        result = detect_overpayment_anomaly(paid=200.0, total_ti=100.0, invoice_number="F001")
        assert result is not None
        assert result.type == "surpaiement"
        assert result.amount == pytest.approx(100.0)

    # determine_pec_status
    def test_pec_status_none_when_no_shares(self):
        class FakeInvoice:
            share_social_security = 0
            share_private_insurance = 0

        result = determine_pec_status([FakeInvoice()], 0, 0)
        assert result is None

    def test_pec_status_en_attente_when_shares_but_no_payments(self):
        class FakeInvoice:
            share_social_security = 100
            share_private_insurance = 0

        result = determine_pec_status([FakeInvoice()], 0, 0)
        assert result == "en_attente_pec"

    def test_pec_status_secu_et_mutuelle(self):
        class FakeInvoice:
            share_social_security = 100
            share_private_insurance = 50

        result = determine_pec_status([FakeInvoice()], total_secu=100, total_mutuelle=50)
        assert result == "secu_et_mutuelle"

    # build_explanation
    def test_build_explanation_all_settled(self):
        expl = build_explanation(
            invoice_count=2, total_facture=400, total_outstanding=0,
            total_secu=0, total_mutuelle=0, total_client=400, total_avoir=0,
        )
        assert "soldees" in expl
        assert "2 facture" in expl

    def test_build_explanation_outstanding(self):
        expl = build_explanation(
            invoice_count=1, total_facture=300, total_outstanding=100,
            total_secu=0, total_mutuelle=0, total_client=200, total_avoir=0,
        )
        assert "100.00 EUR" in expl

    def test_build_explanation_includes_secu_and_mutuelle(self):
        expl = build_explanation(
            invoice_count=1, total_facture=300, total_outstanding=0,
            total_secu=150, total_mutuelle=100, total_client=50, total_avoir=0,
        )
        assert "Secu" in expl
        assert "Mutuelle" in expl

    # determine_invoice_status
    def test_invoice_status_solde_when_settled(self):
        status = determine_invoice_status(settled=True, outstanding=0, paid=100, total_ti=100)
        assert status == RECON_SOLDE

    def test_invoice_status_partiellement_paye(self):
        status = determine_invoice_status(settled=False, outstanding=50, paid=50, total_ti=100)
        assert status == RECON_PARTIELLEMENT_PAYE

    def test_invoice_status_en_attente_when_no_payment(self):
        status = determine_invoice_status(settled=False, outstanding=100, paid=0, total_ti=100)
        assert status == RECON_EN_ATTENTE
