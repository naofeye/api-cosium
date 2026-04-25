"""Parser for invoices (factures).

Extracts invoice number, date, amounts (HT, TVA, TTC).
"""

from __future__ import annotations

import re
from typing import Any

_NUMBER = r"[\d\s]+[.,]\d{2}"

_NUMERO_FACTURE = re.compile(
    r"(?:n[°o]\s*facture|facture\s*n[°o]?|facture)\s*:\s*(?P<numero>[A-Z0-9][\w/-]*)",
    re.IGNORECASE,
)

_DATE_PATTERN = re.compile(
    r"(?:date|le|du|fait\s+le|emise\s+le)\s*:?\s*(?P<date>\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
    re.IGNORECASE,
)

_MONTANT_HT = re.compile(
    r"(?:montant|total)\s*HT\s*:?\s*(?P<amount>" + _NUMBER + r")\s*(?:€|EUR)?",
    re.IGNORECASE,
)

_TVA = re.compile(
    r"(?:TVA|taxe)\s*(?:\(\d+[.,]?\d*\s*%\))?\s*:?\s*(?P<amount>" + _NUMBER + r")\s*(?:€|EUR)?",
    re.IGNORECASE,
)

_MONTANT_TTC = re.compile(
    r"(?:montant|total|net\s+a\s+payer)\s*TTC\s*:?\s*(?P<amount>" + _NUMBER + r")\s*(?:€|EUR)?",
    re.IGNORECASE,
)


def _parse_amount(s: str) -> float:
    """Convert a French-formatted amount string to float."""
    cleaned = s.replace(" ", "").replace(",", ".")
    return float(cleaned)


def parse_facture(text: str) -> dict[str, Any] | None:
    """Parse an invoice document.

    Returns dict with: numero_facture, date, montant_ht, tva, montant_ttc.
    Returns None if no invoice-specific data found.
    """
    if not text or not text.strip():
        return None

    result: dict[str, Any] = {}

    m = _NUMERO_FACTURE.search(text)
    result["numero_facture"] = m.group("numero").strip() if m else None

    m = _DATE_PATTERN.search(text)
    result["date"] = m.group("date") if m else None

    m = _MONTANT_HT.search(text)
    result["montant_ht"] = _parse_amount(m.group("amount")) if m else None

    m = _TVA.search(text)
    result["tva"] = _parse_amount(m.group("amount")) if m else None

    m = _MONTANT_TTC.search(text)
    result["montant_ttc"] = _parse_amount(m.group("amount")) if m else None

    # Only return if we found something useful
    has_data = result.get("numero_facture") or result.get("montant_ttc")
    return result if has_data else None
