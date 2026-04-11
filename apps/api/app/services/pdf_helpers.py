"""Fonctions utilitaires pour la generation PDF (devis, factures, client 360)."""

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from app.models import Customer


def format_money(amount: float) -> str:
    return f"{amount:,.2f} EUR".replace(",", " ").replace(".", ",").replace(" ", " ")


def build_header(elements: list, styles: dict, doc_type: str, numero: str, date: str, tenant_info: dict) -> None:
    elements.append(Paragraph(tenant_info["name"], styles["title"]))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(f"{doc_type} N\u00b0 {numero}", styles["heading"]))
    elements.append(Paragraph(f"Date : {date}", styles["normal"]))
    elements.append(Spacer(1, 8 * mm))


def build_customer_block(elements: list, styles: dict, customer: Customer | None) -> None:
    if not customer:
        return
    name = f"{customer.first_name} {customer.last_name}"
    lines = [f"<b>Client :</b> {name}"]
    if customer.email:
        lines.append(f"Email : {customer.email}")
    if customer.phone:
        lines.append(f"Tel : {customer.phone}")
    if customer.address:
        addr = customer.address
        if customer.postal_code or customer.city:
            addr += f", {customer.postal_code or ''} {customer.city or ''}".strip()
        lines.append(f"Adresse : {addr}")
    for line in lines:
        elements.append(Paragraph(line, styles["normal"]))
    elements.append(Spacer(1, 8 * mm))


def build_lines_table(elements: list, lignes: list) -> None:
    header = ["Designation", "Qte", "PU HT", "TVA %", "Total HT", "Total TTC"]
    data = [header]
    for l in lignes:
        data.append(
            [
                l.designation,
                str(l.quantite),
                format_money(float(l.prix_unitaire_ht)),
                f"{float(l.taux_tva):.1f}%",
                format_money(float(l.montant_ht)),
                format_money(float(l.montant_ttc)),
            ]
        )

    table = Table(data, colWidths=[65 * mm, 15 * mm, 25 * mm, 18 * mm, 25 * mm, 25 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 6 * mm))


def build_totals(
    elements: list, styles: dict, montant_ht: float, tva: float, montant_ttc: float, extras: dict | None = None
) -> None:
    totals_data = [
        ["Total HT", format_money(montant_ht)],
        ["TVA", format_money(tva)],
        ["Total TTC", format_money(montant_ttc)],
    ]
    if extras:
        if extras.get("part_secu"):
            totals_data.append(["Part Securite sociale", f"- {format_money(extras['part_secu'])}"])
        if extras.get("part_mutuelle"):
            totals_data.append(["Part Mutuelle", f"- {format_money(extras['part_mutuelle'])}"])
        if extras.get("reste_a_charge") is not None:
            totals_data.append(["Reste a charge", format_money(extras["reste_a_charge"])])

    table = Table(totals_data, colWidths=[120 * mm, 50 * mm])
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#2563eb")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(table)
