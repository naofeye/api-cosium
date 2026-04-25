"""Financial and identity incoherence checks for consolidated profiles.

Contains check functions for financial data validation, identity
data inconsistencies (mutuelle expiration), and missing data detection.
"""

from datetime import date, datetime

from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidationAlert,
)


def _parse_date(value: object) -> date | None:
    """Try to parse a date from various formats."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
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


def detect_financial_incoherences(
    profile: ConsolidatedClientProfile,
) -> list[ConsolidationAlert]:
    """Detect financial data inconsistencies."""
    alerts: list[ConsolidationAlert] = []

    montant_ttc = _safe_float(profile.montant_ttc.value) if profile.montant_ttc else None
    part_secu = _safe_float(profile.part_secu.value) if profile.part_secu else None
    part_mut = _safe_float(profile.part_mutuelle.value) if profile.part_mutuelle else None
    rac = _safe_float(profile.reste_a_charge.value) if profile.reste_a_charge else None

    if montant_ttc is not None and part_secu is not None and part_mut is not None:
        total_prise_en_charge = part_secu + part_mut
        if total_prise_en_charge > montant_ttc + 0.01:
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

    if rac is not None and rac < -0.01:
        alerts.append(
            ConsolidationAlert(
                severity="error",
                field="reste_a_charge",
                message=f"Le reste a charge est negatif ({rac:.2f} EUR)",
                sources=[profile.reste_a_charge.source] if profile.reste_a_charge else [],
            )
        )

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
