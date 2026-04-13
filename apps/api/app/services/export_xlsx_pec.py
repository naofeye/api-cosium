"""Export Excel — preparations PEC avec correction OD/OG, montants, score."""
import io
import json

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.models.client import Customer as CustomerModel
from app.models.pec_preparation import PecPreparation
from app.services._export_styles import THIN_BORDER, apply_header_row, set_column_widths

logger = get_logger("export_xlsx_pec")


def _get_pec_field(profile: dict, key: str) -> str:
    """Lit un champ PEC consolide (gere wrap dict {value, source} ou valeur brute)."""
    field = profile.get(key)
    if isinstance(field, dict):
        return str(field.get("value", "-"))
    return str(field) if field else "-"


def _correction_str(profile: dict, prefix: str) -> str:
    """Formate la correction OD ou OG : Sph / Cyl / Axe / Add."""
    sph = _get_pec_field(profile, f"sphere_{prefix}")
    cyl = _get_pec_field(profile, f"cylinder_{prefix}")
    axe = _get_pec_field(profile, f"axis_{prefix}")
    add = _get_pec_field(profile, f"addition_{prefix}")
    return f"{sph} / {cyl} / {axe} / {add}"


def _load_customer_names(db: Session, customer_ids: list[int]) -> dict[int, str]:
    if not customer_ids:
        return {}
    rows = db.execute(
        select(CustomerModel.id, CustomerModel.first_name, CustomerModel.last_name).where(
            CustomerModel.id.in_(customer_ids),
        )
    ).all()
    return {cid: f"{fn or ''} {ln or ''}".strip() for cid, fn, ln in rows}


@log_operation("export_pec_preparations_xlsx")
def export_pec_preparations_xlsx(
    db: Session,
    tenant_id: int,
    status: str | None = None,
) -> bytes:
    """Export PEC preparations as an Excel file.

    Columns: Client, Mutuelle, N Adherent, Correction OD/OG,
    Montant TTC, Part Secu, Part Mutuelle, RAC, Score, Documents.
    """
    stmt = select(PecPreparation).where(PecPreparation.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(PecPreparation.status == status)
    stmt = stmt.order_by(PecPreparation.created_at.desc())
    preps = list(db.scalars(stmt).all())

    customers_map = _load_customer_names(db, list({p.customer_id for p in preps}))

    wb = Workbook()
    ws = wb.active
    ws.title = "Preparations PEC"

    headers = [
        "Client", "Mutuelle", "N. Adherent",
        "OD (Sph/Cyl/Axe/Add)", "OG (Sph/Cyl/Axe/Add)",
        "Montant TTC", "Part Secu", "Part Mutuelle", "RAC",
        "Score (%)", "Statut", "Documents",
    ]
    apply_header_row(ws, headers)

    for row_idx, prep in enumerate(preps, 2):
        profile: dict = {}
        if prep.consolidated_data:
            try:
                profile = json.loads(prep.consolidated_data)
            except (json.JSONDecodeError, TypeError):
                pass

        doc_count = len(prep.documents) if prep.documents else 0
        row_data = [
            customers_map.get(prep.customer_id, f"Client #{prep.customer_id}"),
            _get_pec_field(profile, "mutuelle_nom"),
            _get_pec_field(profile, "mutuelle_numero_adherent"),
            _correction_str(profile, "od"),
            _correction_str(profile, "og"),
            _get_pec_field(profile, "montant_ttc"),
            _get_pec_field(profile, "part_secu"),
            _get_pec_field(profile, "part_mutuelle"),
            _get_pec_field(profile, "reste_a_charge"),
            round(prep.completude_score, 1),
            prep.status,
            f"{doc_count} doc(s)",
        ]
        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = THIN_BORDER

    set_column_widths(ws, [30, 25, 18, 25, 25, 14, 14, 14, 14, 10, 15, 12])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    logger.info("pec_preparations_xlsx_exported", tenant_id=tenant_id, count=len(preps))
    return output.getvalue()
