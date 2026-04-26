"""Reconciliation engine — links payments to invoices and reconciles customer dossiers.

Payment type classification:
  TPSV = securite sociale (tiers payant secu)
  TPMV = mutuelle (tiers payant mutuelle)
  CB, CHQ, ESP, ALMA, VIR = client direct
  AV = avoir / remboursement

Helpers internes : `_reconciliation_helpers.py`.
"""

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.constants import (
    CONFIDENCE_INCERTAIN,
    RECON_EN_ATTENTE,
    RECON_INCOHERENT,
    RECON_PARTIELLEMENT_PAYE,
)
from app.core.logging import get_logger
from app.domain.schemas.reconciliation import (
    AnomalyItem,
    BatchReconciliationResult,
    DossierReconciliationResponse,
    InvoiceReconciliation,
    LinkPaymentsResult,
    ReconciliationSummary,
)
from app.repositories import client_repo, reconciliation_repo

# Re-export helpers for backward compatibility — callers (including tests)
# importing from reconciliation_service continue to work.
from app.services._reconciliation_helpers import (  # noqa: F401
    TOLERANCE,
    build_explanation,
    classify_payment,
    detect_overpayment_anomaly,
    determine_invoice_status,
    determine_pec_status,
    determine_reconciliation_status,
    names_match,
    normalize_name,
)
from app.services.reconciliation_helpers import (
    aggregate_payments_by_category as _aggregate_payments_by_category,
)
from app.services.reconciliation_helpers import (
    build_invoice_reconciliation as _build_invoice_reconciliation,
)

logger = get_logger("reconciliation_service")


def link_payments_to_customers(db: Session, tenant_id: int) -> LinkPaymentsResult:
    """Link CosiumPayments to Customers by matching issuer_name to customer name."""
    unlinked = reconciliation_repo.get_unlinked_payments(db, tenant_id)
    all_customers = reconciliation_repo.get_all_customers(db, tenant_id)

    # Build normalized name → customer mapping (both name orders)
    name_map: dict[str, int] = {}
    for cust in all_customers:
        for full_name in (f"{cust.last_name} {cust.first_name}", f"{cust.first_name} {cust.last_name}"):
            norm = normalize_name(full_name)
            if norm:
                name_map[norm] = cust.id

    total = len(unlinked)
    newly_linked = 0
    for payment in unlinked:
        norm_issuer = normalize_name(payment.issuer_name)
        if not norm_issuer:
            continue
        if norm_issuer in name_map:
            payment.customer_id = name_map[norm_issuer]
            newly_linked += 1
            continue
        for name_key, cust_id in name_map.items():
            if names_match(payment.issuer_name, name_key):
                payment.customer_id = cust_id
                newly_linked += 1
                break

    db.commit()
    total_payments_count = reconciliation_repo.count_payments(db, tenant_id)
    already_linked = total_payments_count - total

    logger.info(
        "payments_linked_to_customers",
        tenant_id=tenant_id,
        total=total,
        newly_linked=newly_linked,
        unmatched=total - newly_linked,
    )
    return LinkPaymentsResult(
        total_payments=total_payments_count,
        already_linked=already_linked,
        newly_linked=newly_linked,
        unmatched=total - newly_linked,
    )


