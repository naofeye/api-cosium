"""Identity and mutuelle consolidation for PEC preparation.

Handles consolidation of identity fields (nom, prenom, date_naissance, numero_secu)
and mutuelle fields (mutuelle_nom, mutuelle_numero_adherent, etc.).
"""

from datetime import UTC

from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    FieldStatus,
)
from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle

from app.services.consolidation_helpers import _make_field, _resolve_field, _make_missing_field


def consolidate_identity(
    profile: ConsolidatedClientProfile,
    customer: Customer | None,
    ocr_map: dict[str, tuple[dict, str, str, float]],
) -> None:
    """Consolidate identity fields. Cosium client is PRIMARY."""
    ocr_att = ocr_map.get("attestation_mutuelle")
    ocr_att_data = ocr_att[0] if ocr_att else {}
    ocr_src = ocr_att[1] if ocr_att else ""
    ocr_label = ocr_att[2] if ocr_att else ""
    ocr_conf = ocr_att[3] if ocr_att else 0.0

    now = (customer.updated_at or customer.created_at) if customer else None

    profile.nom = _resolve_field(
        customer.last_name if customer else None, "cosium_client", "Cosium", 1.0,
        ocr_att_data.get("nom"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.nom.status == FieldStatus.MISSING:
        profile.nom = None

    profile.prenom = _resolve_field(
        customer.first_name if customer else None, "cosium_client", "Cosium", 1.0,
        ocr_att_data.get("prenom"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.prenom.status == FieldStatus.MISSING:
        profile.prenom = None

    if customer and customer.birth_date:
        profile.date_naissance = _make_field(
            str(customer.birth_date), "cosium_client", "Cosium", 1.0,
            last_updated=now,
        )

    profile.numero_secu = _resolve_field(
        customer.social_security_number if customer else None, "cosium_client", "Cosium", 1.0,
        ocr_att_data.get("numero_secu"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.numero_secu.status == FieldStatus.MISSING:
        profile.numero_secu = None


def consolidate_mutuelle(
    profile: ConsolidatedClientProfile,
    mutuelles: list[ClientMutuelle],
    ocr_map: dict[str, tuple[dict, str, str, float]],
) -> None:
    """Consolidate mutuelle fields. OCR attestation is PRIMARY (most detail), Cosium TPP confirms."""
    ocr_att = ocr_map.get("attestation_mutuelle")
    ocr_data = ocr_att[0] if ocr_att else {}
    ocr_src = ocr_att[1] if ocr_att else ""
    ocr_label = ocr_att[2] if ocr_att else ""
    ocr_conf = ocr_att[3] if ocr_att else 0.0

    best = mutuelles[0] if mutuelles else None
    m_src = f"mutuelle_{best.source}" if best else ""
    m_label = f"Mutuelle ({best.source})" if best else ""
    m_conf = best.confidence if best else 0.0

    # For mutuelle, OCR attestation is PRIMARY
    profile.mutuelle_nom = _resolve_field(
        ocr_data.get("mutuelle_nom"), ocr_src, ocr_label, ocr_conf,
        best.mutuelle_name if best else None, m_src, m_label, m_conf,
    )
    if profile.mutuelle_nom.status == FieldStatus.MISSING:
        profile.mutuelle_nom = None

    profile.mutuelle_numero_adherent = _resolve_field(
        ocr_data.get("numero_adherent"), ocr_src, ocr_label, ocr_conf,
        best.numero_adherent if best else None, m_src, m_label, m_conf,
    )
    if profile.mutuelle_numero_adherent.status == FieldStatus.MISSING:
        profile.mutuelle_numero_adherent = None

    if ocr_data.get("code_organisme"):
        profile.mutuelle_code_organisme = _make_field(
            ocr_data["code_organisme"], ocr_src, ocr_label, ocr_conf, FieldStatus.EXTRACTED,
        )
    elif best and getattr(best, "code_organisme", None):
        profile.mutuelle_code_organisme = _make_field(
            best.code_organisme, m_src, m_label, m_conf, FieldStatus.DEDUCED,
        )

    # Type beneficiaire
    if best and best.type_beneficiaire:
        profile.type_beneficiaire = _make_field(
            best.type_beneficiaire, m_src, m_label, m_conf, FieldStatus.EXTRACTED,
        )

    # Date fin droits
    date_fin_ocr = ocr_data.get("date_fin_droits")
    date_fin_mut = str(best.date_fin) if best and best.date_fin else None
    profile.date_fin_droits = _resolve_field(
        date_fin_ocr, ocr_src, ocr_label, ocr_conf,
        date_fin_mut, m_src, m_label, m_conf,
    )
    if profile.date_fin_droits.status == FieldStatus.MISSING:
        profile.date_fin_droits = None
