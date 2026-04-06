"""Specialized document parsers for optical industry documents.

Each parser takes raw text and returns a dict with structured fields
(or None if the text does not match the expected format).
"""

from __future__ import annotations

from typing import Any

from app.services.parsers.attestation_mutuelle_parser import parse_attestation_mutuelle
from app.services.parsers.devis_parser import parse_devis
from app.services.parsers.facture_parser import parse_facture
from app.services.parsers.ordonnance_parser import parse_ordonnance

_PARSERS: dict[str, Any] = {
    "ordonnance": parse_ordonnance,
    "devis": parse_devis,
    "attestation_mutuelle": parse_attestation_mutuelle,
    "facture": parse_facture,
}


def parse_document(text: str, document_type: str) -> dict[str, Any] | None:
    """Dispatch to the appropriate parser based on document type.

    Returns structured data dict or None if no parser available / text
    cannot be parsed.
    """
    parser = _PARSERS.get(document_type)
    if parser is None:
        return None
    return parser(text)
