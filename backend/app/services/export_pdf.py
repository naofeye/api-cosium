"""Service d'export PDF : dashboard et balance clients."""

import io
from datetime import UTC, date, datetime

from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.cosium_data import CosiumInvoice

logger = get_logger("export_pdf")


# ---------------------------------------------------------------------------
# Balance Clients — shared data helper
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


# ---------------------------------------------------------------------------
# Balance Clients PDF
# ---------------------------------------------------------------------------

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
# Dashboard PDF
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
            mois = m.mois if hasattr(m, "mois") else m["mois"]
            ca = m.ca if hasattr(m, "ca") else m["ca"]
            ca_data.append([mois, _money(ca)])
        t = Table(ca_data, colWidths=[250, 200])
        t.setStyle(kpi_style)
        elements.append(t)

    doc.build(elements)
    output.seek(0)

    logger.info("dashboard_pdf_exported", tenant_id=tenant_id)
    return output.getvalue()
