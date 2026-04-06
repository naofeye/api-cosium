"""Parser for optical quotes (devis).

Extracts quote number, date, amounts (HT, TTC, Secu, Mutuelle,
reste a charge) and line items (monture, verres).
"""

from __future__ import annotations

import re
from typing import Any

_NUMBER = r"[\d\s]+[.,]\d{2}"

_NUMERO_DEVIS = re.compile(
    r"(?:devis|n[°o]\s*devis)\s*:?\s*(?P<numero>[A-Z0-9/-]+)",
    re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"(?:date|le|du|fait\s+le|etabli\s+le)\s*:?\s*(?P<date>\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
    re.IGNORECASE,
)

_AMOUNT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "montant_ht",
        re.compile(r"(?:montant|total)\s*HT\s*:?\s*(?P<amount>" + _NUMBER + r")\s*(?:€|EUR)?", re.IGNORECASE),
    ),
    (
        "montant_ttc",
        re.compile(r"(?:montant|total)\s*TTC\s*:?\s*(?P<amount>" + _NUMBER + r")\s*(?:€|EUR)?", re.IGNORECASE),
    ),
    (
        "part_secu",
        re.compile(
            r"(?:part|prise\s+en\s+charge)\s*(?:secu|securite\s+sociale|AMO)\s*:?\s*(?P<amount>" + _NUMBER + r")\s*(?:€|EUR)?",
            re.IGNORECASE,
        ),
    ),
    (
        "part_mutuelle",
        re.compile(
            r"(?:part|prise\s+en\s+charge)\s*(?:mutuelle|complementaire|AMC)\s*:?\s*(?P<amount>" + _NUMBER + r")\s*(?:€|EUR)?",
            re.IGNORECASE,
        ),
    ),
    (
        "reste_a_charge",
        re.compile(
            r"(?:reste\s+a\s+charge|RAC|a\s+votre\s+charge)\s*:?\s*(?P<amount>" + _NUMBER + r")\s*(?:€|EUR)?",
            re.IGNORECASE,
        ),
    ),
]

_LINE_ITEM_PATTERN = re.compile(
    r"(?P<description>monture|verres?|verre\s+(?:droit|gauche)|equipement|traitement|supplement)"
    r"[^€\d]*?"
    r"(?P<amount>" + _NUMBER + r")\s*(?:€|EUR)?",
    re.IGNORECASE,
)


def _parse_amount(s: str) -> float:
    """Convert a French-formatted amount string to float."""
    cleaned = s.replace(" ", "").replace(",", ".")
    return float(cleaned)


def parse_devis(text: str) -> dict[str, Any] | None:
    """Parse a quote document.

    Returns dict with: numero_devis, date, amounts, line_items.
    Returns None if no devis-specific data found.
    """
    if not text or not text.strip():
        return None

    result: dict[str, Any] = {}

    # Quote number
    m = _NUMERO_DEVIS.search(text)
    result["numero_devis"] = m.group("numero").strip() if m else None

    # Date
    m = _DATE_PATTERN.search(text)
    result["date"] = m.group("date") if m else None

    # Amounts
    for field_name, pattern in _AMOUNT_PATTERNS:
        m = pattern.search(text)
        result[field_name] = _parse_amount(m.group("amount")) if m else None

    # Line items
    line_items: list[dict[str, Any]] = []
    for m in _LINE_ITEM_PATTERN.finditer(text):
        line_items.append({
            "description": m.group("description").strip(),
            "montant": _parse_amount(m.group("amount")),
        })
    result["line_items"] = line_items

    # Only return if we found something useful
    has_data = result.get("numero_devis") or result.get("montant_ttc") or line_items
    return result if has_data else None
