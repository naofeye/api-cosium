"""Individual incoherence check functions for consolidated client profiles.

Contains all check functions organized by domain:
- Field status alerts
- Temporal incoherences
- Optical incoherences (range validation, prescription checks)
- Financial incoherences
- Identity incoherences
- Equipment incoherences
- Missing data detection
"""

from datetime import date, datetime, timedelta

from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
    FieldStatus,
)

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


def detect_field_status_alerts(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Generate alerts based on field-level FieldStatus values."""
    alerts: list[ConsolidationAlert] = []

    field_names = [
        "nom", "prenom", "date_naissance", "numero_secu",
        "mutuelle_nom", "mutuelle_numero_adherent", "mutuelle_code_organisme",
        "type_beneficiaire", "date_fin_droits",
        "sphere_od", "cylinder_od", "axis_od", "addition_od",
        "sphere_og", "cylinder_og", "axis_og", "addition_og",
        "ecart_pupillaire", "prescripteur", "date_ordonnance",
        "monture", "montant_ttc", "part_secu", "part_mutuelle", "reste_a_charge",
    ]

    for name in field_names:
        field: ConsolidatedField | None = getattr(profile, name, None)
        if field is None:
            continue
        if field.status == FieldStatus.CONFLICT:
            alt_info = ""
            if field.alternatives:
                alt_values = ", ".join(str(a.get("value", "?")) for a in field.alternatives)
                alt_info = f" (alternatives: {alt_values})"
            alerts.append(
                ConsolidationAlert(
                    severity="warning",
                    field=name,
                    message=f"Conflit entre sources pour {name}: valeur retenue={field.value}{alt_info}",
                    sources=[field.source] + [a.get("source", "") for a in (field.alternatives or [])],
                )
            )
        elif field.status == FieldStatus.DEDUCED:
            alerts.append(
                ConsolidationAlert(
                    severity="info",
                    field=name,
                    message=f"Ce champ est deduit ({field.source_label}), verifiez sa valeur",
                    sources=[field.source],
                )
            )

    return alerts


def detect_temporal_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Detect temporal incoherences between dates."""
    alerts: list[ConsolidationAlert] = []

    ordo_date = None
    if profile.date_ordonnance:
        ordo_date = _parse_date(profile.date_ordonnance.value)

    if ordo_date and profile.montant_ttc and profile.montant_ttc.last_updated:
        devis_date = profile.montant_ttc.last_updated.date() if hasattr(profile.montant_ttc.last_updated, "date") else None
        if devis_date and devis_date < ordo_date - timedelta(days=30):
            alerts.append(
                ConsolidationAlert(
                    severity="warning",
                    field="montant_ttc",
                    message="Devis anterieur a l'ordonnance de plus de 30 jours",
                    sources=[profile.montant_ttc.source],
                )
            )

    client_age = None
    if profile.date_naissance:
        dob = _parse_date(profile.date_naissance.value)
        if dob:
            client_age = _calculate_age(dob)

    if client_age is not None:
        add_od = _safe_float(profile.addition_od.value) if profile.addition_od else None
        add_og = _safe_float(profile.addition_og.value) if profile.addition_og else None
        has_addition = (add_od is not None and add_od > 0) or (add_og is not None and add_og > 0)

        if client_age < 16 and has_addition:
            alerts.append(
                ConsolidationAlert(
                    severity="warning",
                    field="addition",
                    message=f"Addition inhabituelle pour un mineur ({client_age} ans)",
                    sources=[],
                )
            )

        if client_age > 50 and not has_addition:
            alerts.append(
                ConsolidationAlert(
                    severity="info",
                    field="addition",
                    message=f"Pas d'addition declaree pour un presbyte probable ({client_age} ans)",
                    sources=[],
                )
            )

    return alerts


def detect_equipment_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Detect equipment-related incoherences from devis lines."""
    alerts: list[ConsolidationAlert] = []

    has_monture = profile.monture is not None and profile.monture.value
    has_verres = len(profile.verres) > 0

    if not has_monture and profile.montant_ttc:
        alerts.append(
            ConsolidationAlert(
                severity="warning",
                field="monture",
                message="Pas de monture dans le devis",
                sources=[],
            )
        )

    if not has_verres and profile.montant_ttc:
        alerts.append(
            ConsolidationAlert(
                severity="warning",
                field="verres",
                message="Pas de verres dans le devis",
                sources=[],
            )
        )

    add_od = _safe_float(profile.addition_od.value) if profile.addition_od else None
    add_og = _safe_float(profile.addition_og.value) if profile.addition_og else None
    has_addition = (add_od is not None and add_od > 0) or (add_og is not None and add_og > 0)

    if has_addition and has_verres:
        for verre in profile.verres:
            verre_val = str(verre.value).lower() if verre.value else ""
            if "unifocal" in verre_val:
                alerts.append(
                    ConsolidationAlert(
                        severity="warning",
                        field="verres",
                        message="Incoherence : addition prescrite mais verre unifocal dans le devis",
                        sources=[verre.source],
                    )
                )
                break

    return alerts


def detect_optical_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Detect optical data inconsistencies and validate ranges."""
    alerts: list[ConsolidationAlert] = []

    if profile.date_ordonnance:
        ordo_date = _parse_date(profile.date_ordonnance.value)
        if ordo_date:
            today = date.today()
            age_days = (today - ordo_date).days
            if age_days > 3 * 365:
                alerts.append(
                    ConsolidationAlert(
                        severity="error",
                        field="date_ordonnance",
                        message=(
                            f"Ordonnance perimee ({ordo_date.strftime('%d/%m/%Y')}) — "
                            "plus de 3 ans, non utilisable pour PEC"
                        ),
                        sources=[profile.date_ordonnance.source],
                    )
                )
            elif age_days > 365:
                alerts.append(
                    ConsolidationAlert(
                        severity="warning",
                        field="date_ordonnance",
                        message=(
                            f"Ordonnance expiree ({ordo_date.strftime('%d/%m/%Y')}) — "
                            "plus de 1 an"
                        ),
                        sources=[profile.date_ordonnance.source],
                    )
                )

    if profile.addition_od and profile.addition_og:
        add_od = _safe_float(profile.addition_od.value)
        add_og = _safe_float(profile.addition_og.value)
        if add_od is not None and add_og is not None:
            if abs(add_od - add_og) > 0.50:
                alerts.append(
                    ConsolidationAlert(
                        severity="warning",
                        field="addition",
                        message=(
                            f"Ecart d'addition important : OD={add_od:+.2f} vs OG={add_og:+.2f} "
                            f"(ecart {abs(add_od - add_og):.2f})"
                        ),
                        sources=[
                            profile.addition_od.source,
                            profile.addition_og.source,
                        ],
                    )
                )

    range_checks: list[tuple[ConsolidatedField | None, str, str, float, float]] = [
        (profile.sphere_od, "sphere_od", "Sphere OD", SPHERE_MIN, SPHERE_MAX),
        (profile.sphere_og, "sphere_og", "Sphere OG", SPHERE_MIN, SPHERE_MAX),
        (profile.cylinder_od, "cylinder_od", "Cylindre OD", CYLINDER_MIN, CYLINDER_MAX),
        (profile.cylinder_og, "cylinder_og", "Cylindre OG", CYLINDER_MIN, CYLINDER_MAX),
        (profile.axis_od, "axis_od", "Axe OD", AXIS_MIN, AXIS_MAX),
        (profile.axis_og, "axis_og", "Axe OG", AXIS_MIN, AXIS_MAX),
        (profile.addition_od, "addition_od", "Addition OD", ADDITION_MIN, ADDITION_MAX),
        (profile.addition_og, "addition_og", "Addition OG", ADDITION_MIN, ADDITION_MAX),
        (profile.ecart_pupillaire, "ecart_pupillaire", "Ecart pupillaire", PD_MIN, PD_MAX),
    ]

    for field, field_name, label, min_v, max_v in range_checks:
        if field is None:
            continue
        val = _safe_float(field.value)
        alert = _validate_optical_range(val, field_name, label, min_v, max_v, field.source)
        if alert:
            alerts.append(alert)

    return alerts


