"""Internal reconciliation computation helpers.

Extracted from reconciliation_service.py to keep files under 300 lines.
Contains: payment aggregation, per-invoice reconciliation builder.
"""

from app.core.constants import RECON_INCOHERENT
from app.domain.schemas.reconciliation import (
    AnomalyItem,
    InvoiceReconciliation,
    PaymentMatch,
)
from app.services._reconciliation_helpers import (
    classify_payment,
    detect_overpayment_anomaly,
    determine_invoice_status,
)


def aggregate_payments_by_category(payments: list) -> dict[str, float]:
    """Calcule les totaux par categorie (secu/mutuelle/client/avoir)."""
    totals = {"secu": 0.0, "mutuelle": 0.0, "client": 0.0, "avoir": 0.0}
    for p in payments:
        totals[classify_payment(p.type)] += p.amount
    return totals


def build_invoice_reconciliation(
    inv,
    payments: list,
    used_payment_ids: set[int],
) -> tuple[InvoiceReconciliation, list[AnomalyItem]]:
    """Reconcile une facture avec ses paiements directs (matches sur invoice_cosium_id)."""
    inv_payments: list[PaymentMatch] = []
    direct_matches = [
        p for p in payments
        if p.invoice_cosium_id == inv.cosium_id and p.id not in used_payment_ids
    ]
    for p in direct_matches:
        cat = classify_payment(p.type)
        inv_payments.append(PaymentMatch(
            payment_id=p.id, cosium_id=p.cosium_id, amount=p.amount,
            type=p.type, category=cat, issuer_name=p.issuer_name,
            due_date=p.due_date, payment_number=p.payment_number,
        ))
        used_payment_ids.add(p.id)

    inv_paid = sum(pm.amount for pm in inv_payments)
    by_cat = {
        cat: sum(pm.amount for pm in inv_payments if pm.category == cat)
        for cat in ("secu", "mutuelle", "client", "avoir")
    }

    inv_status = determine_invoice_status(
        settled=inv.settled,
        outstanding=inv.outstanding_balance,
        paid=inv_paid,
        total_ti=inv.total_ti,
    )
    anomaly = detect_overpayment_anomaly(
        paid=inv_paid, total_ti=inv.total_ti, invoice_number=inv.invoice_number,
    )
    inv_anomalies = [anomaly] if anomaly else []
    if anomaly:
        inv_status = RECON_INCOHERENT

    return InvoiceReconciliation(
        invoice_id=inv.id, cosium_id=inv.cosium_id,
        invoice_number=inv.invoice_number, invoice_date=inv.invoice_date,
        total_ti=inv.total_ti, outstanding_balance=inv.outstanding_balance,
        share_social_security=inv.share_social_security,
        share_private_insurance=inv.share_private_insurance,
        settled=inv.settled, payments=inv_payments,
        total_paid=inv_paid,
        paid_secu=by_cat["secu"], paid_mutuelle=by_cat["mutuelle"],
        paid_client=by_cat["client"], paid_avoir=by_cat["avoir"],
        status=inv_status, anomalies=inv_anomalies,
    ), inv_anomalies
