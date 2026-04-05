"""Service d'export CSV, Excel et FEC (Fichier des Ecritures Comptables)."""

import csv
import io
from datetime import date, datetime

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import (
    AuditLog,
    Campaign,
    Customer,
    Devis,
    Facture,
    Payment,
    PecRequest,
    Reminder,
)

logger = get_logger("export_service")

ENTITY_CONFIGS: dict[str, dict] = {
    "clients": {
        "model": Customer,
        "columns": ["id", "first_name", "last_name", "email", "phone", "city", "postal_code", "created_at"],
        "headers": ["ID", "Prenom", "Nom", "Email", "Telephone", "Ville", "Code postal", "Date creation"],
    },
    "factures": {
        "model": Facture,
        "columns": ["id", "numero", "montant_ht", "tva", "montant_ttc", "status", "date_emission", "created_at"],
        "headers": ["ID", "Numero", "Montant HT", "TVA", "Montant TTC", "Statut", "Date emission", "Date creation"],
    },
    "paiements": {
        "model": Payment,
        "columns": [
            "id",
            "case_id",
            "payer_type",
            "mode_paiement",
            "amount_due",
            "amount_paid",
            "status",
            "created_at",
        ],
        "headers": ["ID", "Dossier", "Type payeur", "Mode", "Montant du", "Montant paye", "Statut", "Date"],
    },
    "devis": {
        "model": Devis,
        "columns": [
            "id",
            "numero",
            "status",
            "montant_ht",
            "tva",
            "montant_ttc",
            "part_secu",
            "part_mutuelle",
            "reste_a_charge",
            "created_at",
        ],
        "headers": ["ID", "Numero", "Statut", "HT", "TVA", "TTC", "Part secu", "Part mutuelle", "RAC", "Date"],
    },
    "pec": {
        "model": PecRequest,
        "columns": ["id", "case_id", "organization_id", "montant_demande", "montant_accorde", "status", "created_at"],
        "headers": ["ID", "Dossier", "Organisme", "Montant demande", "Montant accorde", "Statut", "Date"],
    },
    "relances": {
        "model": Reminder,
        "columns": ["id", "target_type", "target_id", "channel", "status", "content", "created_at"],
        "headers": ["ID", "Type cible", "ID cible", "Canal", "Statut", "Contenu", "Date"],
    },
    "campagnes": {
        "model": Campaign,
        "columns": ["id", "name", "channel", "status", "sent_at", "created_at"],
        "headers": ["ID", "Nom", "Canal", "Statut", "Date envoi", "Date creation"],
    },
    "audit_logs": {
        "model": AuditLog,
        "columns": ["id", "user_id", "action", "entity_type", "entity_id", "created_at"],
        "headers": ["ID", "Utilisateur", "Action", "Type entite", "ID entite", "Date"],
    },
}


def _get_rows(
    db: Session, tenant_id: int, entity_type: str, date_from: datetime | None = None, date_to: datetime | None = None
) -> list[list]:
    config = ENTITY_CONFIGS.get(entity_type)
    if not config:
        return []

    model = config["model"]
    columns = config["columns"]

    q = select(model)
    if hasattr(model, "tenant_id"):
        q = q.where(model.tenant_id == tenant_id)
    if date_from and hasattr(model, "created_at"):
        q = q.where(model.created_at >= date_from)
    if date_to and hasattr(model, "created_at"):
        q = q.where(model.created_at <= date_to)

    items = db.scalars(q.order_by(model.id.desc())).all()
    rows = []
    for item in items:
        row = []
        for col in columns:
            val = getattr(item, col, "")
            if isinstance(val, datetime):
                val = val.strftime("%d/%m/%Y %H:%M")
            elif val is None:
                val = ""
            row.append(val)
        rows.append(row)
    return rows


def export_to_csv(
    db: Session, tenant_id: int, entity_type: str, date_from: datetime | None = None, date_to: datetime | None = None
) -> bytes:
    config = ENTITY_CONFIGS.get(entity_type)
    if not config:
        return b""

    rows = _get_rows(db, tenant_id, entity_type, date_from, date_to)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(config["headers"])
    writer.writerows(rows)

    logger.info("csv_exported", tenant_id=tenant_id, entity_type=entity_type, rows=len(rows))
    return output.getvalue().encode("utf-8-sig")


def export_to_xlsx(
    db: Session, tenant_id: int, entity_type: str, date_from: datetime | None = None, date_to: datetime | None = None
) -> bytes:
    config = ENTITY_CONFIGS.get(entity_type)
    if not config:
        return b""

    rows = _get_rows(db, tenant_id, entity_type, date_from, date_to)
    wb = Workbook()
    ws = wb.active
    ws.title = entity_type.capitalize()
    ws.append(config["headers"])
    for row in rows:
        ws.append([str(v) for v in row])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    logger.info("xlsx_exported", tenant_id=tenant_id, entity_type=entity_type, rows=len(rows))
    return output.getvalue()


# ---------------------------------------------------------------------------
# FEC (Fichier des Ecritures Comptables) — export reglementaire francais
# ---------------------------------------------------------------------------

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
    factures = list(db.scalars(factures_q).all())

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
    payments = list(db.scalars(payments_q).all())

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
