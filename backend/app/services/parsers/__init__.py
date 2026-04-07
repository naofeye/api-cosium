"""Specialized document parsers for optical industry documents.

Each parser takes raw text and returns a dict with structured fields
(or None if the text does not match the expected format).

When ``use_ai=True``, the dispatcher first attempts extraction via Claude AI
and falls back to the regex-based parsers on failure.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.services.parsers.ai_parser import parse_with_ai
from app.services.parsers.attestation_mutuelle_parser import parse_attestation_mutuelle
from app.services.parsers.devis_parser import parse_devis
from app.services.parsers.facture_parser import parse_facture
from app.services.parsers.ordonnance_parser import parse_ordonnance

logger = get_logger("parsers")

_PARSERS: dict[str, Any] = {
    "ordonnance": parse_ordonnance,
    "devis": parse_devis,
    "attestation_mutuelle": parse_attestation_mutuelle,
    "facture": parse_facture,
}


def parse_document(
    text: str, document_type: str, *, use_ai: bool = False
) -> dict[str, Any] | None:
    """Dispatch to the appropriate parser based on document type.

    When *use_ai* is ``True``, attempts AI extraction first and falls back
    to the regex parser if the AI result is ``None`` or an error occurs.

    Returns structured data dict or None if no parser available / text
    cannot be parsed.
    """
    if use_ai:
        try:
            ai_result = parse_with_ai(text, document_type)
            if ai_result is not None:
                logger.info("ai_extraction_used", document_type=document_type)
                return ai_result
        except (ConnectionError, TimeoutError, ValueError):
            logger.exception("ai_extraction_fallback", document_type=document_type)
        logger.info("ai_extraction_fallback_to_regex", document_type=document_type)

    parser = _PARSERS.get(document_type)
    if parser is None:
        return None
    return parser(text)
