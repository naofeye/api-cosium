"""Client 360 — Financial data aggregation (invoices, payments, balance, aging)."""

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.client_360 import (
    CosiumInvoiceSummary,
    FinancialSummary,
    PrescriptionWarning,
)
from app.models import Case
from app.models.cosium_data import CosiumInvoice

logger = get_logger("client_360_finance")


def fetch_cosium_invoices(
    db: Session,
    tenant_id: int,
    client_id: int,
    client_full_name: str,
) -> tuple[list[CosiumInvoiceSummary], list]:
    """Fetch Cosium invoices for a client. Returns (summaries, raw_rows)."""
    cosium_inv_query = select(CosiumInvoice).where(
        CosiumInvoice.tenant_id == tenant_id,
    )
    cosium_invoices_raw = db.scalars(
        cosium_inv_query.where(
            (CosiumInvoice.customer_id == client_id)
            | (sa_func.upper(CosiumInvoice.customer_name).contains(client_full_name.upper()))
        )
        .order_by(CosiumInvoice.invoice_date.desc())
        .limit(50)
    ).all()

    cosium_invoices_list = [
        CosiumInvoiceSummary(
            cosium_id=ci.cosium_id,
            invoice_number=ci.invoice_number,
            invoice_date=str(ci.invoice_date) if ci.invoice_date else None,
            type=ci.type,
            total_ti=ci.total_ti,
            outstanding_balance=ci.outstanding_balance,
            share_social_security=ci.share_social_security,
            share_private_insurance=ci.share_private_insurance,
            settled=ci.settled,
        )
        for ci in cosium_invoices_raw
    ]
    return cosium_invoices_list, list(cosium_invoices_raw)


def aggregate_case_financials(cases: list[Case]) -> dict:
    """Aggregate financial data from cases: devis, factures, paiements, PEC.

    Returns dict with keys: devis, factures, paiements, pec,
    total_facture, total_paye.
    """
    devis_list: list[dict] = []
    factures: list[dict] = []
    paiements: list[dict] = []
    pec_list: list[dict] = []
    total_facture = 0.0
    total_paye = 0.0

    for case in cases:
        for d in case.devis:
            devis_list.append(
                {
                    "id": d.id,
                    "numero": d.numero,
                    "statut": d.status,
                    "montant_ttc": float(d.montant_ttc),
                    "reste_a_charge": float(d.reste_a_charge),
                }
            )

        for f in case.factures:
            factures.append(
                {
                    "id": f.id,
                    "numero": f.numero,
                    "statut": f.status,
                    "montant_ttc": float(f.montant_ttc),
                    "date_emission": str(f.date_emission),
                }
            )
            total_facture += float(f.montant_ttc)

        for p in case.payments:
            paiements.append(
                {
                    "id": p.id,
                    "payeur": p.payer_type,
                    "mode": p.mode_paiement,
                    "montant_du": float(p.amount_due),
                    "montant_paye": float(p.amount_paid),
                    "statut": p.status,
                }
            )
            total_paye += float(p.amount_paid)

        for p in case.pec_requests:
            pec_list.append(
                {
                    "id": p.id,
                    "statut": p.status,
                    "montant_demande": float(p.montant_demande),
                    "montant_accorde": float(p.montant_accorde) if p.montant_accorde else None,
                }
            )

    return {
        "devis": devis_list,
        "factures": factures,
        "paiements": paiements,
        "pec": pec_list,
        "total_facture": total_facture,
        "total_paye": total_paye,
    }


def build_financial_summary(total_facture: float, total_paye: float) -> FinancialSummary:
    """Build a FinancialSummary from totals."""
    reste_du = round(max(total_facture - total_paye, 0), 2)
    taux = round(total_paye / total_facture * 100, 1) if total_facture > 0 else 0
    return FinancialSummary(
        total_facture=round(total_facture, 2),
        total_paye=round(total_paye, 2),
        reste_du=reste_du,
        taux_recouvrement=taux,
    )


def compute_total_ca_cosium(cosium_invoices_raw: list) -> float:
    """Compute total CA from Cosium invoices (INVOICE + CREDIT_NOTE)."""
    return sum(
        ci.total_ti for ci in cosium_invoices_raw
        if ci.type in ("INVOICE", "CREDIT_NOTE")
    )


def build_prescription_warning(
    prescriptions: list,
) -> PrescriptionWarning | None:
    """Check if latest prescription is older than 2 years."""
    if not prescriptions:
        return None
    latest_rx_date_str = prescriptions[0].prescription_date
    if not latest_rx_date_str:
        return None
    try:
        from datetime import UTC, datetime

        latest_rx_date = datetime.strptime(latest_rx_date_str[:10], "%Y-%m-%d")
        days_since = (datetime.now(UTC).replace(tzinfo=None) - latest_rx_date).days
        if days_since > 730:
            return PrescriptionWarning(
                expired=True,
                latest_date=latest_rx_date_str[:10],
                days_since=days_since,
                message=(
                    f"Ordonnance de plus de 2 ans "
                    f"(derniere : {latest_rx_date.strftime('%d/%m/%Y')}, "
                    f"il y a {days_since} jours). "
                    f"Pensez a contacter le client pour un renouvellement."
                ),
            )
    except (ValueError, TypeError):
        pass
    return None
