"""Reconciliation engine — links payments to invoices and reconciles customer dossiers.

Payment type classification:
  TPSV = securite sociale (tiers payant secu)
  TPMV = mutuelle (tiers payant mutuelle)
  CB, CHQ, ESP, ALMA, VIR = client direct
  AV = avoir / remboursement
"""

import json
import re
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.constants import (
    CONFIDENCE_CERTAIN,
    CONFIDENCE_INCERTAIN,
    CONFIDENCE_PARTIEL,
    CONFIDENCE_PROBABLE,
    RECON_EN_ATTENTE,
    RECON_INCOHERENT,
    RECON_INFO_INSUFFISANTE,
    RECON_PARTIELLEMENT_PAYE,
    RECON_SOLDE,
    RECON_SOLDE_NON_RAPPROCHE,
)
from app.core.logging import get_logger
from app.domain.schemas.reconciliation import (
    AnomalyItem,
    BatchReconciliationResult,
    DossierReconciliationResponse,
    InvoiceReconciliation,
    LinkPaymentsResult,
    PaymentMatch,
    ReconciliationSummary,
)
from app.repositories import client_repo, reconciliation_repo

logger = get_logger("reconciliation_service")

# Payment type → category mapping
_SECU_TYPES = {"TPSV"}
_MUTUELLE_TYPES = {"TPMV"}
_CLIENT_TYPES = {"CB", "CHQ", "ESP", "ALMA", "VIR"}
_AVOIR_TYPES = {"AV"}

# Tolerance for financial comparison (euros)
_TOLERANCE = Decimal("0.02")


def _normalize_name(name: str) -> str:
    """Normalize a name for fuzzy matching: lowercase, strip accents, remove punctuation."""
    if not name:
        return ""
    # NFD decomposition then strip combining marks
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Lowercase, strip extra whitespace, remove punctuation
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", ascii_str.lower())
    return " ".join(cleaned.split())


def _names_match(name_a: str, name_b: str) -> bool:
    """Check if two names match (exact normalized match or token subset)."""
    norm_a = _normalize_name(name_a)
    norm_b = _normalize_name(name_b)
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True
    # Token-based: all tokens of shorter name present in longer name
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    if len(tokens_a) < 2 or len(tokens_b) < 2:
        return False
    shorter, longer = (tokens_a, tokens_b) if len(tokens_a) <= len(tokens_b) else (tokens_b, tokens_a)
    return shorter.issubset(longer)


def _classify_payment(payment_type: str) -> str:
    """Classify a payment type into a category."""
    upper = payment_type.strip().upper()
    if upper in _SECU_TYPES:
        return "secu"
    if upper in _MUTUELLE_TYPES:
        return "mutuelle"
    if upper in _AVOIR_TYPES:
        return "avoir"
    return "client"


def _determine_reconciliation_status(
    *,
    total_facture: float,
    total_paid: float,
    total_outstanding: float,
    has_invoices: bool,
    has_payments: bool,
    has_unmatched: bool,
    has_anomalies: bool,
) -> tuple[str, str]:
    """Determine global reconciliation status and confidence level.

    Returns a (status, confidence) tuple based on financial totals and flags.
    Extracted from reconcile_customer_dossier for clarity and testability.
    """
    if not has_invoices:
        return RECON_INFO_INSUFFISANTE, CONFIDENCE_INCERTAIN

    if abs(total_outstanding) < _TOLERANCE:
        if has_unmatched:
            return RECON_SOLDE_NON_RAPPROCHE, CONFIDENCE_PROBABLE
        return RECON_SOLDE, CONFIDENCE_CERTAIN

    if total_paid > _TOLERANCE and total_outstanding > _TOLERANCE:
        confidence = CONFIDENCE_PROBABLE if not has_anomalies else CONFIDENCE_PARTIEL
        return RECON_PARTIELLEMENT_PAYE, confidence

    if total_paid < _TOLERANCE:
        return RECON_EN_ATTENTE, CONFIDENCE_CERTAIN

    return RECON_INCOHERENT, CONFIDENCE_INCERTAIN


