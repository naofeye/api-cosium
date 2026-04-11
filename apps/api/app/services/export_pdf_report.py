"""Monthly/periodic report PDF exports."""

import calendar as cal_module
import io
from datetime import UTC, datetime

from reportlab.lib import colors as rl_colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import log_operation
from app.models import Case, Customer, Devis, Facture, Payment, PecRequest
from app.models.cosium_data import CosiumInvoice
from app.services.export_pdf_base import (
    append_footer,
    create_pdf_doc,
    fmt_money,
    generated_timestamp,
    kpi_table_style,
    logger,
    make_date_style,
    make_section_style,
    make_title_style,
    section_table_style,
)

MONTH_NAMES_FR = {
    1: "Janvier", 2: "Fevrier", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Aout",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Decembre",
}


# ---------------------------------------------------------------------------
# Monthly Report PDF
# ---------------------------------------------------------------------------

@log_operation("export_monthly_report_pdf")
def export_monthly_report_pdf(
    db: Session,
    tenant_id: int,
    year: int,
    month: int,
) -> bytes:
    """Generate a comprehensive monthly business report PDF."""
    month_name = MONTH_NAMES_FR.get(month, str(month))
    last_day = cal_module.monthrange(year, month)[1]
    month_start = datetime(year, month, 1)
    month_end = datetime(year, month, last_day, 23, 59, 59)

    output = io.BytesIO()
    doc = create_pdf_doc(output)
    styles = getSampleStyleSheet()
    elements: list = []

    title_style = make_title_style("MonthlyTitle")
    date_style = make_date_style("MonthlyDate")
    sec_style = make_section_style("MonthlySection")
    kpi_ts = kpi_table_style()

    # -- Header --
    elements.append(Paragraph(
        f"Rapport mensuel — {month_name} {year} — OptiFlow", title_style,
    ))
    elements.append(Paragraph(f"Genere le {generated_timestamp()}", date_style))

    # -- 1. KPIs du mois --
    _append_monthly_kpis(elements, db, tenant_id, month_start, month_end, sec_style, kpi_ts)

    # -- 2. Activite du mois --
    _append_monthly_activity(elements, db, tenant_id, month_start, month_end, sec_style, kpi_ts)

    # -- 3. Top 10 clients par CA --
    _append_top_clients(elements, db, tenant_id, month_start, month_end, sec_style)

    # -- 4. Balance agee --
    _append_aging_balance(elements, db, tenant_id, sec_style)

    # -- 5. Statistiques opticiens --
    _append_opticien_stats(elements, db, tenant_id, month_start, month_end, sec_style, styles)

    # Footer
    append_footer(elements, "MonthlyFooter")

    doc.build(elements)
    output.seek(0)

    logger.info(
        "monthly_report_pdf_exported",
        tenant_id=tenant_id, year=year, month=month,
    )
    return output.getvalue()


def _append_monthly_kpis(elements: list, db: object, tenant_id: int, month_start: object, month_end: object, sec_style: object, kpi_ts: object) -> None:
    elements.append(Paragraph("1. KPIs du mois", sec_style))

    ca_total = float(db.scalar(
        select(func.coalesce(func.sum(Facture.montant_ttc), 0))
        .where(Facture.tenant_id == tenant_id,
               Facture.created_at >= month_start, Facture.created_at <= month_end)
    ) or 0)

    encaisse = float(db.scalar(
        select(func.coalesce(func.sum(Payment.amount_paid), 0))
        .where(Payment.tenant_id == tenant_id,
               Payment.created_at >= month_start, Payment.created_at <= month_end)
    ) or 0)

    impayes = round(ca_total - encaisse, 2) if ca_total > encaisse else 0
    taux_recouv = round(encaisse / ca_total * 100, 1) if ca_total > 0 else 0

    kpi_data = [
        ["Indicateur", "Valeur"],
        ["CA Total", fmt_money(ca_total)],
        ["Encaisse", fmt_money(encaisse)],
        ["Impayes", fmt_money(impayes)],
        ["Taux de recouvrement", f"{taux_recouv} %"],
    ]
    t = Table(kpi_data, colWidths=[250, 200])
    t.setStyle(kpi_ts)
    elements.append(t)
    elements.append(Spacer(1, 6 * mm))


def _append_monthly_activity(elements: list, db: object, tenant_id: int, month_start: object, month_end: object, sec_style: object, kpi_ts: object) -> None:
    elements.append(Paragraph("2. Activite du mois", sec_style))

    dossiers_crees = db.scalar(
        select(func.count()).select_from(Case)
        .where(Case.tenant_id == tenant_id,
               Case.created_at >= month_start, Case.created_at <= month_end)
    ) or 0

    devis_signes = db.scalar(
        select(func.count()).select_from(Devis)
        .where(Devis.tenant_id == tenant_id,
               Devis.status.in_(["signe", "facture"]),
               Devis.created_at >= month_start, Devis.created_at <= month_end)
    ) or 0

    factures_emises = db.scalar(
        select(func.count()).select_from(Facture)
        .where(Facture.tenant_id == tenant_id,
               Facture.created_at >= month_start, Facture.created_at <= month_end)
    ) or 0

    pec_soumises = db.scalar(
        select(func.count()).select_from(PecRequest)
        .where(PecRequest.tenant_id == tenant_id,
               PecRequest.created_at >= month_start, PecRequest.created_at <= month_end)
    ) or 0

    activity_data = [
        ["Indicateur", "Nombre"],
        ["Dossiers crees", str(dossiers_crees)],
        ["Devis signes", str(devis_signes)],
        ["Factures emises", str(factures_emises)],
        ["PEC soumises", str(pec_soumises)],
    ]
    t = Table(activity_data, colWidths=[250, 200])
    t.setStyle(kpi_ts)
    elements.append(t)
    elements.append(Spacer(1, 6 * mm))