def reconcile_customer_dossier(
    db: Session, tenant_id: int, customer_id: int,
) -> DossierReconciliationResponse:
    """Reconcile all financial data for a single customer."""
    from app.core.exceptions import NotFoundError

    customer = client_repo.get_by_id(db, customer_id, tenant_id)
    if not customer:
        raise NotFoundError("Customer", customer_id)
    customer_name = f"{customer.last_name} {customer.first_name}"

    all_invoices = reconciliation_repo.get_invoices_by_customer(db, tenant_id, customer_id)
    invoices = [i for i in all_invoices if i.type == "INVOICE"]
    quotes = [i for i in all_invoices if i.type == "QUOTE"]
    credit_notes = [i for i in all_invoices if i.type == "CREDIT_NOTE"]

    payments = reconciliation_repo.get_payments_by_customer(
        db, tenant_id, customer_id=customer_id, customer_cosium_id=customer.cosium_id,
    )

    totals_by_cat = _aggregate_payments_by_category(payments)
    total_paid = sum(totals_by_cat.values())
    total_facture = sum(i.total_ti for i in invoices)
    total_outstanding = sum(i.outstanding_balance for i in invoices)
    pec_status = determine_pec_status(invoices, totals_by_cat["secu"], totals_by_cat["mutuelle"])
    has_pec = pec_status is not None

    invoice_details: list[InvoiceReconciliation] = []
    all_anomalies: list[AnomalyItem] = []
    used_payment_ids: set[int] = set()
    for inv in invoices:
        detail, anomalies = _build_invoice_reconciliation(inv, payments, used_payment_ids)
        invoice_details.append(detail)
        all_anomalies.extend(anomalies)

    unmatched_payments = [p for p in payments if p.id not in used_payment_ids]
    if unmatched_payments and invoices:
        unmatched_total = sum(p.amount for p in unmatched_payments)
        all_anomalies.append(AnomalyItem(
            type="paiements_non_rapproches", severity="info",
            message=(
                f"{len(unmatched_payments)} paiement(s) non rapproche(s) "
                f"pour un total de {unmatched_total:.2f} EUR"
            ),
            amount=unmatched_total,
        ))

    global_status, confidence = determine_reconciliation_status(
        total_facture=total_facture, total_paid=total_paid,
        total_outstanding=total_outstanding,
        has_invoices=bool(invoices), has_payments=bool(payments),
        has_unmatched=bool(unmatched_payments), has_anomalies=bool(all_anomalies),
    )

    if total_paid > total_facture + TOLERANCE and invoices:
        all_anomalies.append(AnomalyItem(
            type="surpaiement_global", severity="error",
            message=(
                f"Total paye ({total_paid:.2f} EUR) superieur "
                f"au total facture ({total_facture:.2f} EUR)"
            ),
            amount=total_paid - total_facture,
        ))
        global_status = RECON_INCOHERENT
        confidence = CONFIDENCE_INCERTAIN

    explanation = build_explanation(
        invoice_count=len(invoices),
        total_facture=total_facture, total_outstanding=total_outstanding,
        total_secu=totals_by_cat["secu"], total_mutuelle=totals_by_cat["mutuelle"],
        total_client=totals_by_cat["client"], total_avoir=totals_by_cat["avoir"],
    )

    recon = reconciliation_repo.upsert_reconciliation(db, tenant_id, customer_id, {
        "status": global_status, "confidence": confidence,
        "total_facture": total_facture,
        "total_outstanding": total_outstanding, "total_paid": total_paid,
        "total_secu": totals_by_cat["secu"], "total_mutuelle": totals_by_cat["mutuelle"],
        "total_client": totals_by_cat["client"], "total_avoir": totals_by_cat["avoir"],
        "invoice_count": len(invoices), "payment_count": len(payments),
        "quote_count": len(quotes), "credit_note_count": len(credit_notes),
        "has_pec": has_pec, "pec_status": pec_status,
        "detail_json": json.dumps([d.model_dump(mode="json") for d in invoice_details]),
        "anomalies": json.dumps([a.model_dump() for a in all_anomalies]),
        "explanation": explanation, "reconciled_at": datetime.now(UTC),
    })

    return DossierReconciliationResponse(
        id=recon.id, tenant_id=tenant_id, customer_id=customer_id, customer_name=customer_name,
        status=global_status, confidence=confidence,
        total_facture=total_facture, total_outstanding=total_outstanding, total_paid=total_paid,
        total_secu=totals_by_cat["secu"], total_mutuelle=totals_by_cat["mutuelle"],
        total_client=totals_by_cat["client"], total_avoir=totals_by_cat["avoir"],
        invoice_count=len(invoices), payment_count=len(payments),
        quote_count=len(quotes), credit_note_count=len(credit_notes),
        has_pec=has_pec, pec_status=pec_status,
        invoices=invoice_details, anomalies=all_anomalies,
        explanation=explanation, reconciled_at=recon.reconciled_at,
    )


