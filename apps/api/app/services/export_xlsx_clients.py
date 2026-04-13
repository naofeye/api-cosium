"""Export Excel — clients complets (toutes colonnes)."""
import io
from datetime import datetime as _dt

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.models import Customer
from app.services._export_styles import THIN_BORDER, apply_header_row, set_column_widths

logger = get_logger("export_xlsx_clients")


@log_operation("export_clients_complet_xlsx")
def export_clients_complet_xlsx(
    db: Session,
    tenant_id: int,
    date_from=None,
    date_to=None,
    has_email: bool | None = None,
    has_cosium_id: bool | None = None,
) -> bytes:
    """Export ALL clients with ALL data columns in styled Excel format."""
    q = select(Customer).where(Customer.tenant_id == tenant_id, Customer.deleted_at.is_(None))
    if date_from:
        q = q.where(Customer.created_at >= _dt.combine(date_from, _dt.min.time()))
    if date_to:
        q = q.where(Customer.created_at <= _dt.combine(date_to, _dt.max.time()))
    if has_email is True:
        q = q.where(Customer.email.isnot(None), Customer.email != "")
    elif has_email is False:
        q = q.where((Customer.email.is_(None)) | (Customer.email == ""))
    if has_cosium_id is True:
        q = q.where(Customer.cosium_id.isnot(None), Customer.cosium_id != "")
    elif has_cosium_id is False:
        q = q.where((Customer.cosium_id.is_(None)) | (Customer.cosium_id == ""))

    clients = db.scalars(q.order_by(Customer.last_name, Customer.first_name).limit(50000)).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "Clients Complet"

    headers = [
        "Nom", "Prenom", "Date de naissance", "Telephone", "Email",
        "Adresse", "Ville", "Code postal", "N° Secu",
        "N° Client Cosium", "N° Client", "Opticien",
        "Notes", "Date creation",
    ]
    apply_header_row(ws, headers)

    for row_idx, c in enumerate(clients, 2):
        vals = [
            c.last_name,
            c.first_name,
            c.birth_date.strftime("%d/%m/%Y") if c.birth_date else "",
            c.phone or "",
            c.email or "",
            c.address or "",
            c.city or "",
            c.postal_code or "",
            c.social_security_number or "",
            c.cosium_id or "",
            c.customer_number or "",
            c.optician_name or "",
            c.notes or "",
            c.created_at.strftime("%d/%m/%Y %H:%M") if c.created_at else "",
        ]
        for col_idx, val in enumerate(vals, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = THIN_BORDER

    set_column_widths(ws, [20, 15, 16, 18, 30, 35, 20, 12, 18, 18, 15, 20, 30, 18])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    logger.info("clients_complet_xlsx_exported", tenant_id=tenant_id, rows=len(clients))
    return output.getvalue()
