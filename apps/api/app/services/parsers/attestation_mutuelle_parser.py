"""Parser for mutual insurance attestations (attestation mutuelle).

Extracts insurer name, organization code, member number,
insured person name, and coverage dates.
"""

from __future__ import annotations

import re
from typing import Any

_MUTUELLE_NAME = re.compile(
    r"(?:mutuelle|organisme|complementaire)\s*:\s*(?P<name>[A-Z\u00C0-\u00FF][A-Za-z\u00C0-\u00FF -]*[A-Za-z\u00C0-\u00FF])",
    re.IGNORECASE,
)

_CODE_ORGANISME = re.compile(
    r"(?:code\s+organisme|code\s+AMC|code\s+mutuelle)\s*:?\s*(?P<code>[A-Z0-9]+)",
    re.IGNORECASE,
)

_NUMERO_ADHERENT = re.compile(
    r"(?:n[°o]\s*adherent|numero\s+adherent|n[°o]\s*membre)\s*:?\s*(?P<numero>[A-Z0-9/-]+)",
    re.IGNORECASE,
)

_NOM_ASSURE = re.compile(
    r"(?:nom\s+(?:de\s+l'?)?assure|titulaire|beneficiaire)\s*:?\s*(?P<name>[A-Z\u00C0-\u00FF][a-zA-Z\u00C0-\u00FF -]*[a-zA-Z\u00C0-\u00FF])",
    re.IGNORECASE,
)

_PRENOM_ASSURE = re.compile(
    r"(?:prenom)\s*:?\s*(?P<prenom>[A-Z\u00C0-\u00FF][a-zA-Z\u00C0-\u00FF-]+)",
    re.IGNORECASE,
)

_DATE_DEBUT = re.compile(
    r"(?:date\s+(?:de\s+)?debut|valable\s+(?:a\s+partir\s+)?du|du)\s*:?\s*(?P<date>\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
    re.IGNORECASE,
)

_DATE_FIN = re.compile(
    r"(?:date\s+(?:de\s+)?fin|valable\s+jusqu'?\s*au|au)\s*:?\s*(?P<date>\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})",
    re.IGNORECASE,
)


def parse_attestation_mutuelle(text: str) -> dict[str, Any] | None:
    """Parse a mutual insurance attestation.

    Returns dict with: nom_mutuelle, code_organisme, numero_adherent,
    nom_assure, prenom_assure, date_debut_droits, date_fin_droits.
    Returns None if no relevant data found.
    """
    if not text or not text.strip():
        return None

    result: dict[str, Any] = {}

    m = _MUTUELLE_NAME.search(text)
    result["nom_mutuelle"] = m.group("name").strip() if m else None

    m = _CODE_ORGANISME.search(text)
    result["code_organisme"] = m.group("code").strip() if m else None

    m = _NUMERO_ADHERENT.search(text)
    result["numero_adherent"] = m.group("numero").strip() if m else None

    m = _NOM_ASSURE.search(text)
    result["nom_assure"] = m.group("name").strip() if m else None

    m = _PRENOM_ASSURE.search(text)
    result["prenom_assure"] = m.group("prenom").strip() if m else None

    m = _DATE_DEBUT.search(text)
    result["date_debut_droits"] = m.group("date") if m else None

    m = _DATE_FIN.search(text)
    result["date_fin_droits"] = m.group("date") if m else None

    # Only return if we found something useful
    has_data = any(
        result.get(k) for k in ("nom_mutuelle", "code_organisme", "numero_adherent")
    )
    return result if has_data else None