def link_payments_to_customers(db: Session, tenant_id: int) -> LinkPaymentsResult:
    """Link CosiumPayments to Customers by matching issuer_name to customer name."""
    unlinked = reconciliation_repo.get_unlinked_payments(db, tenant_id)
    all_customers = reconciliation_repo.get_all_customers(db, tenant_id)

    # Build normalized name → customer mapping
    name_map: dict[str, int] = {}
    for cust in all_customers:
        full_name = f"{cust.last_name} {cust.first_name}"
        norm = _normalize_name(full_name)
        if norm:
            name_map[norm] = cust.id
        # Also index reversed order
        rev_name = f"{cust.first_name} {cust.last_name}"
        norm_rev = _normalize_name(rev_name)
        if norm_rev:
            name_map[norm_rev] = cust.id

    total = len(unlinked)
    newly_linked = 0

    for payment in unlinked:
        norm_issuer = _normalize_name(payment.issuer_name)
        if not norm_issuer:
            continue

        # Exact match first
        if norm_issuer in name_map:
            payment.customer_id = name_map[norm_issuer]
            newly_linked += 1
            continue

        # Token-based fuzzy match
        for name_key, cust_id in name_map.items():
            if _names_match(payment.issuer_name, name_key):
                payment.customer_id = cust_id
                newly_linked += 1
                break

    db.commit()

    # Count already-linked payments
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

    cosium_id = customer.cosium_id
    customer_name = f"{customer.last_name} {customer.first_name}"

    # Load invoices by type (use customer_id, not cosium_id)
    all_invoices = reconciliation_repo.get_invoices_by_customer(db, tenant_id, customer_id)

    invoices = [i for i in all_invoices if i.type == "INVOICE"]
    quotes = [i for i in all_invoices if i.type == "QUOTE"]
    credit_notes = [i for i in all_invoices if i.type == "CREDIT_NOTE"]

    # Load payments
    payments = reconciliation_repo.get_payments_by_customer(
        db, tenant_id, customer_id=customer_id, customer_cosium_id=cosium_id,
    )

    # Group payments by category
    secu_payments = [p for p in payments if _classify_payment(p.type) == "secu"]
    mutuelle_payments = [p for p in payments if _classify_payment(p.type) == "mutuelle"]
    client_payments = [p for p in payments if _classify_payment(p.type) == "client"]
    avoir_payments = [p for p in payments if _classify_payment(p.type) == "avoir"]

    total_secu = sum(p.amount for p in secu_payments)
    total_mutuelle = sum(p.amount for p in mutuelle_payments)
    total_client = sum(p.amount for p in client_payments)
    total_avoir = sum(p.amount for p in avoir_payments)
    total_paid = total_secu + total_mutuelle + total_client + total_avoir
    total_facture = sum(i.total_ti for i in invoices)
    total_outstanding = sum(i.outstanding_balance for i in invoices)

    # Determine PEC status
    has_pec = any(i.share_social_security > 0 or i.share_private_insurance > 0 for i in invoices)
    pec_status = None
    if has_pec:
        if total_secu > 0 and total_mutuelle > 0:
            pec_status = "secu_et_mutuelle"
        elif total_secu > 0:
            pec_status = "secu_uniquement"
        elif total_mutuelle > 0:
            pec_status = "mutuelle_uniquement"
        else:
            pec_status = "en_attente_pec"

    # Per-invoice reconciliation
    invoice_details: list[InvoiceReconciliation] = []
    all_anomalies: list[AnomalyItem] = []

    # Simple matching: distribute payments across invoices by date proximity
    # Since invoice_cosium_id is NULL on payments, we match all customer payments to all invoices
    used_payment_ids: set[int] = set()

    for inv in invoices:
        inv_payments: list[PaymentMatch] = []

        # Match payments to this invoice by invoice_cosium_id if available
        direct_matches = [p for p in payments if p.invoice_cosium_id == inv.cosium_id and p.id not in used_payment_ids]
        for p in direct_matches:
            cat = _classify_payment(p.type)
            inv_payments.append(PaymentMatch(
                payment_id=p.id, cosium_id=p.cosium_id, amount=p.amount,
                type=p.type, category=cat, issuer_name=p.issuer_name,
                due_date=p.due_date, payment_number=p.payment_number,
            ))
            used_payment_ids.add(p.id)

        inv_paid = sum(pm.amount for pm in inv_payments)
        inv_secu = sum(pm.amount for pm in inv_payments if pm.category == "secu")
        inv_mut = sum(pm.amount for pm in inv_payments if pm.category == "mutuelle")
        inv_cli = sum(pm.amount for pm in inv_payments if pm.category == "client")
        inv_av = sum(pm.amount for pm in inv_payments if pm.category == "avoir")

        # Determine invoice status
        if inv.settled or abs(inv.outstanding_balance) < _TOLERANCE:
            inv_status = RECON_SOLDE
        elif inv_paid > _TOLERANCE and inv.outstanding_balance > _TOLERANCE:
            inv_status = RECON_PARTIELLEMENT_PAYE
        elif inv_paid < _TOLERANCE and inv.total_ti > _TOLERANCE:
            inv_status = RECON_EN_ATTENTE
        else:
            inv_status = RECON_EN_ATTENTE

        # Detect anomalies
        inv_anomalies: list[AnomalyItem] = []
        if inv_paid > inv.total_ti + _TOLERANCE:
            inv_anomalies.append(AnomalyItem(
                type="surpaiement",
                severity="error",
                message=f"Paiements ({inv_paid:.2f} EUR) superieurs au TTC ({inv.total_ti:.2f} EUR)",
                invoice_number=inv.invoice_number,
                amount=inv_paid - inv.total_ti,
            ))
            inv_status = RECON_INCOHERENT

        invoice_details.append(InvoiceReconciliation(
            invoice_id=inv.id, cosium_id=inv.cosium_id,
            invoice_number=inv.invoice_number, invoice_date=inv.invoice_date,
            total_ti=inv.total_ti, outstanding_balance=inv.outstanding_balance,
            share_social_security=inv.share_social_security,
            share_private_insurance=inv.share_private_insurance,
            settled=inv.settled, payments=inv_payments,
            total_paid=inv_paid, paid_secu=inv_secu, paid_mutuelle=inv_mut,
            paid_client=inv_cli, paid_avoir=inv_av,
            status=inv_status, anomalies=inv_anomalies,
        ))
        all_anomalies.extend(inv_anomalies)

    # Check for unmatched payments
    unmatched_payments = [p for p in payments if p.id not in used_payment_ids]
    if unmatched_payments and invoices:
        # Payments exist but could not be linked to a specific invoice
        unmatched_total = sum(p.amount for p in unmatched_payments)
        all_anomalies.append(AnomalyItem(
            type="paiements_non_rapproches",
            severity="info",
            message=f"{len(unmatched_payments)} paiement(s) non rapproche(s) pour un total de {unmatched_total:.2f} EUR",
            amount=unmatched_total,
        ))

    # Determine global status via state machine
    global_status, confidence = _determine_reconciliation_status(
        total_facture=total_facture,
        total_paid=total_paid,
        total_outstanding=total_outstanding,
        has_invoices=bool(invoices),
        has_payments=bool(payments),
        has_unmatched=bool(unmatched_payments),
        has_anomalies=bool(all_anomalies),
    )

    # Check for global anomalies
    if total_paid > total_facture + _TOLERANCE and invoices:
        all_anomalies.append(AnomalyItem(
            type="surpaiement_global",
            severity="error",
            message=f"Total paye ({total_paid:.2f} EUR) superieur au total facture ({total_facture:.2f} EUR)",
            amount=total_paid - total_facture,
        ))
        global_status = RECON_INCOHERENT
        confidence = CONFIDENCE_INCERTAIN

    # Build explanation
    explanation_parts = []
    explanation_parts.append(f"{len(invoices)} facture(s) pour {total_facture:.2f} EUR TTC.")
    if total_outstanding > _TOLERANCE:
        explanation_parts.append(f"Solde restant du : {total_outstanding:.2f} EUR.")
    else:
        explanation_parts.append("Toutes les factures sont soldees.")
    if total_secu > 0:
        explanation_parts.append(f"Secu : {total_secu:.2f} EUR.")
    if total_mutuelle > 0:
        explanation_parts.append(f"Mutuelle : {total_mutuelle:.2f} EUR.")
    if total_client > 0:
        explanation_parts.append(f"Client : {total_client:.2f} EUR.")
    if total_avoir > 0:
        explanation_parts.append(f"Avoirs : {total_avoir:.2f} EUR.")
    explanation = " ".join(explanation_parts)

    # Persist to DB
    recon_data = {
        "status": global_status,
        "confidence": confidence,
        "total_facture": total_facture,
        "total_outstanding": total_outstanding,
        "total_paid": total_paid,
        "total_secu": total_secu,
        "total_mutuelle": total_mutuelle,
        "total_client": total_client,
        "total_avoir": total_avoir,
        "invoice_count": len(invoices),
        "payment_count": len(payments),
        "quote_count": len(quotes),
        "credit_note_count": len(credit_notes),
        "has_pec": has_pec,
        "pec_status": pec_status,
        "detail_json": json.dumps([d.model_dump(mode="json") for d in invoice_details]),
        "anomalies": json.dumps([a.model_dump() for a in all_anomalies]),
        "explanation": explanation,
        "reconciled_at": datetime.now(UTC),
    }
    recon = reconciliation_repo.upsert_reconciliation(db, tenant_id, customer_id, recon_data)

    return DossierReconciliationResponse(
        id=recon.id,
        tenant_id=tenant_id,
        customer_id=customer_id,
        customer_name=customer_name,
        status=global_status,
        confidence=confidence,
        total_facture=total_facture,
        total_outstanding=total_outstanding,
        total_paid=total_paid,
        total_secu=total_secu,
        total_mutuelle=total_mutuelle,
        total_client=total_client,
        total_avoir=total_avoir,
        invoice_count=len(invoices),
        payment_count=len(payments),
        quote_count=len(quotes),
        credit_note_count=len(credit_notes),
        has_pec=has_pec,
        pec_status=pec_status,
        invoices=invoice_details,
        anomalies=all_anomalies,
        explanation=explanation,
        reconciled_at=recon.reconciled_at,
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
        except Exception:
            logger.exception(
                "reconciliation_failed",
                tenant_id=tenant_id,
                customer_id=customer.id,
            )

    # Build summary from DB
    summary = get_reconciliation_summary(db, tenant_id)

    return BatchReconciliationResult(
        total_processed=total_processed,
        summary=summary,
        anomaly_count=anomaly_count,
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
    """Return paginated list of non-settled reconciliations (partiellement_paye, en_attente, incoherent)."""
    unsettled_statuses = [RECON_PARTIELLEMENT_PAYE, RECON_EN_ATTENTE, RECON_INCOHERENT]
    all_items = []
    total = 0
    for status in unsettled_statuses:
        items, count = reconciliation_repo.get_reconciliations_by_status(
            db, tenant_id, status, page, page_size,
        )
        all_items.extend(items)
        total += count

    results = []
    for recon in all_items[:page_size]:
        results.append({
            "customer_id": recon.customer_id,
            "status": recon.status,
            "total_facture": recon.total_facture,
            "total_outstanding": recon.total_outstanding,
            "total_paid": recon.total_paid,
            "explanation": recon.explanation,
        })
    return {"items": results, "total": total, "page": page, "page_size": page_size}


def get_customer_reconciliation(
    db: Session, tenant_id: int, customer_id: int,
) -> DossierReconciliationResponse | None:
    """Get stored reconciliation for a customer, or compute it on the fly."""
    recon = reconciliation_repo.get_reconciliation_by_customer(db, tenant_id, customer_id)
    if recon is None:
        # Compute on-demand
        return reconcile_customer_dossier(db, tenant_id, customer_id)

    # Reconstruct response from stored data
    customer = client_repo.get_by_id(db, customer_id, tenant_id)
    customer_name = f"{customer.last_name} {customer.first_name}" if customer else ""

    invoices = json.loads(recon.detail_json) if recon.detail_json else []
    anomalies = json.loads(recon.anomalies) if recon.anomalies else []

    return DossierReconciliationResponse(
        id=recon.id,
        tenant_id=recon.tenant_id,
        customer_id=recon.customer_id,
        customer_name=customer_name,
        status=recon.status,
        confidence=recon.confidence,
        total_facture=recon.total_facture,
        total_outstanding=recon.total_outstanding,
        total_paid=recon.total_paid,
        total_secu=recon.total_secu,
        total_mutuelle=recon.total_mutuelle,
        total_client=recon.total_client,
        total_avoir=recon.total_avoir,
        invoice_count=recon.invoice_count,
        payment_count=recon.payment_count,
        quote_count=recon.quote_count,
        credit_note_count=recon.credit_note_count,
        has_pec=recon.has_pec,
        pec_status=recon.pec_status,
        invoices=[InvoiceReconciliation(**i) for i in invoices],
        anomalies=[AnomalyItem(**a) for a in anomalies],
        explanation=recon.explanation or "",
        reconciled_at=recon.reconciled_at,
    )
