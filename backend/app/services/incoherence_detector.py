"""Incoherence detection engine for consolidated client profiles.

Detects contradictions, anomalies, and missing data that would prevent
a successful PEC submission.
"""

from datetime import date, datetime

from app.core.logging import get_logger
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidationAlert,
)

logger = get_logger("incoherence_detector")


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


def detect_optical_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Detect optical data inconsistencies."""
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

    alerts.extend(detect_optical_incoherences(profile))
    alerts.extend(detect_financial_incoherences(profile))
    alerts.extend(detect_identity_incoherences(profile))
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
