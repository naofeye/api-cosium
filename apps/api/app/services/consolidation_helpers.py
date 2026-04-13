"""Shared helper functions and constants for consolidation modules.

Contains field creation utilities, comparison functions, and constants used
across consolidation_identity, consolidation_optical, and consolidation_financial.

Les data loaders sont dans `consolidation_loaders.py` (re-exportes ci-dessous).
"""

import json
from datetime import UTC, date, datetime

from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    FieldStatus,
)
from app.models.document_extraction import DocumentExtraction

# Fields required for a complete PEC submission
PEC_REQUIRED_FIELDS = [
    "nom",
    "prenom",
    "numero_secu",
    "mutuelle_nom",
    "mutuelle_numero_adherent",
    "date_ordonnance",
    "sphere_od",
    "sphere_og",
    "montant_ttc",
    "part_secu",
    "part_mutuelle",
    "reste_a_charge",
]

# Tolerances for conflict detection
TOLERANCE_SPHERE = 0.25  # Dioptres
TOLERANCE_CYLINDER = 0.25  # Dioptres
TOLERANCE_AXIS = 5  # Degrees
TOLERANCE_ADDITION = 0.25  # Dioptres
TOLERANCE_AMOUNT = 1.00  # EUR


def _make_field(
    value: object,
    source: str,
    source_label: str,
    confidence: float = 1.0,
    status: FieldStatus = FieldStatus.EXTRACTED,
    alternatives: list[dict] | None = None,
    last_updated: datetime | None = None,
) -> ConsolidatedField:
    return ConsolidatedField(
        value=value,
        source=source,
        source_label=source_label,
        confidence=confidence,
        status=status,
        alternatives=alternatives,
        last_updated=last_updated or datetime.now(UTC),
    )


def _make_missing_field() -> ConsolidatedField:
    """Create a field marked as MISSING."""
    return _make_field(
        value=None,
        source="",
        source_label="",
        confidence=0.0,
        status=FieldStatus.MISSING,
    )


def _normalize_date(value: object) -> date | None:
    """Try to parse a date from various formats for comparison."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _values_equal(a: object, b: object) -> bool:
    """Compare two values, normalizing dates if both look like dates."""
    if a == b:
        return True
    da = _normalize_date(a)
    db = _normalize_date(b)
    if da is not None and db is not None:
        return da == db
    return False


def _resolve_field(
    primary_value: object,
    primary_source: str,
    primary_label: str,
    primary_confidence: float,
    secondary_value: object | None = None,
    secondary_source: str = "",
    secondary_label: str = "",
    secondary_confidence: float = 0.0,
    tolerance: float | None = None,
) -> ConsolidatedField:
    """Resolve a field from two sources, detecting conflicts.

    The primary source is used unless absent. If the secondary source
    provides a different value, a CONFLICT status is set (unless within
    tolerance for numeric fields). Date values are normalized before
    comparison to avoid false conflicts from format differences.
    """
    if primary_value is not None:
        field = _make_field(
            primary_value, primary_source, primary_label,
            primary_confidence, FieldStatus.EXTRACTED,
        )
        if secondary_value is not None and not _values_equal(primary_value, secondary_value):
            if tolerance is not None:
                try:
                    diff = abs(float(primary_value) - float(secondary_value))
                    if diff <= tolerance:
                        field.status = FieldStatus.EXTRACTED
                    else:
                        field.status = FieldStatus.CONFLICT
                        field.alternatives = [
                            {"value": secondary_value, "source": secondary_source, "confidence": secondary_confidence}
                        ]
                except (ValueError, TypeError):
                    field.status = FieldStatus.CONFLICT
                    field.alternatives = [
                        {"value": secondary_value, "source": secondary_source, "confidence": secondary_confidence}
                    ]
            else:
                field.status = FieldStatus.CONFLICT
                field.alternatives = [
                    {"value": secondary_value, "source": secondary_source, "confidence": secondary_confidence}
                ]
        return field
    elif secondary_value is not None:
        return _make_field(
            secondary_value, secondary_source, secondary_label,
            secondary_confidence, FieldStatus.DEDUCED,
        )
    else:
        return _make_missing_field()


def _parse_structured_data(extraction: DocumentExtraction) -> dict | None:
    """Parse JSON structured_data from a DocumentExtraction."""
    if not extraction.structured_data:
        return None
    try:
        return json.loads(extraction.structured_data)
    except (json.JSONDecodeError, TypeError):
        return None


def _calculate_completude(profile: ConsolidatedClientProfile) -> float:
    """Calculate completude score (0-100) based on required fields.

    A field counts as filled only if it is a ConsolidatedField with a non-None value.
    """
    filled = 0
    for field_name in PEC_REQUIRED_FIELDS:
        field = getattr(profile, field_name, None)
        if field is not None and isinstance(field, ConsolidatedField) and field.value is not None:
            filled += 1
    total = len(PEC_REQUIRED_FIELDS)
    return round((filled / total) * 100, 1) if total > 0 else 0.0


def _collect_ocr_data(
    extractions: list[DocumentExtraction],
) -> dict[str, tuple[dict, str, str, float]]:
    """Collect the best OCR data per document type.

    Returns a dict keyed by doc_type with (parsed_data, source_id, source_label, confidence).
    Only the first (most recent) extraction per type is kept.
    """
    result: dict[str, tuple[dict, str, str, float]] = {}
    for extraction in extractions:
        doc_type = extraction.document_type or "unknown"
        if doc_type in result:
            continue
        data = _parse_structured_data(extraction)
        if not data:
            continue
        src = f"document_ocr_{extraction.id}"
        src_label = f"Document OCR ({doc_type})"
        confidence = extraction.ocr_confidence or 0.7
        result[doc_type] = (data, src, src_label, confidence)
    return result


# --- Data loaders ---
# Deplaces dans `consolidation_loaders.py`. Re-exportes ici pour compat ascendante.
from app.services.consolidation_loaders import (  # noqa: E402, F401
    load_client_mutuelles,
    load_cosium_client,
    load_devis,
    load_devis_lignes,
    load_document_extractions,
    load_latest_prescription,
)


