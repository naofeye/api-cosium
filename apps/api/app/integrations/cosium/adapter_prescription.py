"""Adaptateurs Cosium pour le domaine optique : prescriptions + dioptries.

Extrait de adapter.py pour limiter la taille de fichier.
"""
from __future__ import annotations

import json


def _hundredths_to_diopter(value: int | float | None) -> float | None:
    """Convert a Cosium hundredths value to actual diopter.

    E.g. -50 -> -0.50, 225 -> 2.25
    """
    if value is None:
        return None
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return None


def cosium_prescription_to_optiflow(data: dict) -> dict:
    """Mappe une ordonnance optique Cosium vers un dict pour import.

    Structure Cosium : `diopters: [{sphere100Left, sphere100Right, cylinder100Left,
    cylinder100Right, axisLeft, axisRight, addition100Left, addition100Right,
    visionType}], prescriptionDate, fileDate, selectedSpectacles: [...]`.

    Note : les valeurs dioptriques sont en centièmes — diviser par 100.
    Ex. sphere100Left=-50 → -0.50 dioptries.
    """
    cosium_id = data.get("id")
    if not cosium_id:
        self_href = data.get("_links", {}).get("self", {}).get("href", "")
        if "/optical-prescriptions/" in self_href:
            try:
                cosium_id = int(self_href.rsplit("/optical-prescriptions/", 1)[-1].split("?")[0])
            except (ValueError, IndexError):
                pass

    # Extract customer ID from _links
    customer_cosium_id = None
    cust_href = data.get("_links", {}).get("customer", {}).get("href", "")
    if "/customers/" in cust_href:
        try:
            customer_cosium_id = int(cust_href.rsplit("/customers/", 1)[-1].split("?")[0])
        except (ValueError, IndexError):
            pass

    # Parse first diopter entry (distance vision by default)
    diopters = data.get("diopters", [])
    sphere_right = cylinder_right = axis_right = addition_right = None
    sphere_left = cylinder_left = axis_left = addition_left = None

    if diopters and isinstance(diopters, list) and len(diopters) > 0:
        d = diopters[0]
        sphere_right = _hundredths_to_diopter(d.get("sphere100Right"))
        cylinder_right = _hundredths_to_diopter(d.get("cylinder100Right"))
        axis_right = d.get("axisRight")
        addition_right = _hundredths_to_diopter(d.get("addition100Right"))
        sphere_left = _hundredths_to_diopter(d.get("sphere100Left"))
        cylinder_left = _hundredths_to_diopter(d.get("cylinder100Left"))
        axis_left = d.get("axisLeft")
        addition_left = _hundredths_to_diopter(d.get("addition100Left"))

    spectacles = data.get("selectedSpectacles", [])
    spectacles_json = json.dumps(spectacles) if spectacles else None

    prescriber_name = None
    prescriber = data.get("_embedded", {}).get("prescriber", {})
    if prescriber:
        prescriber_name = f"{prescriber.get('firstName', '')} {prescriber.get('lastName', '')}".strip() or None

    return {
        "cosium_id": cosium_id,
        "prescription_date": data.get("prescriptionDate"),
        "file_date": data.get("fileDate"),
        "customer_cosium_id": customer_cosium_id,
        "sphere_right": sphere_right,
        "cylinder_right": cylinder_right,
        "axis_right": axis_right,
        "addition_right": addition_right,
        "sphere_left": sphere_left,
        "cylinder_left": cylinder_left,
        "axis_left": axis_left,
        "addition_left": addition_left,
        "spectacles_json": spectacles_json,
        "prescriber_name": prescriber_name,
    }


def cosium_diopter_to_optiflow(raw: dict) -> dict:
    """Mappe une entree dioptries Cosium vers un dict plat."""
    return {
        "sphere_right": _hundredths_to_diopter(raw.get("sphere100Right")),
        "cylinder_right": _hundredths_to_diopter(raw.get("cylinder100Right")),
        "axis_right": raw.get("axisRight"),
        "addition_right": _hundredths_to_diopter(raw.get("addition100Right")),
        "prism_right": _hundredths_to_diopter(raw.get("prism100Right")),
        "sphere_left": _hundredths_to_diopter(raw.get("sphere100Left")),
        "cylinder_left": _hundredths_to_diopter(raw.get("cylinder100Left")),
        "axis_left": raw.get("axisLeft"),
        "addition_left": _hundredths_to_diopter(raw.get("addition100Left")),
        "prism_left": _hundredths_to_diopter(raw.get("prism100Left")),
        "vision_type": raw.get("visionType"),
    }
