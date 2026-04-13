"""Dashboard and KPI PDF exports."""

import io
from datetime import datetime

from reportlab.platypus import Paragraph, Spacer, Table
from sqlalchemy.orm import Session

from app.core.logging import log_operation
from app.services.export_pdf_base import (
    create_pdf_doc,
    generated_timestamp,
    kpi_table_style,
    logger,
    make_section_style,
    make_title_style,
)


def _money(val: float) -> str:
    return f"{val:,.2f} EUR"


@log_operation("export_dashboard_pdf")
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
    doc = create_pdf_doc(output)
    elements: list = []

    title_style = make_title_style("DashTitle")
    sec_style = make_section_style("SectionTitle")
    kpi_style = kpi_table_style()

    # Title
    elements.append(Paragraph(
        f"Tableau de Bord OptiFlow — {generated_timestamp()}", title_style,
    ))
    elements.append(Spacer(1, 10))

    # --- Financial KPIs ---
    fin = dashboard.financial
    elements.append(Paragraph("KPIs Financiers", sec_style))
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
        elements.append(Paragraph("Donnees Cosium", sec_style))
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
    elements.append(Paragraph("KPIs Operationnels", sec_style))
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
    elements.append(Paragraph("KPIs Commerciaux", sec_style))
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
        elements.append(Paragraph("CA par Mois", sec_style))
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
