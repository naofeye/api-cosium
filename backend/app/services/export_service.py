"""Service d'export CSV, Excel, FEC, PDF et Balance Clients."""

import csv
import io
from datetime import UTC, date, datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
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
from app.models.cosium_data import CosiumInvoice

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


# ---------------------------------------------------------------------------
# Balance Clients — qui doit quoi
# ---------------------------------------------------------------------------

def _get_balance_rows(
    db: Session,
    tenant_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[dict]:
    """Return aggregated balance data per customer from CosiumInvoice."""
    q = (
        select(
            CosiumInvoice.customer_name,
            func.count(CosiumInvoice.id).label("nb_factures"),
            func.sum(CosiumInvoice.total_ti).label("total_facture"),
            func.sum(CosiumInvoice.outstanding_balance).label("total_impaye"),
            func.max(CosiumInvoice.invoice_date).label("derniere_facture"),
        )
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "INVOICE",
            CosiumInvoice.outstanding_balance > 0,
        )
        .group_by(CosiumInvoice.customer_name)
    )
    if date_from:
        q = q.where(CosiumInvoice.invoice_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.where(CosiumInvoice.invoice_date <= datetime.combine(date_to, datetime.max.time()))

    q = q.order_by(func.sum(CosiumInvoice.outstanding_balance).desc())
    rows = db.execute(q).all()

    result = []
    for r in rows:
        result.append({
            "client": r.customer_name or "Inconnu",
            "nb_factures": int(r.nb_factures),
            "total_facture": round(float(r.total_facture or 0), 2),
            "total_impaye": round(float(r.total_impaye or 0), 2),
            "derniere_facture": r.derniere_facture,
        })
    return result


def export_balance_clients_xlsx(
    db: Session,
    tenant_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> bytes:
    """Generate an Excel balance report of outstanding client debts."""
    rows = _get_balance_rows(db, tenant_id, date_from, date_to)

    wb = Workbook()
    ws = wb.active
    ws.title = "Balance Clients"

    # Header styling
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    headers = ["Client", "Nb Factures", "Total Facture (EUR)", "Total Impaye (EUR)", "Derniere Facture"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border

    total_facture = 0.0
    total_impaye = 0.0
    for row_idx, row in enumerate(rows, 2):
        ws.cell(row=row_idx, column=1, value=row["client"]).border = thin_border
        ws.cell(row=row_idx, column=2, value=row["nb_factures"]).border = thin_border
        c_fact = ws.cell(row=row_idx, column=3, value=row["total_facture"])
        c_fact.number_format = "#,##0.00"
        c_fact.border = thin_border
        c_imp = ws.cell(row=row_idx, column=4, value=row["total_impaye"])
        c_imp.number_format = "#,##0.00"
        c_imp.border = thin_border
        date_val = row["derniere_facture"].strftime("%d/%m/%Y") if row["derniere_facture"] else ""
        ws.cell(row=row_idx, column=5, value=date_val).border = thin_border
        total_facture += row["total_facture"]
        total_impaye += row["total_impaye"]

    # Total row
    total_row = len(rows) + 2
    ws.cell(row=total_row, column=1, value="TOTAL").font = Font(bold=True)
    ws.cell(row=total_row, column=2, value=len(rows)).font = Font(bold=True)
    c_tf = ws.cell(row=total_row, column=3, value=round(total_facture, 2))
    c_tf.number_format = "#,##0.00"
    c_tf.font = Font(bold=True)
    c_ti = ws.cell(row=total_row, column=4, value=round(total_impaye, 2))
    c_ti.number_format = "#,##0.00"
    c_ti.font = Font(bold=True)

    # Column widths
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 18

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    logger.info("balance_clients_xlsx_exported", tenant_id=tenant_id, rows=len(rows))
    return output.getvalue()


def export_balance_clients_pdf(
    db: Session,
    tenant_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> bytes:
    """Generate a PDF balance report of outstanding client debts."""
    rows = _get_balance_rows(db, tenant_id, date_from, date_to)

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, topMargin=20 * mm, bottomMargin=15 * mm)

    styles = getSampleStyleSheet()
    elements: list = []

    # Title
    title_style = ParagraphStyle(
        "BalanceTitle", parent=styles["Heading1"], fontSize=18, alignment=1, spaceAfter=6
    )
    elements.append(Paragraph("Balance Clients — OptiFlow", title_style))

    # Date of generation
    date_style = ParagraphStyle(
        "BalanceDate", parent=styles["Normal"], fontSize=10, alignment=1, spaceAfter=20, textColor=rl_colors.grey
    )
    generated = datetime.now(UTC).strftime("%d/%m/%Y %H:%M")
    period_text = ""
    if date_from or date_to:
        period_text = f" | Periode : {date_from.strftime('%d/%m/%Y') if date_from else '...'}"
        period_text += f" - {date_to.strftime('%d/%m/%Y') if date_to else '...'}"
    elements.append(Paragraph(f"Genere le {generated}{period_text}", date_style))

    # Table data
    table_data = [["Client", "Nb Factures", "Total Facture", "Total Impaye", "Derniere Facture"]]
    total_facture = 0.0
    total_impaye = 0.0
    for row in rows:
        date_str = row["derniere_facture"].strftime("%d/%m/%Y") if row["derniere_facture"] else ""
        table_data.append([
            row["client"],
            str(row["nb_factures"]),
            f"{row['total_facture']:,.2f} EUR",
            f"{row['total_impaye']:,.2f} EUR",
            date_str,
        ])
        total_facture += row["total_facture"]
        total_impaye += row["total_impaye"]

    table_data.append([
        "TOTAL", str(len(rows)),
        f"{total_facture:,.2f} EUR",
        f"{total_impaye:,.2f} EUR",
        "",
    ])

    col_widths = [140, 65, 90, 90, 85]
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("BACKGROUND", (0, -1), (-1, -1), rl_colors.HexColor("#F3F4F6")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [rl_colors.white, rl_colors.HexColor("#F9FAFB")]),
    ]))
    elements.append(table)

    doc.build(elements)
    output.seek(0)

    logger.info("balance_clients_pdf_exported", tenant_id=tenant_id, rows=len(rows))
    return output.getvalue()


