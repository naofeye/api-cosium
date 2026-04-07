"""Pre-control engine for PEC preparations.

Runs a comprehensive pre-submission check and produces a structured
result indicating readiness, missing pieces, blocking errors, and
advisory warnings.
"""

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    FieldStatus,
)
from app.models.pec_preparation import PecPreparation

logger = get_logger("pec_precontrol")

# Document roles that can appear in a PEC preparation
REQUIRED_DOCUMENTS = ["ordonnance", "devis"]
RECOMMENDED_DOCUMENTS = ["attestation_mutuelle"]
OPTIONAL_DOCUMENTS = ["carte_vitale"]

# All required PEC fields and their human labels
REQUIRED_FIELDS = {
    "nom": "Nom du client",
    "prenom": "Prenom du client",
    "date_naissance": "Date de naissance",
    "numero_secu": "Numero de securite sociale",
    "mutuelle_nom": "Mutuelle",
    "date_ordonnance": "Date d'ordonnance",
    "montant_ttc": "Montant TTC",
}


class PreControlResult(BaseModel):
    """Result of the pre-submission control on a PEC preparation."""

    status: str = Field(
        ...,
        description="pret | incomplet | conflits | validation_requise",
    )
    status_label: str = Field(
        ...,
        description="Human-readable status label in French",
    )
    completude_score: float = 0.0

    # Document checklist
    pieces_presentes: list[str] = []
    pieces_manquantes: list[str] = []
    pieces_recommandees_manquantes: list[str] = []

    # Issues by severity
    erreurs_bloquantes: list[str] = []
    alertes_verification: list[str] = []
    points_vigilance: list[str] = []

    # Field summary
    champs_confirmes: int = 0
    champs_deduits: int = 0
    champs_en_conflit: int = 0
    champs_manquants: int = 0
    champs_manuels: int = 0
    champs_extraits: int = 0


def _count_field_statuses(
    profile: ConsolidatedClientProfile,
) -> dict[str, int]:
    """Count fields by their FieldStatus."""
    counts: dict[str, int] = {
        "confirmed": 0,
        "extracted": 0,
        "deduced": 0,
        "missing": 0,
        "conflict": 0,
        "manual": 0,
    }

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
            counts["missing"] += 1
            continue
        status_key = field.status.value if isinstance(field.status, FieldStatus) else str(field.status)
        if status_key in counts:
            counts[status_key] += 1
        else:
            counts["extracted"] += 1

    return counts


def _check_documents(prep: PecPreparation) -> tuple[list[str], list[str], list[str]]:
    """Check which documents are present, missing (required), or recommended but absent."""
    present_roles: set[str] = set()
    if prep.documents:
        for doc in prep.documents:
            present_roles.add(doc.document_role)

    pieces_presentes = list(present_roles)
    pieces_manquantes = [r for r in REQUIRED_DOCUMENTS if r not in present_roles]
    pieces_recommandees = [r for r in RECOMMENDED_DOCUMENTS if r not in present_roles]

    return pieces_presentes, pieces_manquantes, pieces_recommandees


def _parse_user_validations(prep: PecPreparation) -> set[str]:
    """Extract the set of field names explicitly validated by the user."""
    import json as _json

    if not prep.user_validations:
        return set()
    try:
        data = _json.loads(prep.user_validations)
    except (ValueError, TypeError):
        return set()
    if not isinstance(data, dict):
        return set()
    return {k for k, v in data.items() if isinstance(v, dict) and v.get("validated")}


