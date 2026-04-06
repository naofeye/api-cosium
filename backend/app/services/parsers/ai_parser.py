"""AI-powered document parser using Claude for structured data extraction.

Falls back to regex parsers if AI is unavailable or fails.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger

logger = get_logger("ai_parser")

_PROMPTS: dict[str, str] = {
    "ordonnance": (
        "Extrais les donnees structurees de cette ordonnance optique.\n"
        "Retourne un JSON avec: prescriber_name, prescription_date (YYYY-MM-DD), "
        "sphere_od, cylinder_od, axis_od, addition_od, "
        "sphere_og, cylinder_og, axis_og, addition_og, "
        "pupillary_distance. Valeurs null si non trouvees."
    ),
    "devis": (
        "Extrais les donnees structurees de ce devis optique.\n"
        "Retourne un JSON avec: numero_devis, date_devis (YYYY-MM-DD), "
        "montant_ht, montant_ttc, part_secu, part_mutuelle, reste_a_charge, "
        "lignes (array of {designation, quantite, prix_unitaire})."
    ),
    "attestation_mutuelle": (
        "Extrais les donnees de cette attestation mutuelle.\n"
        "Retourne un JSON avec: nom_mutuelle, code_organisme, numero_adherent, "
        "nom_assure, prenom_assure, date_debut_droits (YYYY-MM-DD), "
        "date_fin_droits (YYYY-MM-DD)."
    ),
    "facture": (
        "Extrais les donnees de cette facture.\n"
        "Retourne un JSON avec: numero_facture, date_facture (YYYY-MM-DD), "
        "montant_ht, tva, montant_ttc."
    ),
}

_SYSTEM = (
    "Tu es un assistant specialise en extraction de donnees de documents optiques. "
    "Retourne UNIQUEMENT un JSON valide, sans texte avant ou apres."
)

MAX_TEXT_LENGTH = 3000


def _extract_json(text: str) -> dict[str, Any] | None:
    """Try to parse JSON from a response that may contain surrounding text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    return None


def parse_with_ai(text: str, document_type: str) -> dict[str, Any] | None:
    """Use Claude AI to extract structured data from document text.

    Returns a dict of structured fields, or None if the AI is unavailable,
    the document type is unsupported, or parsing fails.
    """
    from app.integrations.ai.claude_provider import claude_provider

    prompt_body = _PROMPTS.get(document_type)
    if prompt_body is None:
        logger.info("ai_parser_no_prompt", document_type=document_type)
        return None

    truncated = text[:MAX_TEXT_LENGTH]
    full_prompt = f"{prompt_body}\n\nTexte du document:\n{truncated}"

    try:
        result = claude_provider.query_with_usage(full_prompt, system=_SYSTEM)
    except Exception:
        logger.exception("ai_parser_query_failed", document_type=document_type)
        return None

    response_text: str = result.get("text", "")

    # If the provider returned a placeholder (no API key), skip
    if response_text.startswith("[IA non configuree]") or response_text.startswith("[Erreur IA]"):
        logger.info("ai_parser_provider_unavailable", document_type=document_type)
        return None

    parsed = _extract_json(response_text)
    if parsed is None:
        logger.warning(
            "ai_parser_json_parse_failed",
            document_type=document_type,
            response_len=len(response_text),
        )
        return None

    logger.info(
        "ai_parser_success",
        document_type=document_type,
        fields=len(parsed),
        tokens_in=result.get("tokens_in", 0),
        tokens_out=result.get("tokens_out", 0),
    )
    return parsed
