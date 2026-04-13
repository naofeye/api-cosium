"""Service d'export — facade qui regroupe CSV/XLSX/FEC/PDF.

- CSV/XLSX generique (entites simples) : ce module
- XLSX specialise : `export_xlsx_balance.py`, `export_xlsx_clients.py`, `export_xlsx_pec.py`
- FEC (comptable francais) : `export_fec.py`
- PDF : `export_pdf.py`

Les re-exports en bas garantissent la compatibilite ascendante des imports
`from app.services import export_service` puis `export_service.xxx(...)`.
"""

import csv
import io
from datetime import datetime

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, log_operation
from app.models import (
    AuditLog,
    Campaign,
    Customer,
    Devis,
    Facture,
    Payment,
    PecRequest,
    Reminder,
)

logger = get_logger("export_service")

ENTITY_CONFIGS: dict[str, dict] = {
    "clients": {
        "model": Customer,
        "columns": ["id", "first_name", "last_name", "email", "phone", "city", "postal_code", "created_at"],
        "headers": ["ID", "Prenom", "Nom", "Email", "Telephone", "Ville", "Code postal", "Date creation"],
    },
    "factures": {
        "model": Facture,
        "columns": ["id", "numero", "montant_ht", "tva", "montant_ttc", "status", "date_emission", "created_at"],
        "headers": ["ID", "Numero", "Montant HT", "TVA", "Montant TTC", "Statut", "Date emission", "Date creation"],
    },
    "paiements": {
        "model": Payment,
        "columns": [
            "id", "case_id", "payer_type", "mode_paiement",
            "amount_due", "amount_paid", "status", "created_at",
        ],
        "headers": ["ID", "Dossier", "Type payeur", "Mode", "Montant du", "Montant paye", "Statut", "Date"],
    },
    "devis": {
        "model": Devis,
        "columns": [
            "id", "numero", "status", "montant_ht", "tva", "montant_ttc",
            "part_secu", "part_mutuelle", "reste_a_charge", "created_at",
        ],
        "headers": ["ID", "Numero", "Statut", "HT", "TVA", "TTC", "Part secu", "Part mutuelle", "RAC", "Date"],
    },
    "pec": {
        "model": PecRequest,
        "columns": ["id", "case_id", "organization_id", "montant_demande", "montant_accorde", "status", "created_at"],
        "headers": ["ID", "Dossier", "Organisme", "Montant demande", "Montant accorde", "Statut", "Date"],
    },
    "relances": {
        "model": Reminder,
        "columns": ["id", "target_type", "target_id", "channel", "status", "content", "created_at"],
        "headers": ["ID", "Type cible", "ID cible", "Canal", "Statut", "Contenu", "Date"],
    },
    "campagnes": {
        "model": Campaign,
        "columns": ["id", "name", "channel", "status", "sent_at", "created_at"],
        "headers": ["ID", "Nom", "Canal", "Statut", "Date envoi", "Date creation"],
    },
    "audit_logs": {
        "model": AuditLog,
        "columns": ["id", "user_id", "action", "entity_type", "entity_id", "created_at"],
        "headers": ["ID", "Utilisateur", "Action", "Type entite", "ID entite", "Date"],
    },
}

_MAX_EXPORT_ROWS = 50000


def _get_rows(
    db: Session,
    tenant_id: int,
    entity_type: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[list]:
    config = ENTITY_CONFIGS.get(entity_type)
    if not config:
        return []

    model = config["model"]
    columns = config["columns"]

    q = select(model)
    if hasattr(model, "tenant_id"):
        q = q.where(model.tenant_id == tenant_id)
    if date_from and hasattr(model, "created_at"):
        q = q.where(model.created_at >= date_from)
    if date_to and hasattr(model, "created_at"):
        q = q.where(model.created_at <= date_to)

    items = db.scalars(q.order_by(model.id.desc()).limit(_MAX_EXPORT_ROWS)).all()
    rows = []
    for item in items:
        row = []
        for col in columns:
            val = getattr(item, col, "")
            if isinstance(val, datetime):
                val = val.strftime("%d/%m/%Y %H:%M")
            elif val is None:
                val = ""
            row.append(val)
        rows.append(row)
    return rows


@log_operation("export_csv")
def export_to_csv(
    db: Session,
    tenant_id: int,
    entity_type: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> bytes:
    config = ENTITY_CONFIGS.get(entity_type)
    if not config:
        return b""

    rows = _get_rows(db, tenant_id, entity_type, date_from, date_to)
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(config["headers"])
    writer.writerows(rows)

    logger.info("csv_exported", tenant_id=tenant_id, entity_type=entity_type, rows=len(rows))
    return output.getvalue().encode("utf-8-sig")


@log_operation("export_xlsx")
def export_to_xlsx(
    db: Session,
    tenant_id: int,
    entity_type: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> bytes:
    config = ENTITY_CONFIGS.get(entity_type)
    if not config:
        return b""

    rows = _get_rows(db, tenant_id, entity_type, date_from, date_to)
    wb = Workbook()
    ws = wb.active
    ws.title = entity_type.capitalize()
    ws.append(config["headers"])
    for row in rows:
        ws.append([str(v) for v in row])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    logger.info("xlsx_exported", tenant_id=tenant_id, entity_type=entity_type, rows=len(rows))
    return output.getvalue()


# ---------------------------------------------------------------------------
# Re-exports : conserver l'API publique stable.
# Les callers `export_service.export_balance_clients_xlsx(...)` etc. continuent
# de fonctionner sans migration.
# ---------------------------------------------------------------------------
from app.services.export_fec import generate_fec  # noqa: E402, F401
from app.services.export_pdf import (  # noqa: E402, F401
    export_balance_clients_pdf,
    export_dashboard_pdf,
    export_monthly_report_pdf,
)
from app.services.export_xlsx_balance import export_balance_clients_xlsx  # noqa: E402, F401
from app.services.export_xlsx_clients import export_clients_complet_xlsx  # noqa: E402, F401
from app.services.export_xlsx_pec import export_pec_preparations_xlsx  # noqa: E402, F401
