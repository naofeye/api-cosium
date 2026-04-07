"""Balance clients PDF export and data helper."""

import io
from datetime import datetime, date

from reportlab.lib import colors as rl_colors
from reportlab.platypus import Paragraph, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import log_operation
from app.models.cosium_data import CosiumInvoice
from app.services.export_pdf_base import (
    create_pdf_doc,
    generated_timestamp,
    logger,
    make_date_style,
    make_title_style,
)


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

@log_operation("export_balance_clients_pdf")
def export_balance_clients_pdf(
    db: Session,
    tenant_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> bytes:
    """Generate a PDF balance report of outstanding client debts."""
    rows = _get_balance_rows(db, tenant_id, date_from, date_to)

    output = io.BytesIO()
    doc = create_pdf_doc(output)

    elements: list = []

    title_style = make_title_style("BalanceTitle")
    date_style = make_date_style("BalanceDate")

    elements.append(Paragraph("Balance Clients — OptiFlow", title_style))

    generated = generated_timestamp()
    period_text = ""
    if date_from or date_to:
        period_text = f" | Periode : {date_from.strftime('%d/%m/%Y') if date_from else '...'}"
        period_text += f" - {date_to.strftime('%d/%m/%Y') if date_to else '...'}"
    elements.append(Paragraph(f"Genere le {generated}{period_text}", date_style))

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
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [
            rl_colors.white, rl_colors.HexColor("#F9FAFB"),
        ]),
    ]))
    elements.append(table)

    doc.build(elements)
    output.seek(0)

    logger.info("balance_clients_pdf_exported", tenant_id=tenant_id, rows=len(rows))
    return output.getvalue()
