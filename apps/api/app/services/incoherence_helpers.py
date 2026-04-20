"""Helper utilities for incoherence check functions.

Contains:
- Optical validation range constants
- Date/float parsing utilities
- Range validation helper
- Age calculation helper
"""

from datetime import date, datetime

from app.domain.schemas.consolidation import ConsolidationAlert

# Optical validation ranges
SPHERE_MIN, SPHERE_MAX = -25.0, 25.0
CYLINDER_MIN, CYLINDER_MAX = -10.0, 10.0
AXIS_MIN, AXIS_MAX = 0, 180
ADDITION_MIN, ADDITION_MAX = 0.50, 4.00
PD_MIN, PD_MAX = 50.0, 80.0


def _parse_date(value: object) -> date | None:
    """Try to parse a date from various formats."""
    if isinstance(value, date):
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


def _safe_float(value: object) -> float | None:
    """Try to convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _validate_optical_range(
    value: float | None, field_name: str, label: str,
    min_val: float, max_val: float, source: str,
) -> ConsolidationAlert | None:
    """Validate an optical value is within a valid range."""
    if value is None:
        return None
    if value < min_val or value > max_val:
        return ConsolidationAlert(
            severity="error",
            field=field_name,
            message=(
                f"{label} hors plage valide : {value} "
                f"(attendu entre {min_val} et {max_val})"
            ),
            sources=[source] if source else [],
        )
    return None


def _calculate_age(date_naissance: date) -> int:
    """Calculate age in years from a birth date."""
    today = date.today()
    return today.year - date_naissance.year - (
        (today.month, today.day) < (date_naissance.month, date_naissance.day)
    )