def reconcile_all_customers(db: Session, tenant_id: int) -> BatchReconciliationResult:
    """Reconcile all customers that have invoices."""
    customers = reconciliation_repo.get_customers_with_invoices(db, tenant_id)
    total_processed = 0
    anomaly_count = 0
    for customer in customers:
        try:
            result = reconcile_customer_dossier(db, tenant_id, customer.id)
            total_processed += 1
            anomaly_count += len(result.anomalies)
        except Exception as exc:
            logger.exception(
                "reconciliation_failed",
                tenant_id=tenant_id,
                customer_id=customer.id,
                error=str(exc),
            )

    summary = get_reconciliation_summary(db, tenant_id)
    return BatchReconciliationResult(
        total_processed=total_processed, summary=summary, anomaly_count=anomaly_count,
    )


def get_reconciliation_summary(db: Session, tenant_id: int) -> ReconciliationSummary:
    """Build summary from persisted reconciliation data."""
    rows = reconciliation_repo.get_reconciliation_summary(db, tenant_id)
    summary = ReconciliationSummary(total_customers=0)
    for status, count, total_fac, total_out, total_pd in rows:
        summary.total_customers += count
        setattr(summary, status, count)
        summary.total_facture += total_fac or 0
        summary.total_outstanding += total_out or 0
        summary.total_paid += total_pd or 0
    return summary


def get_unsettled_reconciliations(
    db: Session, tenant_id: int, page: int = 1, page_size: int = 25,
) -> dict:
    """Return paginated list of non-settled reconciliations."""
    unsettled_statuses = [RECON_PARTIELLEMENT_PAYE, RECON_EN_ATTENTE, RECON_INCOHERENT]
    all_items = []
    total = 0
    for status in unsettled_statuses:
        items, count = reconciliation_repo.get_reconciliations_by_status(
            db, tenant_id, status, page, page_size,
        )
        all_items.extend(items)
        total += count

    results = [{
        "customer_id": r.customer_id, "status": r.status,
        "total_facture": r.total_facture, "total_outstanding": r.total_outstanding,
        "total_paid": r.total_paid, "explanation": r.explanation,
    } for r in all_items[:page_size]]
    return {"items": results, "total": total, "page": page, "page_size": page_size}


def get_customer_reconciliation(
    db: Session, tenant_id: int, customer_id: int,
) -> DossierReconciliationResponse | None:
    """Get stored reconciliation for a customer, or compute it on the fly."""
    recon = reconciliation_repo.get_reconciliation_by_customer(db, tenant_id, customer_id)
    if recon is None:
        return reconcile_customer_dossier(db, tenant_id, customer_id)

    customer = client_repo.get_by_id(db, customer_id, tenant_id)
    customer_name = f"{customer.last_name} {customer.first_name}" if customer else ""

    invoices = json.loads(recon.detail_json) if recon.detail_json else []
    anomalies = json.loads(recon.anomalies) if recon.anomalies else []

    return DossierReconciliationResponse(
        id=recon.id, tenant_id=recon.tenant_id, customer_id=recon.customer_id,
        customer_name=customer_name, status=recon.status, confidence=recon.confidence,
        total_facture=recon.total_facture, total_outstanding=recon.total_outstanding,
        total_paid=recon.total_paid,
        total_secu=recon.total_secu, total_mutuelle=recon.total_mutuelle,
        total_client=recon.total_client, total_avoir=recon.total_avoir,
        invoice_count=recon.invoice_count, payment_count=recon.payment_count,
        quote_count=recon.quote_count, credit_note_count=recon.credit_note_count,
        has_pec=recon.has_pec, pec_status=recon.pec_status,
        invoices=[InvoiceReconciliation(**i) for i in invoices],
        anomalies=[AnomalyItem(**a) for a in anomalies],
        explanation=recon.explanation or "",
        reconciled_at=recon.reconciled_at,
    )
