"""Client-related PDF exports: client profile, client 360."""

import io
from datetime import UTC, datetime

from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.services.export_pdf_base import (
    create_pdf_doc,
    fmt_diopter,
    fmt_money,
    generated_timestamp,
    logger,
    make_date_style,
    make_footer_style,
    make_section_style,
    make_title_style,
    section_table_style,
)


def export_client_pdf(db: Session, client_id: int, tenant_id: int) -> bytes:
    """Generate a comprehensive PDF for a single client with all their data."""
    from app.services.client_360_service import get_client_360

    data = get_client_360(db, tenant_id=tenant_id, client_id=client_id)

    output = io.BytesIO()
    doc = create_pdf_doc(output)

    styles = getSampleStyleSheet()
    elements: list = []

    title_style = make_title_style("ClientTitle")
    date_style = make_date_style("ClientDate")
    sec_style = make_section_style("SectionTitle")
    normal = styles["Normal"]

    # -- 1. Header --
    elements.append(Paragraph("Fiche Client — OptiFlow", title_style))
    elements.append(Paragraph(f"Generee le {generated_timestamp()}", date_style))

    # -- 2. Informations personnelles --
    elements.append(Paragraph("Informations personnelles", sec_style))
    info_rows = [["Nom", f"{data.first_name} {data.last_name}"]]
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

    # -- 3. Correction actuelle --
    correction = data.cosium_data.correction_actuelle if data.cosium_data else None
    if correction:
        _append_correction_section(elements, correction, sec_style, normal)

    # -- 4. Resume financier --
    _append_financial_summary(elements, data, sec_style)

    # -- 5. Factures Cosium (20 dernieres) --
    cosium_invoices = data.cosium_invoices[:20] if data.cosium_invoices else []
    if cosium_invoices:
        _append_cosium_invoices(elements, data, cosium_invoices, sec_style)

    # -- 6. Paiements Cosium (20 derniers) --
    cosium_payments = (
        data.cosium_data.cosium_payments[:20]
        if data.cosium_data and data.cosium_data.cosium_payments else []
    )
    if cosium_payments:
        _append_cosium_payments(elements, data, cosium_payments, sec_style)

    # -- 7. Rendez-vous (10 derniers) --
    calendar = (
        data.cosium_data.calendar_events[:10]
        if data.cosium_data and data.cosium_data.calendar_events else []
    )
    if calendar:
        _append_calendar_events(elements, data, calendar, sec_style)

    # -- 8. Equipements --
    equipments = (
        data.cosium_data.equipments[:20]
        if data.cosium_data and data.cosium_data.equipments else []
    )
    if equipments:
        _append_equipments(elements, data, equipments, sec_style)

    # Footer
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph(
        "Document genere automatiquement par OptiFlow AI. Confidentiel.",
        make_footer_style("FooterStyle"),
    ))

    doc.build(elements)
    output.seek(0)

    logger.info("client_pdf_exported", tenant_id=tenant_id, client_id=client_id)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Internal section builders
# ---------------------------------------------------------------------------

def _append_correction_section(
    elements: list, correction, sec_style, normal,
) -> None:
    elements.append(Paragraph("Correction actuelle", sec_style))
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
            fmt_diopter(correction.sphere_right),
            fmt_diopter(correction.cylinder_right),
            str(correction.axis_right) if correction.axis_right is not None else "-",
            fmt_diopter(correction.addition_right),
        ],
        [
            "OG",
            fmt_diopter(correction.sphere_left),
            fmt_diopter(correction.cylinder_left),
            str(correction.axis_left) if correction.axis_left is not None else "-",
            fmt_diopter(correction.addition_left),
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
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            rl_colors.white, rl_colors.HexColor("#F9FAFB"),
        ]),
    ]))
    elements.append(corr_table)
    elements.append(Spacer(1, 8 * mm))


def _append_financial_summary(elements: list, data, sec_style) -> None:
    elements.append(Paragraph("Resume financier", sec_style))
    fin = data.resume_financier
    cosium_ca = data.cosium_data.total_ca_cosium if data.cosium_data else 0
    fin_rows = [
        ["CA Cosium", fmt_money(cosium_ca)],
        ["Total facture (OptiFlow)", fmt_money(fin.total_facture)],
        ["Montant paye", fmt_money(fin.total_paye)],
        ["Reste du", fmt_money(fin.reste_du)],
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


def _append_cosium_invoices(elements, data, cosium_invoices, sec_style) -> None:
    elements.append(Paragraph(
        f"Factures Cosium ({len(data.cosium_invoices)} total)", sec_style,
    ))
    inv_data = [["Date", "Numero", "Type", "Montant TTC", "Impaye", "Solde"]]
    for inv in cosium_invoices:
        inv_data.append([
            inv.invoice_date or "-",
            inv.invoice_number,
            inv.type,
            fmt_money(inv.total_ti),
            fmt_money(inv.outstanding_balance),
            "Oui" if inv.settled else "Non",
        ])
    inv_table = Table(inv_data, colWidths=[65, 80, 60, 75, 75, 40])
    inv_table.setStyle(section_table_style())
    elements.append(inv_table)
    elements.append(Spacer(1, 8 * mm))


def _append_cosium_payments(elements, data, cosium_payments, sec_style) -> None:
    elements.append(Paragraph(
        f"Paiements ({len(data.cosium_data.cosium_payments)} total)", sec_style,
    ))
    pay_data = [["Date", "Montant", "Type", "Banque", "Emetteur"]]
    for p in cosium_payments:
        pay_data.append([
            p.due_date or "-",
            fmt_money(p.amount),
            p.type,
            p.bank or "-",
            p.issuer_name or "-",
        ])
    pay_table = Table(pay_data, colWidths=[65, 75, 80, 80, 95])
    pay_table.setStyle(section_table_style())
    elements.append(pay_table)
    elements.append(Spacer(1, 8 * mm))


def _append_calendar_events(elements, data, calendar, sec_style) -> None:
    elements.append(Paragraph(
        f"Rendez-vous ({len(data.cosium_data.calendar_events)} total)", sec_style,
    ))
    cal_data = [["Date debut", "Categorie", "Statut", "Annule", "Manque"]]
    for ev in calendar:
        cal_data.append([
            ev.start_date or "-",
            ev.category_name or "-",
            ev.status or "-",
            "Oui" if ev.canceled else "Non",
            "Oui" if ev.missed else "Non",
        ])
    cal_table = Table(cal_data, colWidths=[100, 100, 80, 50, 50])
    cal_table.setStyle(section_table_style())
    elements.append(cal_table)
    elements.append(Spacer(1, 8 * mm))


def _append_equipments(elements, data, equipments, sec_style) -> None:
    elements.append(Paragraph(
        f"Equipements ({len(data.cosium_data.equipments)} total)", sec_style,
    ))
    eq_data = [["Date", "Designation", "Marque", "Type"]]
    for eq in equipments:
        eq_data.append([
            eq.prescription_date or "-",
            eq.label or "-",
            eq.brand or "-",
            eq.type or "-",
        ])
    eq_table = Table(eq_data, colWidths=[75, 150, 100, 80])
    eq_table.setStyle(section_table_style())
    elements.append(eq_table)
    elements.append(Spacer(1, 8 * mm))
