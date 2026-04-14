"""Tests for the reconciliation engine."""

from datetime import UTC, datetime

from app.models.client import Customer
from app.models.cosium_data import CosiumInvoice, CosiumPayment
from app.models.tenant import Tenant
from app.services.reconciliation_service import (
    classify_payment,
    get_reconciliation_summary,
    link_payments_to_customers,
    names_match,
    normalize_name,
    reconcile_customer_dossier,
)


def _seed_customer(db, tenant_id: int, first_name: str = "Jean", last_name: str = "Dupont", cosium_id: str = "C100") -> Customer:
    c = Customer(
        tenant_id=tenant_id, first_name=first_name, last_name=last_name,
        cosium_id=cosium_id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _seed_invoice(
    db, tenant_id: int, cosium_id: int, customer_cosium_id: str,
    total_ti: float = 500, outstanding: float = 0, settled: bool = True,
    inv_type: str = "INVOICE", share_ss: float = 0, share_pi: float = 0,
    customer_id: int | None = None,
) -> CosiumInvoice:
    # Auto-resolve customer_id from cosium_id if not provided
    if customer_id is None and customer_cosium_id:
        cust = db.query(Customer).filter(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id == customer_cosium_id,
        ).first()
        if cust:
            customer_id = cust.id
    inv = CosiumInvoice(
        tenant_id=tenant_id, cosium_id=cosium_id,
        invoice_number=f"F-{cosium_id}", invoice_date=datetime(2026, 3, 15, tzinfo=UTC),
        customer_name="Dupont Jean", customer_cosium_id=customer_cosium_id,
        customer_id=customer_id,
        type=inv_type, total_ti=total_ti, outstanding_balance=outstanding,
        share_social_security=share_ss, share_private_insurance=share_pi,
        settled=settled,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def _seed_payment(
    db, tenant_id: int, cosium_id: int, amount: float = 100, ptype: str = "CB",
    issuer_name: str = "DUPONT JEAN", customer_id: int | None = None,
    customer_cosium_id: str | None = None, invoice_cosium_id: int | None = None,
) -> CosiumPayment:
    p = CosiumPayment(
        tenant_id=tenant_id, cosium_id=cosium_id, amount=amount,
        type=ptype, issuer_name=issuer_name, customer_id=customer_id,
        customer_cosium_id=customer_cosium_id, invoice_cosium_id=invoice_cosium_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# -----------------------------------------------------------------------
# Test 1: link_payments matches by issuer_name
# -----------------------------------------------------------------------
def test_link_payments_matches_by_issuer_name(db, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _seed_customer(db, tid, "Jean", "Dupont", "C100")
    _seed_payment(db, tid, 1, amount=100, ptype="CB", issuer_name="DUPONT JEAN", customer_id=None)
    _seed_payment(db, tid, 2, amount=50, ptype="CHQ", issuer_name="Dupont Jean", customer_id=None)

    result = link_payments_to_customers(db, tid)
    assert result.newly_linked == 2
    assert result.unmatched == 0

    # Verify payments now have customer_id
    p1 = db.query(CosiumPayment).filter(CosiumPayment.cosium_id == 1).first()
    assert p1.customer_id == cust.id


# -----------------------------------------------------------------------
# Test 2: Settled invoice → status SOLDE
# -----------------------------------------------------------------------
def test_settled_invoice_status_solde(db, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _seed_customer(db, tid, "Marie", "Martin", "C200")
    _seed_invoice(db, tid, 1001, "C200", total_ti=300, outstanding=0, settled=True)
    _seed_payment(db, tid, 10, amount=300, ptype="CB", customer_id=cust.id, customer_cosium_id="C200", invoice_cosium_id=1001)

    result = reconcile_customer_dossier(db, tid, cust.id)
    assert result.status == "solde"
    assert result.confidence == "certain"
    assert result.total_facture == 300


# -----------------------------------------------------------------------
# Test 3: Outstanding > 0 → status PARTIELLEMENT_PAYE
# -----------------------------------------------------------------------
def test_outstanding_partially_paid(db, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _seed_customer(db, tid, "Paul", "Durand", "C300")
    _seed_invoice(db, tid, 2001, "C300", total_ti=500, outstanding=200, settled=False)
    _seed_payment(db, tid, 20, amount=300, ptype="CB", customer_id=cust.id, customer_cosium_id="C300", invoice_cosium_id=2001)

    result = reconcile_customer_dossier(db, tid, cust.id)
    assert result.status == "partiellement_paye"
    assert result.total_outstanding == 200


# -----------------------------------------------------------------------
# Test 4: No payments → status EN_ATTENTE
# -----------------------------------------------------------------------
def test_no_payments_en_attente(db, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _seed_customer(db, tid, "Luc", "Bernard", "C400")
    _seed_invoice(db, tid, 3001, "C400", total_ti=250, outstanding=250, settled=False)

    result = reconcile_customer_dossier(db, tid, cust.id)
    assert result.status == "en_attente"
    assert result.payment_count == 0


# -----------------------------------------------------------------------
# Test 5: Payment types correctly categorized
# -----------------------------------------------------------------------
def test_payment_types_categorized(db, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _seed_customer(db, tid, "Lucie", "Moreau", "C500")
    _seed_invoice(db, tid, 4001, "C500", total_ti=1000, outstanding=0, settled=True,
                  share_ss=300, share_pi=200)

    # Secu payment
    _seed_payment(db, tid, 30, amount=300, ptype="TPSV", customer_id=cust.id,
                  customer_cosium_id="C500", invoice_cosium_id=4001)
    # Mutuelle payment
    _seed_payment(db, tid, 31, amount=200, ptype="TPMV", customer_id=cust.id,
                  customer_cosium_id="C500", invoice_cosium_id=4001)
    # Client direct
    _seed_payment(db, tid, 32, amount=500, ptype="CB", customer_id=cust.id,
                  customer_cosium_id="C500", invoice_cosium_id=4001)

    result = reconcile_customer_dossier(db, tid, cust.id)
    assert result.total_secu == 300
    assert result.total_mutuelle == 200
    assert result.total_client == 500
    assert result.has_pec is True
    assert result.pec_status == "secu_et_mutuelle"

    # Also test classify_payment directly
    assert classify_payment("TPSV") == "secu"
    assert classify_payment("TPMV") == "mutuelle"
    assert classify_payment("CB") == "client"
    assert classify_payment("AV") == "avoir"
    assert classify_payment("ESP") == "client"


# -----------------------------------------------------------------------
# Test 6: Anomaly detected when payment sum > TTC
# -----------------------------------------------------------------------
def test_anomaly_overpayment(db, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _seed_customer(db, tid, "Sophie", "Petit", "C600")
    _seed_invoice(db, tid, 5001, "C600", total_ti=200, outstanding=0, settled=True)
    # Payment exceeds TTC
    _seed_payment(db, tid, 40, amount=300, ptype="CB", customer_id=cust.id,
                  customer_cosium_id="C600", invoice_cosium_id=5001)

    result = reconcile_customer_dossier(db, tid, cust.id)
    assert result.status == "incoherent"
    assert len(result.anomalies) > 0
    anomaly_types = [a.type for a in result.anomalies]
    assert "surpaiement" in anomaly_types or "surpaiement_global" in anomaly_types


# -----------------------------------------------------------------------
# Test 7: Reconciliation summary returns correct counts
# -----------------------------------------------------------------------
def test_reconciliation_summary(db, default_tenant: Tenant) -> None:
    tid = default_tenant.id

    # Create two customers: one settled, one en_attente
    cust1 = _seed_customer(db, tid, "Alice", "Roy", "C700")
    _seed_invoice(db, tid, 6001, "C700", total_ti=100, outstanding=0, settled=True)
    _seed_payment(db, tid, 50, amount=100, ptype="CB", customer_id=cust1.id,
                  customer_cosium_id="C700", invoice_cosium_id=6001)

    cust2 = _seed_customer(db, tid, "Bob", "Lefevre", "C701")
    _seed_invoice(db, tid, 6002, "C701", total_ti=200, outstanding=200, settled=False)

    # Reconcile both
    reconcile_customer_dossier(db, tid, cust1.id)
    reconcile_customer_dossier(db, tid, cust2.id)

    summary = get_reconciliation_summary(db, tid)
    assert summary.total_customers == 2
    assert summary.solde >= 1
    assert summary.en_attente >= 1


# -----------------------------------------------------------------------
# Test 8: Customer reconciliation includes all invoices
# -----------------------------------------------------------------------
def test_customer_reconciliation_includes_all_invoices(db, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    cust = _seed_customer(db, tid, "Emma", "Garcia", "C800")

    # Create 3 invoices + 1 quote
    _seed_invoice(db, tid, 7001, "C800", total_ti=100, outstanding=0, settled=True)
    _seed_invoice(db, tid, 7002, "C800", total_ti=200, outstanding=50, settled=False)
    _seed_invoice(db, tid, 7003, "C800", total_ti=300, outstanding=300, settled=False)
    _seed_invoice(db, tid, 7004, "C800", total_ti=150, inv_type="QUOTE")

    result = reconcile_customer_dossier(db, tid, cust.id)
    assert result.invoice_count == 3  # Only INVOICE type
    assert result.quote_count == 1
    assert len(result.invoices) == 3
    assert result.total_facture == 600  # 100 + 200 + 300
