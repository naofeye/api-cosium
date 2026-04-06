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
# Styles helper
# ---------------------------------------------------------------------------

def _section_table_style() -> TableStyle:
    """Reusable table style for data sections."""
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F9FAFB")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])


def _fmt_money(val: float) -> str:
    return f"{val:,.2f} EUR".replace(",", " ").replace(".", ",").replace(" ", " ")


def _fmt_diopter(val: float | None) -> str:
    if val is None:
        return "-"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}"


# ---------------------------------------------------------------------------
# Fiche Client Complete PDF
# ---------------------------------------------------------------------------

def export_client_pdf(db: Session, client_id: int, tenant_id: int) -> bytes:
    """Generate a comprehensive PDF for a single client with all their data."""
    from app.services.client_360_service import get_client_360

    data = get_client_360(db, tenant_id=tenant_id, client_id=client_id)

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=15 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    elements: list = []

    title_style = ParagraphStyle(
        "ClientTitle", parent=styles["Heading1"], fontSize=18, alignment=1, spaceAfter=6,
    )
    date_style = ParagraphStyle(
        "ClientDate", parent=styles["Normal"], fontSize=10, alignment=1,
        spaceAfter=20, textColor=rl_colors.grey,
    )
    section_style = ParagraphStyle(
        "SectionTitle", parent=styles["Heading2"], fontSize=13, spaceAfter=8,
        spaceBefore=14, textColor=rl_colors.HexColor("#1E40AF"),
    )
    normal = styles["Normal"]

    # ── 1. Header ──
    elements.append(Paragraph("Fiche Client — OptiFlow", title_style))
    generated = datetime.now(UTC).strftime("%d/%m/%Y %H:%M")
    elements.append(Paragraph(f"Generee le {generated}", date_style))

    # ── 2. Informations personnelles ──
    elements.append(Paragraph("Informations personnelles", section_style))
    info_rows = [
        ["Nom", f"{data.first_name} {data.last_name}"],
    ]
    if data.birth_date:
        info_rows.append(["Date de naissance", data.birth_date])
    if data.email:
        info_rows.append(["Email", data.email])
    if data.phone:
        info_rows.append(["Telephone", data.phone])
    if data.address:
        addr = data.address
        if data.postal_code or data.city:
            addr += f", {data.postal_code or ''} {data.city or ''}".strip()
        info_rows.append(["Adresse", addr])
    if data.social_security_number:
        info_rows.append(["N. Securite Sociale", data.social_security_number])
    if data.cosium_id:
        info_rows.append(["Cosium ID", data.cosium_id])

    info_table = Table(info_rows, colWidths=[120, 360])
    info_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor("#E5E7EB")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 8 * mm))

    # ── 3. Correction actuelle ──
    correction = data.cosium_data.correction_actuelle if data.cosium_data else None
    if correction:
        elements.append(Paragraph("Correction actuelle", section_style))
        if correction.prescription_date:
            elements.append(Paragraph(
                f"Ordonnance du {correction.prescription_date}"
                + (f" — {correction.prescriber_name}" if correction.prescriber_name else ""),
                normal,
            ))
            elements.append(Spacer(1, 2 * mm))

        corr_data = [
            ["", "Sphere", "Cylindre", "Axe", "Addition"],
            [
                "OD",
                _fmt_diopter(correction.sphere_right),
                _fmt_diopter(correction.cylinder_right),
                str(correction.axis_right) if correction.axis_right is not None else "-",
                _fmt_diopter(correction.addition_right),
            ],
            [
                "OG",
                _fmt_diopter(correction.sphere_left),
                _fmt_diopter(correction.cylinder_left),
                str(correction.axis_left) if correction.axis_left is not None else "-",
                _fmt_diopter(correction.addition_left),
            ],
        ]
        corr_table = Table(corr_data, colWidths=[40, 80, 80, 60, 80])
        corr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F9FAFB")]),
        ]))
        elements.append(corr_table)
        elements.append(Spacer(1, 8 * mm))

    # ── 4. Resume financier ──
    elements.append(Paragraph("Resume financier", section_style))
    fin = data.resume_financier
    cosium_ca = data.cosium_data.total_ca_cosium if data.cosium_data else 0
    fin_rows = [
        ["CA Cosium", _fmt_money(cosium_ca)],
        ["Total facture (OptiFlow)", _fmt_money(fin.total_facture)],
        ["Montant paye", _fmt_money(fin.total_paye)],
        ["Reste du", _fmt_money(fin.reste_du)],
        ["Taux de recouvrement", f"{fin.taux_recouvrement:.1f} %"],
    ]
    fin_table = Table(fin_rows, colWidths=[200, 200])
    fin_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor("#E5E7EB")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(fin_table)
    elements.append(Spacer(1, 8 * mm))

    # ── 5. Factures Cosium (20 dernieres) ──
    cosium_invoices = data.cosium_invoices[:20] if data.cosium_invoices else []
    if cosium_invoices:
        elements.append(Paragraph(f"Factures Cosium ({len(data.cosium_invoices)} total)", section_style))
        inv_data = [["Date", "Numero", "Type", "Montant TTC", "Impaye", "Solde"]]
        for inv in cosium_invoices:
            inv_data.append([
                inv.invoice_date or "-",
                inv.invoice_number,
                inv.type,
                _fmt_money(inv.total_ti),
                _fmt_money(inv.outstanding_balance),
                "Oui" if inv.settled else "Non",
            ])
        inv_table = Table(inv_data, colWidths=[65, 80, 60, 75, 75, 40])
        inv_table.setStyle(_section_table_style())
        elements.append(inv_table)
        elements.append(Spacer(1, 8 * mm))

    # ── 6. Paiements Cosium (20 derniers) ──
    cosium_payments = (data.cosium_data.cosium_payments[:20]
                       if data.cosium_data and data.cosium_data.cosium_payments else [])
    if cosium_payments:
        elements.append(Paragraph(f"Paiements ({len(data.cosium_data.cosium_payments)} total)", section_style))
        pay_data = [["Date", "Montant", "Type", "Banque", "Emetteur"]]
        for p in cosium_payments:
            pay_data.append([
                p.due_date or "-",
                _fmt_money(p.amount),
                p.type,
                p.bank or "-",
                p.issuer_name or "-",
            ])
        pay_table = Table(pay_data, colWidths=[65, 75, 80, 80, 95])
        pay_table.setStyle(_section_table_style())
        elements.append(pay_table)
        elements.append(Spacer(1, 8 * mm))

    # ── 7. Rendez-vous (10 derniers) ──
    calendar = (data.cosium_data.calendar_events[:10]
                if data.cosium_data and data.cosium_data.calendar_events else [])
    if calendar:
        elements.append(Paragraph(f"Rendez-vous ({len(data.cosium_data.calendar_events)} total)", section_style))
        cal_data = [["Date debut", "Categorie", "Statut", "Annule", "Manque"]]
        for ev in calendar:
            status_txt = ev.status or "-"
            cal_data.append([
                ev.start_date or "-",
                ev.category_name or "-",
                status_txt,
                "Oui" if ev.canceled else "Non",
                "Oui" if ev.missed else "Non",
            ])
        cal_table = Table(cal_data, colWidths=[100, 100, 80, 50, 50])
        cal_table.setStyle(_section_table_style())
        elements.append(cal_table)
        elements.append(Spacer(1, 8 * mm))

    # ── 8. Equipements ──
    equipments = (data.cosium_data.equipments[:20]
                  if data.cosium_data and data.cosium_data.equipments else [])
    if equipments:
        elements.append(Paragraph(f"Equipements ({len(data.cosium_data.equipments)} total)", section_style))
        eq_data = [["Date", "Designation", "Marque", "Type"]]
        for eq in equipments:
            eq_data.append([
                eq.prescription_date or "-",
                eq.label or "-",
                eq.brand or "-",
                eq.type or "-",
            ])
        eq_table = Table(eq_data, colWidths=[75, 150, 100, 80])
        eq_table.setStyle(_section_table_style())
        elements.append(eq_table)
        elements.append(Spacer(1, 8 * mm))

    # Footer
    elements.append(Spacer(1, 10 * mm))
    footer_style = ParagraphStyle(
        "FooterStyle", parent=styles["Italic"], fontSize=8,
        textColor=rl_colors.grey, alignment=1,
    )
    elements.append(Paragraph(
        "Document genere automatiquement par OptiFlow AI. Confidentiel.",
        footer_style,
    ))

    doc.build(elements)
    output.seek(0)

    logger.info("client_pdf_exported", tenant_id=tenant_id, client_id=client_id)
    return output.getvalue()


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


