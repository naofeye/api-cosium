"""Service de generation PDF pour devis et factures."""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models import Case, Customer, Devis, DevisLigne, Facture, FactureLigne, Tenant

logger = get_logger("pdf_service")


def _get_tenant_info(db: Session, tenant_id: int) -> dict:
    tenant = db.get(Tenant, tenant_id)
    return {"name": tenant.name if tenant else "OptiFlow", "slug": tenant.slug if tenant else ""}


def _get_customer_for_case(db: Session, case_id: int, tenant_id: int) -> Customer | None:
    case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
    if not case:
        return None
    return db.get(Customer, case.customer_id)


def _format_money(amount: float) -> str:
    return f"{amount:,.2f} EUR".replace(",", " ").replace(".", ",").replace(" ", " ")


def _build_header(elements: list, styles: dict, doc_type: str, numero: str, date: str, tenant_info: dict) -> None:
    elements.append(Paragraph(tenant_info["name"], styles["title"]))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(f"{doc_type} N° {numero}", styles["heading"]))
    elements.append(Paragraph(f"Date : {date}", styles["normal"]))
    elements.append(Spacer(1, 8 * mm))


def _build_customer_block(elements: list, styles: dict, customer: Customer | None) -> None:
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


def _build_lines_table(elements: list, lignes: list) -> None:
    header = ["Designation", "Qte", "PU HT", "TVA %", "Total HT", "Total TTC"]
    data = [header]
    for l in lignes:
        data.append(
            [
                l.designation,
                str(l.quantite),
                _format_money(float(l.prix_unitaire_ht)),
                f"{float(l.taux_tva):.1f}%",
                _format_money(float(l.montant_ht)),
                _format_money(float(l.montant_ttc)),
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


def _build_totals(
    elements: list, styles: dict, montant_ht: float, tva: float, montant_ttc: float, extras: dict | None = None
) -> None:
    totals_data = [
        ["Total HT", _format_money(montant_ht)],
        ["TVA", _format_money(tva)],
        ["Total TTC", _format_money(montant_ttc)],
    ]
    if extras:
        if extras.get("part_secu"):
            totals_data.append(["Part Securite sociale", f"- {_format_money(extras['part_secu'])}"])
        if extras.get("part_mutuelle"):
            totals_data.append(["Part Mutuelle", f"- {_format_money(extras['part_mutuelle'])}"])
        if extras.get("reste_a_charge") is not None:
            totals_data.append(["Reste a charge", _format_money(extras["reste_a_charge"])])

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


def generate_devis_pdf(db: Session, devis_id: int, tenant_id: int) -> bytes:
    """Genere un PDF pour un devis."""
    devis = db.query(Devis).filter(Devis.id == devis_id, Devis.tenant_id == tenant_id).first()
    if not devis:
        raise NotFoundError("devis", devis_id)

    lignes = db.query(DevisLigne).filter(DevisLigne.devis_id == devis_id, DevisLigne.tenant_id == tenant_id).all()
    customer = _get_customer_for_case(db, devis.case_id, tenant_id)
    tenant_info = _get_tenant_info(db, tenant_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("of_title", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#1e3a5f")))
    styles.add(
        ParagraphStyle("of_heading", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#2563eb"))
    )
    custom_styles = {"title": styles["of_title"], "heading": styles["of_heading"], "normal": styles["Normal"]}

    elements: list = []
    date_str = devis.created_at.strftime("%d/%m/%Y") if devis.created_at else datetime.now().strftime("%d/%m/%Y")
    _build_header(elements, custom_styles, "DEVIS", devis.numero, date_str, tenant_info)
    _build_customer_block(elements, custom_styles, customer)
    _build_lines_table(elements, lignes)
    _build_totals(
        elements,
        custom_styles,
        float(devis.montant_ht),
        float(devis.tva),
        float(devis.montant_ttc),
        {
            "part_secu": float(devis.part_secu),
            "part_mutuelle": float(devis.part_mutuelle),
            "reste_a_charge": float(devis.reste_a_charge),
        },
    )

    elements.append(Spacer(1, 15 * mm))
    elements.append(Paragraph(f"Statut : {devis.status}", custom_styles["normal"]))
    elements.append(Spacer(1, 5 * mm))
    elements.append(Paragraph("Ce document est un devis. Il n'a pas valeur de facture.", styles["Italic"]))

    doc.build(elements)
    logger.info("devis_pdf_generated", tenant_id=tenant_id, devis_id=devis_id, numero=devis.numero)
    return buffer.getvalue()


def generate_facture_pdf(db: Session, facture_id: int, tenant_id: int) -> bytes:
    """Genere un PDF pour une facture."""
    facture = db.query(Facture).filter(Facture.id == facture_id, Facture.tenant_id == tenant_id).first()
    if not facture:
        raise NotFoundError("facture", facture_id)

    lignes = (
        db.query(FactureLigne).filter(FactureLigne.facture_id == facture_id, FactureLigne.tenant_id == tenant_id).all()
    )
    customer = _get_customer_for_case(db, facture.case_id, tenant_id)
    tenant_info = _get_tenant_info(db, tenant_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=20 * mm, bottomMargin=20 * mm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("of_title", parent=styles["Title"], fontSize=16, textColor=colors.HexColor("#1e3a5f")))
    styles.add(
        ParagraphStyle("of_heading", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#2563eb"))
    )
    custom_styles = {"title": styles["of_title"], "heading": styles["of_heading"], "normal": styles["Normal"]}

    elements: list = []
    date_str = (
        facture.date_emission.strftime("%d/%m/%Y") if facture.date_emission else datetime.now().strftime("%d/%m/%Y")
    )
    _build_header(elements, custom_styles, "FACTURE", facture.numero, date_str, tenant_info)
    _build_customer_block(elements, custom_styles, customer)
    _build_lines_table(elements, lignes)
    _build_totals(elements, custom_styles, float(facture.montant_ht), float(facture.tva), float(facture.montant_ttc))

    elements.append(Spacer(1, 15 * mm))
    elements.append(Paragraph(f"Statut : {facture.status}", custom_styles["normal"]))

    doc.build(elements)
    logger.info("facture_pdf_generated", tenant_id=tenant_id, facture_id=facture_id, numero=facture.numero)
    return buffer.getvalue()
