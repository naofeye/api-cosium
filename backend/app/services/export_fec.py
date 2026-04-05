"""Service d'export FEC (Fichier des Ecritures Comptables) — reglementaire francais."""

import csv
import io
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import Facture, Payment

logger = get_logger("export_fec")

FEC_COLUMNS = [
    "JournalCode",
    "JournalLib",
    "EcritureNum",
    "EcritureDate",
    "CompteNum",
    "CompteLib",
    "CompAuxNum",
    "CompAuxLib",
    "PieceRef",
    "PieceDate",
    "EcritureLib",
    "Debit",
    "Credit",
    "EcritureLet",
    "DateLet",
    "ValidDate",
    "Montantdevise",
    "Idevise",
]


def _fmt_date(dt: datetime | date | None) -> str:
    """Format a date as YYYYMMDD (FEC standard)."""
    if dt is None:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%Y%m%d")
    return dt.strftime("%Y%m%d")


def _fmt_amount(value: float | None) -> str:
    """Format a decimal amount with comma separator (French FEC standard)."""
    if value is None or value == 0:
        return "0,00"
    return f"{value:.2f}".replace(".", ",")


def generate_fec(
    db: Session,
    tenant_id: int,
    date_from: date,
    date_to: date,
    siren: str = "000000000",
) -> bytes:
    """Generate a FEC-compliant tab-separated file (UTF-8 with BOM).

    The FEC contains two journals:
    - VE (Ventes) : one debit line (client account 411) + one credit line
      (revenue account 707) per invoice.
    - BQ (Banque) : one debit line (bank account 512) + one credit line
      (client account 411) per payment received.
    """
    # Fetch invoices in date range
    factures_q = (
        select(Facture)
        .where(
            Facture.tenant_id == tenant_id,
            Facture.date_emission >= datetime.combine(date_from, datetime.min.time()),
            Facture.date_emission <= datetime.combine(date_to, datetime.max.time()),
        )
        .order_by(Facture.date_emission, Facture.id)
    )
    factures = list(db.scalars(factures_q.limit(50000)).all())

    # Fetch payments in date range
    payments_q = (
        select(Payment)
        .where(
            Payment.tenant_id == tenant_id,
            Payment.date_paiement >= datetime.combine(date_from, datetime.min.time()),
            Payment.date_paiement <= datetime.combine(date_to, datetime.max.time()),
            Payment.status.in_(["recu", "paid"]),
        )
        .order_by(Payment.date_paiement, Payment.id)
    )
    payments = list(db.scalars(payments_q.limit(50000)).all())

    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")

    # Header row
    writer.writerow(FEC_COLUMNS)

    ecriture_num = 0

    # --- Journal VE (Ventes / Invoices) ---
    for facture in factures:
        ecriture_num += 1
        ecriture_id = f"VE{ecriture_num:06d}"
        emission_date = _fmt_date(facture.date_emission)
        montant_ttc = float(facture.montant_ttc) if facture.montant_ttc else 0.0

        # Debit line: client account (411)
        writer.writerow([
            "VE",                           # JournalCode
            "Journal des Ventes",           # JournalLib
            ecriture_id,                    # EcritureNum
            emission_date,                  # EcritureDate
            "411000",                       # CompteNum (client)
            "Clients",                      # CompteLib
            "",                             # CompAuxNum
            "",                             # CompAuxLib
            facture.numero,                 # PieceRef
            emission_date,                  # PieceDate
            f"Facture {facture.numero}",    # EcritureLib
            _fmt_amount(montant_ttc),       # Debit
            _fmt_amount(0),                 # Credit
            "",                             # EcritureLet
            "",                             # DateLet
            emission_date,                  # ValidDate
            _fmt_amount(montant_ttc),       # Montantdevise
            "EUR",                          # Idevise
        ])

        # Credit line: revenue account (707)
        montant_ht = float(facture.montant_ht) if facture.montant_ht else 0.0
        tva = float(facture.tva) if facture.tva else 0.0

        writer.writerow([
            "VE",
            "Journal des Ventes",
            ecriture_id,
            emission_date,
            "707000",
            "Ventes de marchandises",
            "",
            "",
            facture.numero,
            emission_date,
            f"Facture {facture.numero}",
            _fmt_amount(0),
            _fmt_amount(montant_ht),
            "",
            "",
            emission_date,
            _fmt_amount(montant_ht),
            "EUR",
        ])

        # TVA credit line (44571) if TVA > 0
        if tva > 0:
            writer.writerow([
                "VE",
                "Journal des Ventes",
                ecriture_id,
                emission_date,
                "445710",
                "TVA collectee",
                "",
                "",
                facture.numero,
                emission_date,
                f"TVA Facture {facture.numero}",
                _fmt_amount(0),
                _fmt_amount(tva),
                "",
                "",
                emission_date,
                _fmt_amount(tva),
                "EUR",
            ])

    # --- Journal BQ (Banque / Payments) ---
    for payment in payments:
        ecriture_num += 1
        ecriture_id = f"BQ{ecriture_num:06d}"
        paiement_date = _fmt_date(payment.date_paiement)
        amount = float(payment.amount_paid) if payment.amount_paid else 0.0
        ref = payment.reference_externe or f"PAY-{payment.id}"

        # Debit line: bank account (512)
        writer.writerow([
            "BQ",
            "Journal de Banque",
            ecriture_id,
            paiement_date,
            "512000",
            "Banque",
            "",
            "",
            ref,
            paiement_date,
            f"Paiement {ref}",
            _fmt_amount(amount),
            _fmt_amount(0),
            "",
            "",
            paiement_date,
            _fmt_amount(amount),
            "EUR",
        ])

        # Credit line: client account (411)
        writer.writerow([
            "BQ",
            "Journal de Banque",
            ecriture_id,
            paiement_date,
            "411000",
            "Clients",
            "",
            "",
            ref,
            paiement_date,
            f"Paiement {ref}",
            _fmt_amount(0),
            _fmt_amount(amount),
            "",
            "",
            paiement_date,
            _fmt_amount(amount),
            "EUR",
        ])

    content = output.getvalue()
    # UTF-8 with BOM as required by French tax authorities
    result = b"\xef\xbb\xbf" + content.encode("utf-8")

    logger.info(
        "fec_exported",
        tenant_id=tenant_id,
        date_from=str(date_from),
        date_to=str(date_to),
        factures_count=len(factures),
        payments_count=len(payments),
        ecriture_count=ecriture_num,
    )
    return result
