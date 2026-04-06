"""Parser for optical prescriptions (ordonnances).

Extracts OD/OG correction values (sphere, cylinder, axis, addition),
prescriber info, and pupillary distance from raw OCR text.
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# Regex patterns for correction values
# ---------------------------------------------------------------------------

# Matches patterns like: OD +2.50 (-0.75 a 90) Add +2.00
# Or: OD : +2,50 (-0,75 a 90°) Add +2,00
# Or: Sph +2.50 Cyl -0.75 Axe 90 Add +2.00
_NUMBER = r"[+-]?\d+[.,]\d+"
_INT = r"\d+"

# Pattern 1: OD/OG inline format
# Handles: OD +2.50 (-0.75 a 90°) Add +2.00
#           OD +2,50 (-0,75) 90 Add 2,00
#           OD : +2.50 (-0.75 a 90°) Add +2.00
_EYE_PATTERN = re.compile(
    r"(?P<eye>OD|OG|oeil\s+droit|oeil\s+gauche)"
    r"\s*:?\s*"
    r"(?P<sphere>" + _NUMBER + r")"
    r"(?:\s*\(?\s*(?P<cylinder>" + _NUMBER + r")"
    r"\s*\)?\s*(?:a|à)?\s*(?P<axis>" + _INT + r")[°]?\s*\)?)?"
    r"(?:\s*(?:Add|add|ADD)\s*(?P<addition>" + _NUMBER + r"))?",
    re.IGNORECASE,
)

# Pattern 2: Labeled format (Sph / Cyl / Axe / Add on same line with eye label)
_LABELED_PATTERN = re.compile(
    r"(?P<eye>OD|OG|oeil\s+droit|oeil\s+gauche)"
    r".*?"
    r"(?:Sph|sphere)\s*:?\s*(?P<sphere>" + _NUMBER + r")"
    r".*?"
    r"(?:Cyl|cylindre)\s*:?\s*(?P<cylinder>" + _NUMBER + r")"
    r".*?"
    r"(?:Axe|axis|ax)\s*:?\s*(?P<axis>" + _INT + r")"
    r"(?:.*?(?:Add|addition)\s*:?\s*(?P<addition>" + _NUMBER + r"))?",
    re.IGNORECASE,
)

_PD_PATTERN = re.compile(
    r"(?:ecart\s*pupillaire|EP|PD|ecart\s*inter-pupillaire)\s*:?\s*(?P<pd>\d+[.,]?\d*)\s*(?:mm)?",
    re.IGNORECASE,
)

_PRESCRIBER_PATTERN = re.compile(
    r"(?:Dr|Docteur|Medecin|Ophtalmologue|Ophtalmologiste)\s*:?\s*(?P<name>[A-Z\u00C0-\u00FF][a-zA-Z\u00C0-\u00FF\s-]+)",
    re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"(?:date|le|du|fait\s+le)\s*:?\s*(?P<date>\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
    re.IGNORECASE,
)


def _normalize_number(s: str | None) -> float | None:
    if s is None:
        return None
    return float(s.replace(",", "."))


def _normalize_eye(raw: str) -> str:
    low = raw.lower().strip()
    if low in ("od", "oeil droit"):
        return "OD"
    if low in ("og", "oeil gauche"):
        return "OG"
    return raw.upper()


def parse_ordonnance(text: str) -> dict[str, Any] | None:
    """Parse an optical prescription from raw text.

    Returns a dict with keys: od, og, prescriber, date, pupillary_distance.
    Each eye entry has: sphere, cylinder, axis, addition, confidence.
    Returns None if no correction data found.
    """
    if not text or not text.strip():
        return None

    eyes: dict[str, dict[str, Any]] = {}

    # Try both patterns
    for pattern in (_EYE_PATTERN, _LABELED_PATTERN):
        for match in pattern.finditer(text):
            eye = _normalize_eye(match.group("eye"))
            if eye in eyes:
                continue

            sphere = _normalize_number(match.group("sphere"))
            cylinder = _normalize_number(match.group("cylinder"))
            axis_str = match.group("axis")
            axis = int(axis_str) if axis_str else None
            addition = _normalize_number(match.group("addition"))

            fields_found = sum(1 for v in [sphere, cylinder, axis, addition] if v is not None)
            confidence = fields_found / 4.0

            eyes[eye] = {
                "sphere": sphere,
                "cylinder": cylinder,
                "axis": axis,
                "addition": addition,
                "confidence": round(confidence, 2),
            }

    if not eyes:
        return None

    result: dict[str, Any] = {
        "od": eyes.get("OD"),
        "og": eyes.get("OG"),
    }

    # Prescriber
    prescriber_match = _PRESCRIBER_PATTERN.search(text)
    result["prescriber"] = prescriber_match.group("name").strip() if prescriber_match else None

    # Date
    date_match = _DATE_PATTERN.search(text)
    result["date"] = date_match.group("date") if date_match else None

    # Pupillary distance
    pd_match = _PD_PATTERN.search(text)
    result["pupillary_distance"] = (
        float(pd_match.group("pd").replace(",", ".")) if pd_match else None
    )

    return result