# ---------------------------------------------------------------------------
# Dashboard PDF — export du tableau de bord
# ---------------------------------------------------------------------------

def export_dashboard_pdf(
    db: Session,
    tenant_id: int,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> bytes:
    """Generate a PDF snapshot of the dashboard KPIs."""
    from app.services import analytics_service

    dashboard = analytics_service.get_dashboard_full(db, tenant_id, date_from, date_to)

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, topMargin=20 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    elements: list = []

    # Title
    title_style = ParagraphStyle(
        "DashTitle", parent=styles["Heading1"], fontSize=18, alignment=1, spaceAfter=6
    )
    generated = datetime.now(UTC).strftime("%d/%m/%Y %H:%M")
    elements.append(Paragraph(f"Tableau de Bord OptiFlow — {generated}", title_style))
    elements.append(Spacer(1, 10))

    section_style = ParagraphStyle(
        "SectionTitle", parent=styles["Heading2"], fontSize=13, spaceAfter=8, spaceBefore=14,
        textColor=rl_colors.HexColor("#1E40AF"),
    )
    kpi_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F9FAFB")]),
    ])

    def _money(val: float) -> str:
        return f"{val:,.2f} EUR"

    # --- Financial KPIs ---
    fin = dashboard.financial
    elements.append(Paragraph("KPIs Financiers", section_style))
    fin_data = [
        ["Indicateur", "Valeur"],
        ["CA Total", _money(fin.ca_total)],
        ["Montant Facture", _money(fin.montant_facture)],
        ["Montant Encaisse", _money(fin.montant_encaisse)],
        ["Reste a Encaisser", _money(fin.reste_a_encaisser)],
        ["Taux Recouvrement", f"{fin.taux_recouvrement} %"],
    ]
    t = Table(fin_data, colWidths=[250, 200])
    t.setStyle(kpi_style)
    elements.append(t)

    # --- Cosium KPIs ---
    if dashboard.cosium:
        cos = dashboard.cosium
        elements.append(Paragraph("Donnees Cosium", section_style))
        cos_data = [
            ["Indicateur", "Valeur"],
            ["Total Facture Cosium", _money(cos.total_facture_cosium)],
            ["Total Impaye", _money(cos.total_outstanding)],
            ["Total Paye", _money(cos.total_paid)],
            ["Nb Factures", str(cos.invoice_count)],
            ["Nb Devis", str(cos.quote_count)],
            ["Nb Avoirs", str(cos.credit_note_count)],
        ]
        t = Table(cos_data, colWidths=[250, 200])
        t.setStyle(kpi_style)
        elements.append(t)

    # --- Operational KPIs ---
    ops = dashboard.operational
    elements.append(Paragraph("KPIs Operationnels", section_style))
    ops_data = [
        ["Indicateur", "Valeur"],
        ["Dossiers en cours", str(ops.dossiers_en_cours)],
        ["Dossiers complets", str(ops.dossiers_complets)],
        ["Taux Completude", f"{ops.taux_completude} %"],
        ["Pieces manquantes", str(ops.pieces_manquantes)],
    ]
    t = Table(ops_data, colWidths=[250, 200])
    t.setStyle(kpi_style)
    elements.append(t)

    # --- Commercial KPIs ---
    com = dashboard.commercial
    elements.append(Paragraph("KPIs Commerciaux", section_style))
    com_data = [
        ["Indicateur", "Valeur"],
        ["Devis en cours", str(com.devis_en_cours)],
        ["Devis signes", str(com.devis_signes)],
        ["Taux Conversion", f"{com.taux_conversion} %"],
        ["Panier Moyen", _money(com.panier_moyen)],
    ]
    t = Table(com_data, colWidths=[250, 200])
    t.setStyle(kpi_style)
    elements.append(t)

    # --- CA par mois ---
    if com.ca_par_mois:
        elements.append(Paragraph("CA par Mois", section_style))
        ca_data = [["Mois", "CA"]]
        for m in com.ca_par_mois:
            ca_data.append([m["mois"], _money(m["ca"])])
        t = Table(ca_data, colWidths=[250, 200])
        t.setStyle(kpi_style)
        elements.append(t)

    doc.build(elements)
    output.seek(0)

    logger.info("dashboard_pdf_exported", tenant_id=tenant_id)
    return output.getvalue()
