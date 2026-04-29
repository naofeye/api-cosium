"""Client import service -- CSV/Excel file import and template generation.

Helpers (column mapping, regexes, readers) sont dans `_client_import_helpers`.
Module re-exporte les noms prives historiques (`_COLUMN_MAP`, `_parse_date`...)
pour preserver la compatibilite avec les tests qui les importent directement.
"""
import csv
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.clients import ClientImportError, ClientImportResult
from app.models.client import Customer
from app.services import audit_service
from app.services._client_import_helpers import (
    COLUMN_MAP,
    EMAIL_RE,
    PHONE_RE,
    detect_delimiter,
    normalize_column,
    parse_date,
    read_excel_rows,
)

logger = get_logger("client_import_service")

# Compat tests : ces noms etaient prives dans la version monolithique
_COLUMN_MAP = COLUMN_MAP
_EMAIL_RE = EMAIL_RE
_PHONE_RE = PHONE_RE
_detect_delimiter = detect_delimiter
_normalize_column = normalize_column
_parse_date = parse_date
_read_excel_rows = read_excel_rows


def import_from_file(
    db: Session,
    tenant_id: int,
    file_content: bytes,
    filename: str,
    user_id: int,
) -> ClientImportResult:
    """Import clients from CSV or Excel file with auto-detection and validation."""
    is_excel = filename.lower().endswith((".xlsx", ".xls"))

    # Parse rows
    if is_excel:
        raw_rows = read_excel_rows(file_content)
    else:
        text = file_content.decode("utf-8-sig")
        delimiter = detect_delimiter(text.split("\n")[0] if text else "")
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        raw_rows = list(reader)

    if not raw_rows:
        return ClientImportResult(imported=0, updated=0, skipped=0, errors=[])

    # Build column mapping from file headers
    sample_keys = list(raw_rows[0].keys())
    col_mapping: dict[str, str] = {}
    for orig_key in sample_keys:
        normalized = normalize_column(orig_key)
        if normalized in COLUMN_MAP:
            col_mapping[orig_key] = COLUMN_MAP[normalized]

    imported = 0
    updated = 0
    skipped = 0
    errors: list[ClientImportError] = []

    for i, raw_row in enumerate(raw_rows, start=2):
        try:
            mapped: dict[str, str] = {}
            for orig_key, field_name in col_mapping.items():
                val = raw_row.get(orig_key, "").strip()
                if val:
                    mapped[field_name] = val

            last_name = mapped.get("last_name", "")
            first_name = mapped.get("first_name", "")
            if not last_name:
                skipped += 1
                errors.append(ClientImportError(line=i, reason="Nom de famille manquant"))
                continue

            email = mapped.get("email")
            if email and not EMAIL_RE.match(email):
                errors.append(ClientImportError(line=i, reason=f"Email invalide : {email}"))
                email = None

            phone = mapped.get("phone")
            if phone and not PHONE_RE.match(phone):
                errors.append(ClientImportError(line=i, reason=f"Telephone invalide : {phone}"))
                phone = None

            birth_date_str = mapped.get("birth_date")
            birth_date = parse_date(birth_date_str) if birth_date_str else None

            existing: Customer | None = None
            if email:
                existing = db.scalars(
                    select(Customer).where(
                        Customer.tenant_id == tenant_id,
                        Customer.email == email,
                        Customer.deleted_at.is_(None),
                    )
                ).first()

            if existing:
                changed = False
                for attr, val in [
                    ("first_name", first_name),
                    ("last_name", last_name),
                    ("phone", phone),
                    ("address", mapped.get("address")),
                    ("city", mapped.get("city")),
                    ("postal_code", mapped.get("postal_code")),
                    ("social_security_number", mapped.get("social_security_number")),
                    ("notes", mapped.get("notes")),
                ]:
                    if val and val != getattr(existing, attr, None):
                        setattr(existing, attr, val)
                        changed = True
                if birth_date:
                    from datetime import date as _date

                    bd = _date.fromisoformat(birth_date)
                    if bd != existing.birth_date:
                        existing.birth_date = bd
                        changed = True
                if changed:
                    updated += 1
                else:
                    skipped += 1
            else:
                customer_kwargs: dict[str, object] = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": phone,
                    "address": mapped.get("address"),
                    "city": mapped.get("city"),
                    "postal_code": mapped.get("postal_code"),
                    "social_security_number": mapped.get("social_security_number"),
                    "notes": mapped.get("notes"),
                }
                if birth_date:
                    from datetime import date as _date
                    customer_kwargs["birth_date"] = _date.fromisoformat(birth_date)
                customer = Customer(
                    tenant_id=tenant_id,
                    **{k: v for k, v in customer_kwargs.items() if v is not None},
                )
                db.add(customer)
                imported += 1
        except Exception as e:
            errors.append(ClientImportError(line=i, reason=str(e)))
            skipped += 1

    db.commit()
    audit_service.log_action(
        db,
        tenant_id,
        user_id,
        "create",
        "client_import",
        0,
        new_value={"imported": imported, "updated": updated, "skipped": skipped},
    )
    logger.info(
        "file_import_completed",
        tenant_id=tenant_id,
        imported=imported,
        updated=updated,
        skipped=skipped,
        filename=filename,
    )
    return ClientImportResult(imported=imported, updated=updated, skipped=skipped, errors=errors[:50])


def generate_import_template() -> bytes:
    """Generate a CSV template for client import."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Nom", "Prenom", "Email", "Telephone", "Date de naissance",
        "Adresse", "Ville", "Code postal", "N° Secu", "Notes",
    ])
    writer.writerow([
        "Dupont", "Jean", "jean.dupont@email.fr", "06 12 34 56 78", "15/03/1985",
        "12 rue de la Paix", "Paris", "75001", "1850375012345", "Client fidele",
    ])
    return output.getvalue().encode("utf-8-sig")