def _append_top_clients(elements: list, db: object, tenant_id: int, month_start: object, month_end: object, sec_style: object) -> None:
    elements.append(Paragraph("3. Top 10 clients par CA", sec_style))

    top_clients_q = (
        select(
            Customer.first_name,
            Customer.last_name,
            func.coalesce(func.sum(Facture.montant_ttc), 0).label("ca"),
        )
        .join(Case, Case.customer_id == Customer.id)
        .join(Facture, Facture.case_id == Case.id)
        .where(
            Customer.tenant_id == tenant_id,
            Facture.tenant_id == tenant_id,
            Facture.created_at >= month_start,
            Facture.created_at <= month_end,
        )
        .group_by(Customer.id, Customer.first_name, Customer.last_name)
        .order_by(func.sum(Facture.montant_ttc).desc())
        .limit(10)
    )
    top_rows = db.execute(top_clients_q).all()

    top_data = [["#", "Client", "CA"]]
    for i, row in enumerate(top_rows, 1):
        name = f"{row.first_name or ''} {row.last_name or ''}".strip() or "Inconnu"
        top_data.append([str(i), name, fmt_money(float(row.ca))])

    if len(top_data) == 1:
        top_data.append(["", "Aucune donnee pour ce mois", ""])

    t = Table(top_data, colWidths=[30, 280, 140])
    t.setStyle(section_table_style())
    elements.append(t)
    elements.append(Spacer(1, 6 * mm))


def _append_aging_balance(elements: list, db: object, tenant_id: int, sec_style: object) -> None:
    elements.append(Paragraph("4. Balance agee (impayes)", sec_style))

    now = datetime.now(UTC).replace(tzinfo=None)
    overdue_rows = db.execute(
        select(Payment.amount_due, Payment.amount_paid, Payment.created_at)
        .where(
            Payment.tenant_id == tenant_id,
            Payment.status.in_(["pending", "partial"]),
            Payment.amount_paid < Payment.amount_due,
        )
    ).all()

    buckets: dict[str, float] = {
        "0-30 jours": 0, "30-60 jours": 0,
        "60-90 jours": 0, "> 90 jours": 0,
    }
    for r in overdue_rows:
        days = (now - r.created_at).days if r.created_at else 0
        amount = float(r.amount_due) - float(r.amount_paid)
        if days < 30:
            buckets["0-30 jours"] += amount
        elif days < 60:
            buckets["30-60 jours"] += amount
        elif days < 90:
            buckets["60-90 jours"] += amount
        else:
            buckets["> 90 jours"] += amount

    aging_data = [["Tranche", "Montant impaye"]]
    total_aging = 0.0
    for tranche, amount in buckets.items():
        aging_data.append([tranche, fmt_money(round(amount, 2))])
        total_aging += amount
    aging_data.append(["TOTAL", fmt_money(round(total_aging, 2))])

    t = Table(aging_data, colWidths=[250, 200])
    aging_ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl_colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [
            rl_colors.white, rl_colors.HexColor("#F9FAFB"),
        ]),
        ("BACKGROUND", (0, -1), (-1, -1), rl_colors.HexColor("#F3F4F6")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    t.setStyle(aging_ts)
    elements.append(t)
    elements.append(Spacer(1, 6 * mm))


def _append_opticien_stats(elements: list, db: object, tenant_id: int, month_start: object, month_end: object, sec_style: object, styles: object) -> None:
    elements.append(Paragraph("5. Statistiques opticiens", sec_style))

    opticien_q = (
        select(
            CosiumInvoice.site_id,
            func.coalesce(func.sum(CosiumInvoice.total_ti), 0).label("ca"),
            func.count(CosiumInvoice.id).label("nb_factures"),
        )
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "INVOICE",
            CosiumInvoice.invoice_date >= month_start,
            CosiumInvoice.invoice_date <= month_end,
        )
        .group_by(CosiumInvoice.site_id)
        .order_by(func.sum(CosiumInvoice.total_ti).desc())
    )
    opticien_rows = db.execute(opticien_q).all()

    if opticien_rows:
        opt_data = [["Site / Opticien", "Nb Factures", "CA"]]
        for row in opticien_rows:
            name = f"Site {row.site_id}" if row.site_id else "Non renseigne"
            opt_data.append([name, str(row.nb_factures), fmt_money(float(row.ca))])
        t = Table(opt_data, colWidths=[200, 100, 150])
        t.setStyle(section_table_style())
        elements.append(t)
    else:
        elements.append(Paragraph(
            "Aucune donnee opticien disponible pour ce mois.",
            styles["Normal"],
        ))

