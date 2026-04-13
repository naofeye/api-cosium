"""Optical correction consolidation for PEC preparation.

Handles consolidation of optical fields (sphere, cylinder, axis, addition,
ecart pupillaire, prescripteur, date ordonnance).
"""

from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    FieldStatus,
)
from app.models.cosium_data import CosiumPrescription
from app.services.consolidation_helpers import (
    TOLERANCE_ADDITION,
    TOLERANCE_AXIS,
    TOLERANCE_CYLINDER,
    TOLERANCE_SPHERE,
    _make_field,
    _resolve_field,
)


def consolidate_optical(
    profile: ConsolidatedClientProfile,
    prescription: CosiumPrescription | None,
    ocr_map: dict[str, tuple[dict, str, str, float]],
) -> None:
    """Consolidate optical fields. Cosium prescription is PRIMARY, OCR ordonnance is alternative."""
    p_src = ""
    p_label = ""
    p_conf = 0.95
    if prescription:
        p_src = f"cosium_prescription_{prescription.id}"
        p_label = "Ordonnance Cosium"
        if prescription.prescription_date:
            p_label = f"Ordonnance du {prescription.prescription_date}"

    ocr_ord = ocr_map.get("ordonnance")
    ocr_data: dict = {}
    ocr_src = ""
    ocr_label = ""
    ocr_conf = 0.0
    if ocr_ord:
        ocr_data, ocr_src, ocr_label, ocr_conf = ocr_ord
    od_data = ocr_data.get("od", {}) if isinstance(ocr_data.get("od"), dict) else {}
    og_data = ocr_data.get("og", {}) if isinstance(ocr_data.get("og"), dict) else {}

    def _ocr_val(flat_key: str, nested_dict: dict, nested_keys: list[str]) -> object:
        val = ocr_data.get(flat_key)
        if val is not None:
            return val
        for k in nested_keys:
            val = nested_dict.get(k)
            if val is not None:
                return val
        return None

    # Sphere OD/OG
    profile.sphere_od = _resolve_field(
        prescription.sphere_right if prescription and prescription.sphere_right is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("sphere_od", od_data, ["sphere"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_SPHERE,
    )
    if profile.sphere_od.status == FieldStatus.MISSING:
        profile.sphere_od = None

    profile.sphere_og = _resolve_field(
        prescription.sphere_left if prescription and prescription.sphere_left is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("sphere_og", og_data, ["sphere"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_SPHERE,
    )
    if profile.sphere_og.status == FieldStatus.MISSING:
        profile.sphere_og = None

    # Cylinder OD/OG
    profile.cylinder_od = _resolve_field(
        prescription.cylinder_right if prescription and prescription.cylinder_right is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("cylinder_od", od_data, ["cylindre", "cylinder"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_CYLINDER,
    )
    if profile.cylinder_od.status == FieldStatus.MISSING:
        profile.cylinder_od = None

    profile.cylinder_og = _resolve_field(
        prescription.cylinder_left if prescription and prescription.cylinder_left is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("cylinder_og", og_data, ["cylindre", "cylinder"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_CYLINDER,
    )
    if profile.cylinder_og.status == FieldStatus.MISSING:
        profile.cylinder_og = None

    # Axis OD/OG
    profile.axis_od = _resolve_field(
        prescription.axis_right if prescription and prescription.axis_right is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("axis_od", od_data, ["axe", "axis"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AXIS,
    )
    if profile.axis_od.status == FieldStatus.MISSING:
        profile.axis_od = None

    profile.axis_og = _resolve_field(
        prescription.axis_left if prescription and prescription.axis_left is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("axis_og", og_data, ["axe", "axis"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_AXIS,
    )
    if profile.axis_og.status == FieldStatus.MISSING:
        profile.axis_og = None

    # Addition OD/OG
    profile.addition_od = _resolve_field(
        prescription.addition_right if prescription and prescription.addition_right is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("addition_od", od_data, ["addition"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_ADDITION,
    )
    if profile.addition_od.status == FieldStatus.MISSING:
        profile.addition_od = None

    profile.addition_og = _resolve_field(
        prescription.addition_left if prescription and prescription.addition_left is not None else None,
        p_src, p_label, p_conf,
        _ocr_val("addition_og", og_data, ["addition"]), ocr_src, ocr_label, ocr_conf,
        tolerance=TOLERANCE_ADDITION,
    )
    if profile.addition_og.status == FieldStatus.MISSING:
        profile.addition_og = None

    # Ecart pupillaire (OCR only typically)
    ep_ocr = ocr_data.get("ecart_pupillaire") if ocr_data else None
    if ep_ocr is not None:
        profile.ecart_pupillaire = _make_field(ep_ocr, ocr_src, ocr_label, ocr_conf, FieldStatus.DEDUCED)

    # Prescripteur
    profile.prescripteur = _resolve_field(
        prescription.prescriber_name if prescription and prescription.prescriber_name else None,
        p_src, p_label, p_conf,
        ocr_data.get("prescripteur"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.prescripteur.status == FieldStatus.MISSING:
        profile.prescripteur = None

    # Date ordonnance
    profile.date_ordonnance = _resolve_field(
        prescription.prescription_date if prescription and prescription.prescription_date else None,
        p_src, p_label, p_conf,
        ocr_data.get("date_ordonnance"), ocr_src, ocr_label, ocr_conf,
    )
    if profile.date_ordonnance.status == FieldStatus.MISSING:
        profile.date_ordonnance = None
