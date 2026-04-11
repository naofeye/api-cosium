"""Financial consolidation for PEC preparation.

Handles consolidation of financial fields (montant_ttc, part_secu,
part_mutuelle, reste_a_charge, equipment from devis lines).
"""

from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    FieldStatus,
)
from app.models.devis import Devis, DevisLigne

from app.services.consolidation_helpers import (
    TOLERANCE_AMOUNT,
    _make_field,
    _resolve_field,
)


def consolidate_financial(
    profile: ConsolidatedClientProfile,
    devis: Devis | None,
    devis_lignes: list[DevisLigne],
    ocr_map: dict[str, tuple[dict, str, str, float]],
) -> None:
    """Consolidate financial fields. Devis is ALWAYS the PRIMARY source."""
    d_src = ""
    d_label = ""
    if devis:
        d_src = f"devis_{devis.id}"
        d_label = f"Devis {devis.numero}"

    ocr_devis = ocr_map.get("devis")
    ocr_data = ocr_devis[0] if ocr_devis else {}
    ocr_src = ocr_devis[1] if ocr_devis else ""
    ocr_label = ocr_devis[2] if ocr_devis else ""
    ocr_conf = ocr_devis[3] if ocr_devis else 0.0

    # montant_ttc
    profile.montant_ttc = _resolve_field(
        float(devis.montant_ttc) if devis else None, d_src, d_label, 1.0,
        ocr_data.get("montant_ttc"), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AMOUNT,
    )
    if profile.montant_ttc.status == FieldStatus.MISSING:
        profile.montant_ttc = None

    # part_secu
    profile.part_secu = _resolve_field(
        float(devis.part_secu) if devis else None, d_src, d_label, 1.0,
        ocr_data.get("part_secu"), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AMOUNT,
    )
    if profile.part_secu.status == FieldStatus.MISSING:
        profile.part_secu = None

    # part_mutuelle
    profile.part_mutuelle = _resolve_field(
        float(devis.part_mutuelle) if devis else None, d_src, d_label, 1.0,
        ocr_data.get("part_mutuelle"), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AMOUNT,
    )
    if profile.part_mutuelle.status == FieldStatus.MISSING:
        profile.part_mutuelle = None

    # reste_a_charge
    profile.reste_a_charge = _resolve_field(
        float(devis.reste_a_charge) if devis else None, d_src, d_label, 1.0,
        ocr_data.get("reste_a_charge"), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AMOUNT,
    )
    if profile.reste_a_charge.status == FieldStatus.MISSING:
        profile.reste_a_charge = None

    # Equipment from devis lignes
    if devis and devis_lignes:
        for ligne in devis_lignes:
            designation = ligne.designation.lower()
            if "monture" in designation or "cadre" in designation:
                profile.monture = _make_field(
                    ligne.designation, d_src, d_label, 1.0, FieldStatus.EXTRACTED,
                )
            else:
                profile.verres.append(
                    _make_field(ligne.designation, d_src, d_label, 1.0, FieldStatus.EXTRACTED)
                )