# ---------------------------------------------------------------------------
# PEC Preparation PDF
# ---------------------------------------------------------------------------

def _severity_color(severity: str) -> rl_colors.Color:
    """Return a ReportLab color for an alert severity."""
    if severity == "error":
        return rl_colors.HexColor("#DC2626")
    if severity == "warning":
        return rl_colors.HexColor("#D97706")
    return rl_colors.HexColor("#2563EB")


def _field_row(label: str, field: dict | None) -> list[str]:
    """Build a table row from a consolidated field dict."""
    if not field:
        return [label, "-", "-", "-"]
    value = str(field.get("value", "-") or "-")
    source = field.get("source_label", field.get("source", "-"))
    confidence = field.get("confidence")
    conf_str = f"{confidence * 100:.0f} %" if confidence is not None else "-"
    return [label, value, str(source), conf_str]


def export_pec_preparation_pdf(
    db: Session,
    tenant_id: int,
    preparation_id: int,
) -> bytes:
    """Generate a professional PDF of a PEC preparation worksheet."""
    from app.services import pec_preparation_service

    prep = pec_preparation_service.get_preparation(db, tenant_id, preparation_id)

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    elements: list = []

    title_style = ParagraphStyle(
        "PecTitle", parent=styles["Heading1"], fontSize=16, alignment=1, spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "PecSubtitle", parent=styles["Normal"], fontSize=10, alignment=1,
        spaceAfter=6, textColor=rl_colors.grey,
    )
    section_style = ParagraphStyle(
        "PecSection", parent=styles["Heading2"], fontSize=12, spaceAfter=6,
        spaceBefore=12, textColor=rl_colors.HexColor("#1E40AF"),
    )
    normal = styles["Normal"]
    small = ParagraphStyle("SmallPec", parent=normal, fontSize=8, textColor=rl_colors.grey)

    profile = prep.consolidated_data or {}

    # ── Header ──
    elements.append(Paragraph("Fiche d'assistance PEC — OptiFlow", title_style))
    generated = datetime.now(UTC).strftime("%d/%m/%Y %H:%M")
    score = prep.completude_score
    elements.append(Paragraph(
        f"Generee le {generated} | Score de completude : {score:.0f} % | "
        f"Statut : {prep.status}",
        subtitle_style,
    ))
    elements.append(Spacer(1, 6 * mm))

    # ── 1. Identite du patient ──
    elements.append(Paragraph("1. Identite du patient", section_style))
    identity_rows = [["Champ", "Valeur", "Source", "Confiance"]]
    for label, key in [
        ("Nom", "nom"),
        ("Prenom", "prenom"),
        ("Date de naissance", "date_naissance"),
        ("N. Securite sociale", "numero_secu"),
    ]:
        identity_rows.append(_field_row(label, profile.get(key)))
    id_table = Table(identity_rows, colWidths=[120, 160, 100, 60])
    id_table.setStyle(_section_table_style())
    elements.append(id_table)
    elements.append(Spacer(1, 4 * mm))

    # ── 2. Mutuelle / OCAM ──
    elements.append(Paragraph("2. Mutuelle / OCAM", section_style))
    mut_rows = [["Champ", "Valeur", "Source", "Confiance"]]
    for label, key in [
        ("Mutuelle", "mutuelle_nom"),
        ("N. Adherent", "mutuelle_numero_adherent"),
        ("Code organisme", "mutuelle_code_organisme"),
        ("Beneficiaire", "type_beneficiaire"),
        ("Fin de droits", "date_fin_droits"),
    ]:
        mut_rows.append(_field_row(label, profile.get(key)))
    mut_table = Table(mut_rows, colWidths=[120, 160, 100, 60])
    mut_table.setStyle(_section_table_style())
    elements.append(mut_table)
    elements.append(Spacer(1, 4 * mm))

    # ── 3. Correction optique ──
    elements.append(Paragraph("3. Correction optique", section_style))
    corr_header = ["", "Sphere", "Cylindre", "Axe", "Addition"]
    od_row = [
        "OD",
        str((profile.get("sphere_od") or {}).get("value", "-")),
        str((profile.get("cylinder_od") or {}).get("value", "-")),
        str((profile.get("axis_od") or {}).get("value", "-")),
        str((profile.get("addition_od") or {}).get("value", "-")),
    ]
    og_row = [
        "OG",
        str((profile.get("sphere_og") or {}).get("value", "-")),
        str((profile.get("cylinder_og") or {}).get("value", "-")),
        str((profile.get("axis_og") or {}).get("value", "-")),
        str((profile.get("addition_og") or {}).get("value", "-")),
    ]
    corr_table = Table([corr_header, od_row, og_row], colWidths=[40, 80, 80, 60, 80])
    corr_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F9FAFB")]),
    ]))
    elements.append(corr_table)

    prescripteur = profile.get("prescripteur")
    date_ordo = profile.get("date_ordonnance")
    ep = profile.get("ecart_pupillaire")
    extra_rows = []
    if prescripteur:
        extra_rows.append(_field_row("Prescripteur", prescripteur))
    if date_ordo:
        extra_rows.append(_field_row("Date ordonnance", date_ordo))
    if ep:
        extra_rows.append(_field_row("Ecart pupillaire", ep))
    if extra_rows:
        extra_rows.insert(0, ["Champ", "Valeur", "Source", "Confiance"])
        et = Table(extra_rows, colWidths=[120, 160, 100, 60])
        et.setStyle(_section_table_style())
        elements.append(Spacer(1, 2 * mm))
        elements.append(et)
    elements.append(Spacer(1, 4 * mm))

    # ── 4. Equipement (devis) ──
    elements.append(Paragraph("4. Equipement (lignes devis)", section_style))
    equip_rows = [["Element", "Valeur", "Source", "Confiance"]]
    monture = profile.get("monture")
    if monture:
        equip_rows.append(_field_row("Monture", monture))
    verres = profile.get("verres", [])
    for i, v in enumerate(verres):
        equip_rows.append(_field_row(f"Verre {i + 1}", v))
    if len(equip_rows) == 1:
        equip_rows.append(["", "Aucun equipement renseigne", "", ""])
    eq_table = Table(equip_rows, colWidths=[120, 160, 100, 60])
    eq_table.setStyle(_section_table_style())
    elements.append(eq_table)
    elements.append(Spacer(1, 4 * mm))

    # ── 5. Synthese financiere ──
    elements.append(Paragraph("5. Synthese financiere", section_style))
    fin_rows = [["Poste", "Montant", "Source", "Confiance"]]
    for label, key in [
        ("Total TTC", "montant_ttc"),
        ("Part Securite sociale", "part_secu"),
        ("Part Mutuelle", "part_mutuelle"),
        ("Reste a charge", "reste_a_charge"),
    ]:
        field = profile.get(key)
        if field and field.get("value") is not None:
            val = _fmt_money(float(field["value"]))
        else:
            val = "-"
        source = (field.get("source_label", "-") if field else "-")
        conf = f"{field['confidence'] * 100:.0f} %" if field and field.get("confidence") is not None else "-"
        fin_rows.append([label, val, str(source), conf])
    fin_table = Table(fin_rows, colWidths=[120, 120, 100, 60])
    fin_table.setStyle(_section_table_style())
    elements.append(fin_table)
    elements.append(Spacer(1, 4 * mm))

    # ── 6. Pieces justificatives ──
    elements.append(Paragraph("6. Pieces justificatives", section_style))
    from app.services import pec_preparation_service as pps
    try:
        docs = pps.list_documents(db, tenant_id, preparation_id)
        if docs:
            doc_rows = [["Role", "Document ID", "Cosium Doc ID"]]
            for d in docs:
                doc_rows.append([
                    d.document_role,
                    str(d.document_id or "-"),
                    str(d.cosium_document_id or "-"),
                ])
            doc_table = Table(doc_rows, colWidths=[120, 120, 120])
            doc_table.setStyle(_section_table_style())
            elements.append(doc_table)
        else:
            elements.append(Paragraph("Aucune piece justificative attachee.", small))
    except Exception:
        elements.append(Paragraph("Impossible de charger les pieces justificatives.", small))
    elements.append(Spacer(1, 4 * mm))

    # ── 7. Alertes et incoherences ──
    elements.append(Paragraph("7. Alertes et incoherences", section_style))
    alertes = profile.get("alertes", [])
    if alertes:
        alert_rows = [["Severite", "Champ", "Message"]]
        for a in alertes:
            sev = a.get("severity", "info")
            alert_rows.append([sev.upper(), a.get("field", "-"), a.get("message", "-")])
        alert_table = Table(alert_rows, colWidths=[60, 100, 280])
        alert_ts = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#374151")),
            ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
        alert_table.setStyle(alert_ts)
        # Color code severity cells
        for i, a in enumerate(alertes, start=1):
            sev = a.get("severity", "info")
            color = _severity_color(sev)
            alert_table.setStyle(TableStyle([
                ("TEXTCOLOR", (0, i), (0, i), color),
                ("FONTNAME", (0, i), (0, i), "Helvetica-Bold"),
            ]))
        elements.append(alert_table)
    else:
        elements.append(Paragraph("Aucune alerte detectee.", small))
    elements.append(Spacer(1, 4 * mm))

    # Summary
    elements.append(Spacer(1, 4 * mm))
    summary_text = (
        f"Erreurs : {prep.errors_count} | "
        f"Avertissements : {prep.warnings_count} | "
        f"Champs manquants : {', '.join(profile.get('champs_manquants', [])) or 'aucun'}"
    )
    elements.append(Paragraph(summary_text, ParagraphStyle(
        "Summary", parent=normal, fontSize=9, spaceAfter=8,
    )))

    # Footer
    elements.append(Spacer(1, 8 * mm))
    footer_style = ParagraphStyle(
        "PecFooter", parent=styles["Italic"], fontSize=8,
        textColor=rl_colors.grey, alignment=1,
    )
    elements.append(Paragraph(
        "Document genere automatiquement — a verifier avant soumission.",
        footer_style,
    ))

    doc.build(elements)
    output.seek(0)

    logger.info(
        "pec_preparation_pdf_exported",
        tenant_id=tenant_id,
        preparation_id=preparation_id,
    )
    return output.getvalue()
