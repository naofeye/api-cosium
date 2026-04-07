"""Incoherence detection engine for consolidated client profiles.

Detects contradictions, anomalies, and missing data that would prevent
a successful PEC submission.  Uses field-level status (FieldStatus) to
generate richer, more actionable alerts.
"""

from datetime import date, datetime, timedelta

from app.core.logging import get_logger
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
    FieldStatus,
)

logger = get_logger("incoherence_detector")

# Optical validation ranges
SPHERE_MIN, SPHERE_MAX = -25.0, 25.0
CYLINDER_MIN, CYLINDER_MAX = -10.0, 0.0  # Always negative in minus-cylinder form
AXIS_MIN, AXIS_MAX = 0, 180
ADDITION_MIN, ADDITION_MAX = 0.50, 4.00
PD_MIN, PD_MAX = 50.0, 80.0  # Pupillary distance in mm


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


def _detect_field_status_alerts(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Generate alerts based on field-level FieldStatus values."""
    alerts: list[ConsolidationAlert] = []

    # All fields that are ConsolidatedField instances on the profile
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


def detect_temporal_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Detect temporal incoherences between dates."""
    alerts: list[ConsolidationAlert] = []

    ordo_date = None
    if profile.date_ordonnance:
        ordo_date = _parse_date(profile.date_ordonnance.value)

    # Devis date vs ordonnance date
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

    # Client age-based checks
    client_age = None
    if profile.date_naissance:
        dob = _parse_date(profile.date_naissance.value)
        if dob:
            client_age = _calculate_age(dob)

    if client_age is not None:
        # Minor with addition
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

        # Presbyopia age without addition
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

    # Check addition vs unifocal incoherence
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

    # Check ordonnance date
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

    # Check addition OD vs OG mismatch (rare in practice)
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

    # Optical range validations
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


def detect_financial_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Detect financial data inconsistencies."""
    alerts: list[ConsolidationAlert] = []

    montant_ttc = _safe_float(profile.montant_ttc.value) if profile.montant_ttc else None
    part_secu = _safe_float(profile.part_secu.value) if profile.part_secu else None
    part_mut = _safe_float(profile.part_mutuelle.value) if profile.part_mutuelle else None
    rac = _safe_float(profile.reste_a_charge.value) if profile.reste_a_charge else None

    # part_secu + part_mutuelle > montant_ttc
    if montant_ttc is not None and part_secu is not None and part_mut is not None:
        total_prise_en_charge = part_secu + part_mut
        if total_prise_en_charge > montant_ttc + 0.01:  # 1 centime de tolerance
            sources = []
            if profile.part_secu:
                sources.append(profile.part_secu.source)
            if profile.part_mutuelle:
                sources.append(profile.part_mutuelle.source)
            if profile.montant_ttc:
                sources.append(profile.montant_ttc.source)
            alerts.append(
                ConsolidationAlert(
                    severity="error",
                    field="financial",
                    message=(
                        f"La part secu ({part_secu:.2f} EUR) + part mutuelle ({part_mut:.2f} EUR) "
                        f"= {total_prise_en_charge:.2f} EUR depasse le montant TTC ({montant_ttc:.2f} EUR)"
                    ),
                    sources=list(dict.fromkeys(sources)),
                )
            )

    # reste_a_charge > montant_ttc
    if rac is not None and montant_ttc is not None and rac > montant_ttc + 0.01:
        alerts.append(
            ConsolidationAlert(
                severity="error",
                field="reste_a_charge",
                message=(
                    f"Le reste a charge ({rac:.2f} EUR) depasse le montant TTC ({montant_ttc:.2f} EUR)"
                ),
                sources=[
                    s for s in [
                        profile.reste_a_charge.source if profile.reste_a_charge else None,
                        profile.montant_ttc.source if profile.montant_ttc else None,
                    ] if s
                ],
            )
        )

    # reste_a_charge < 0
    if rac is not None and rac < -0.01:
        alerts.append(
            ConsolidationAlert(
                severity="error",
                field="reste_a_charge",
                message=f"Le reste a charge est negatif ({rac:.2f} EUR)",
                sources=[profile.reste_a_charge.source] if profile.reste_a_charge else [],
            )
        )

    # part_secu > 60% of montant_ttc
    if part_secu is not None and montant_ttc is not None and montant_ttc > 0:
        ratio = part_secu / montant_ttc
        if ratio > 0.60:
            alerts.append(
                ConsolidationAlert(
                    severity="warning",
                    field="part_secu",
                    message=(
                        f"Part securite sociale ({part_secu:.2f} EUR) superieure a "
                        f"60% du montant TTC ({montant_ttc:.2f} EUR)"
                    ),
                    sources=[profile.part_secu.source] if profile.part_secu else [],
                )
            )

    # Unusually low/high amounts
    if montant_ttc is not None:
        if montant_ttc < 50:
            alerts.append(
                ConsolidationAlert(
                    severity="warning",
                    field="montant_ttc",
                    message=f"Montant inhabituellement bas ({montant_ttc:.2f} EUR)",
                    sources=[profile.montant_ttc.source] if profile.montant_ttc else [],
                )
            )
        elif montant_ttc > 5000:
            alerts.append(
                ConsolidationAlert(
                    severity="warning",
                    field="montant_ttc",
                    message=f"Montant inhabituellement eleve ({montant_ttc:.2f} EUR)",
                    sources=[profile.montant_ttc.source] if profile.montant_ttc else [],
                )
            )

    # part_mutuelle > 0 but no mutuelle identified
    if part_mut is not None and part_mut > 0 and not profile.mutuelle_nom:
        alerts.append(
            ConsolidationAlert(
                severity="warning",
                field="mutuelle_nom",
                message=(
                    f"Part mutuelle de {part_mut:.2f} EUR indiquee mais aucune mutuelle identifiee"
                ),
                sources=[profile.part_mutuelle.source] if profile.part_mutuelle else [],
            )
        )

    return alerts


def detect_identity_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Detect identity data inconsistencies."""
    alerts: list[ConsolidationAlert] = []

    # Check expired mutuelle rights
    if profile.date_fin_droits:
        fin_date = _parse_date(profile.date_fin_droits.value)
        if fin_date and fin_date < date.today():
            alerts.append(
                ConsolidationAlert(
                    severity="error",
                    field="date_fin_droits",
                    message=(
                        f"Droits mutuelle expires le {fin_date.strftime('%d/%m/%Y')} — "
                        "verifier le renouvellement"
                    ),
                    sources=[profile.date_fin_droits.source],
                )
            )

    return alerts


def detect_missing_data(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Detect critical missing data for PEC."""
    alerts: list[ConsolidationAlert] = []

    if not profile.numero_secu:
        alerts.append(
            ConsolidationAlert(
                severity="error",
                field="numero_secu",
                message="Numero de securite sociale requis pour PEC",
                sources=[],
            )
        )

    if not profile.mutuelle_nom:
        alerts.append(
            ConsolidationAlert(
                severity="warning",
                field="mutuelle_nom",
                message="Mutuelle non identifiee",
                sources=[],
            )
        )

    if not profile.mutuelle_numero_adherent:
        alerts.append(
            ConsolidationAlert(
                severity="warning",
                field="mutuelle_numero_adherent",
                message="Numero d'adherent mutuelle manquant",
                sources=[],
            )
        )

    if not profile.date_ordonnance:
        alerts.append(
            ConsolidationAlert(
                severity="error",
                field="date_ordonnance",
                message="Ordonnance requise pour PEC optique",
                sources=[],
            )
        )

    if not profile.montant_ttc:
        alerts.append(
            ConsolidationAlert(
                severity="error",
                field="montant_ttc",
                message="Devis requis pour PEC",
                sources=[],
            )
        )

    if profile.date_ordonnance and not profile.date_ordonnance.value:
        alerts.append(
            ConsolidationAlert(
                severity="warning",
                field="date_ordonnance",
                message="Ordonnance sans date",
                sources=[profile.date_ordonnance.source],
            )
        )

    return alerts


def detect_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Run all incoherence detection rules on a consolidated profile.

    Returns a list of alerts sorted by severity (error first, then warning, then info).
    """
    alerts: list[ConsolidationAlert] = []

    alerts.extend(_detect_field_status_alerts(profile))
    alerts.extend(detect_temporal_incoherences(profile))
    alerts.extend(detect_optical_incoherences(profile))
    alerts.extend(detect_financial_incoherences(profile))
    alerts.extend(detect_identity_incoherences(profile))
    alerts.extend(detect_equipment_incoherences(profile))
    alerts.extend(detect_missing_data(profile))

    # Sort: errors first, then warnings, then info
    severity_order = {"error": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

    logger.info(
        "incoherence_detection_completed",
        total_alerts=len(alerts),
        errors=sum(1 for a in alerts if a.severity == "error"),
        warnings=sum(1 for a in alerts if a.severity == "warning"),
    )

    return alerts