def run_precontrol(prep: PecPreparation) -> PreControlResult:
    """Run pre-submission control on a PEC preparation.

    Analyzes field statuses, documents, alerts, and determines readiness.
    Fields explicitly validated by the user (present in ``user_validations``)
    are excluded from blocking errors and warnings.
    """
    # Parse consolidated data
    if not prep.consolidated_data:
        return PreControlResult(
            status="incomplet",
            status_label="Dossier incomplet",
            completude_score=0.0,
            erreurs_bloquantes=["Aucune donnee consolidee — relancez la preparation"],
        )

    profile = ConsolidatedClientProfile.model_validate_json(prep.consolidated_data)

    # Fields the user has explicitly approved — skip alerts for these
    validated_fields = _parse_user_validations(prep)

    # Count fields by status
    counts = _count_field_statuses(profile)

    # Check documents
    pieces_presentes, pieces_manquantes, pieces_recommandees = _check_documents(prep)

    # Collect issues by severity
    erreurs_bloquantes: list[str] = []
    alertes_verification: list[str] = []
    points_vigilance: list[str] = []

    # Missing required fields (skip user-validated ones)
    for field_name, label in REQUIRED_FIELDS.items():
        if field_name in validated_fields:
            continue
        field: ConsolidatedField | None = getattr(profile, field_name, None)
        if field is None or field.value is None:
            erreurs_bloquantes.append(f"{label} manquant(e)")

    # Missing required documents
    for doc_role in pieces_manquantes:
        label_map = {
            "ordonnance": "Ordonnance",
            "devis": "Devis signe",
        }
        erreurs_bloquantes.append(
            f"Document requis manquant : {label_map.get(doc_role, doc_role)}"
        )

    # Recommended documents
    for doc_role in pieces_recommandees:
        label_map = {
            "attestation_mutuelle": "Attestation mutuelle",
        }
        alertes_verification.append(
            f"Document recommande manquant : {label_map.get(doc_role, doc_role)}"
        )

    # Conflicts from profile alerts (deduplicate with required field checks)
    # Track fields already reported as missing to avoid duplicates
    missing_field_names = {f for f in REQUIRED_FIELDS if getattr(profile, f, None) is None or (getattr(profile, f, None) is not None and getattr(profile, f).value is None)}
    for alert in profile.alertes:
        # Skip alerts for fields the user explicitly validated
        if alert.field in validated_fields:
            continue
        # Skip missing-data alerts for fields already reported by required-field check
        if alert.field in missing_field_names and alert.severity == "error":
            continue
        if alert.severity == "error" and alert.message not in erreurs_bloquantes:
            erreurs_bloquantes.append(alert.message)
        elif alert.severity == "warning" and alert.message not in alertes_verification:
            alertes_verification.append(alert.message)
        elif alert.severity == "info":
            points_vigilance.append(alert.message)

    # Field conflicts
    if counts["conflict"] > 0:
        alertes_verification.append(
            f"{counts['conflict']} champ(s) en conflit entre sources — a verifier"
        )

    # Deduced fields advisory
    if counts["deduced"] > 3:
        alertes_verification.append(
            f"{counts['deduced']} champ(s) deduit(s) — verification recommandee"
        )

    # Determine overall status
    any_conflicts = counts["conflict"] > 0
    if erreurs_bloquantes:
        status = "conflits" if any_conflicts else "incomplet"
        status_label = (
            "Conflits a resoudre" if any_conflicts else "Dossier incomplet"
        )
    elif counts["deduced"] > 3:
        status = "validation_requise"
        status_label = "Validation requise"
    else:
        status = "pret"
        status_label = "Dossier pret"

    return PreControlResult(
        status=status,
        status_label=status_label,
        completude_score=profile.score_completude,
        pieces_presentes=pieces_presentes,
        pieces_manquantes=pieces_manquantes,
        pieces_recommandees_manquantes=pieces_recommandees,
        erreurs_bloquantes=erreurs_bloquantes,
        alertes_verification=alertes_verification,
        points_vigilance=points_vigilance,
        champs_confirmes=counts["confirmed"],
        champs_deduits=counts["deduced"],
        champs_en_conflit=counts["conflict"],
        champs_manquants=counts["missing"],
        champs_manuels=counts["manual"],
        champs_extraits=counts["extracted"],
    )
