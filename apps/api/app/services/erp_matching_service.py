"""
Service de matching et normalisation des clients ERP -> OptiFlow.

Contient la logique de :
- Normalisation des noms (accents, prefixes, casse)
- Matching des clients Cosium vers OptiFlow (par cosium_id, email, nom)
- Validation des donnees client ERP
- Creation / mise a jour de clients depuis les donnees ERP

SYNCHRONISATION UNIDIRECTIONNELLE : ERP -> OptiFlow uniquement.
"""

import unicodedata

from app.core.logging import get_logger
from app.integrations.erp_models import ERPCustomer
from app.models import Customer

logger = get_logger("erp_matching_service")


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------


def _normalize_name(name: str) -> str:
    """Normalize name for matching: remove accents, uppercase, strip extra spaces."""
    # Remove accents
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Uppercase, strip, normalize hyphens (double or single -> space)
    result = ascii_only.upper().strip()
    result = result.replace("--", "-").replace("-", " ")
    # Collapse multiple spaces
    result = " ".join(result.split())
    return result


def _normalize_phone(phone: str | None) -> str | None:
    """Normalize a phone number: strip spaces, ensure starts with + or 0."""
    if not phone:
        return phone
    normalized = phone.replace(" ", "").replace(".", "").replace("-", "")
    if normalized and not normalized.startswith("+") and not normalized.startswith("0"):
        normalized = "0" + normalized
    return normalized


# ---------------------------------------------------------------------------
# Customer matching
# ---------------------------------------------------------------------------


def _match_customer_by_name(customer_name: str, name_map: dict[str, int]) -> int | None:
    """Try to match a Cosium customerName to an OptiFlow customer ID.

    Cosium format: "M. LASTNAME FIRSTNAME", "Mme. LASTNAME FIRSTNAME", "MME LASTNAME FIRSTNAME".
    Strategies: exact match -> strip prefix -> reverse first/last -> partial (2-word prefix).

    Both the input name and map keys are normalized (accent-insensitive,
    hyphen-normalised, uppercased) before comparison.
    """
    if not customer_name:
        return None

    # Build a normalized version of the map for accent/hyphen-insensitive matching
    normalized_map: dict[str, int] = {}
    for key, cid in name_map.items():
        norm_key = _normalize_name(key)
        # Keep the first mapping (don't overwrite)
        if norm_key not in normalized_map:
            normalized_map[norm_key] = cid

    normalized = _normalize_name(customer_name)

    # Direct match
    if normalized in normalized_map:
        return normalized_map[normalized]

    # Strip title prefixes (including with dot and without)
    stripped = normalized
    for prefix in ("M. ", "MME. ", "MLLE. ", "MME ", "MLLE ", "MR. ", "MR ", "MRS. ", "MRS ", "DR. ", "DR "):
        if normalized.startswith(prefix):
            stripped = normalized[len(prefix):]
            break

    if stripped in normalized_map:
        return normalized_map[stripped]

    # Try "FIRSTNAME LASTNAME" -> "LASTNAME FIRSTNAME" (reverse words)
    parts = stripped.split()
    if len(parts) >= 2:
        # Try LAST FIRST (move last word to front)
        reversed_name = f"{parts[-1]} {' '.join(parts[:-1])}"
        if reversed_name in normalized_map:
            return normalized_map[reversed_name]
        # Try just first and last word swapped
        simple_reverse = f"{parts[0]} {parts[-1]}"
        if simple_reverse in normalized_map:
            return normalized_map[simple_reverse]

    # Partial matching: try just the first 2 words (handles compound names
    # like "RENGIG KULISKOVA LUBICA" matching "KULISKOVA LUBICA" or vice versa)
    if len(parts) >= 2:
        two_word = f"{parts[0]} {parts[1]}"
        if two_word in normalized_map:
            return normalized_map[two_word]

    # Try matching the last 2 words (e.g. "RENGIG KULISKOVA LUBICA" -> "KULISKOVA LUBICA")
    if len(parts) >= 3:
        last_two = f"{parts[-2]} {parts[-1]}"
        if last_two in normalized_map:
            return normalized_map[last_two]

    # LAST RESORT: fuzzy matching on normalized names (score >= 85)
    try:
        from rapidfuzz import fuzz

        best_match = None
        best_score = 0.0
        for map_name, cust_id in normalized_map.items():
            score = fuzz.ratio(stripped, map_name)
            if score > best_score and score >= 85:
                best_score = score
                best_match = cust_id
        if best_match is not None:
            return best_match
    except ImportError:
        pass

    return None


# ---------------------------------------------------------------------------
# ERP data validation
# ---------------------------------------------------------------------------


def _validate_erp_customer_data(erp_c: ERPCustomer) -> list[str]:
    """Validate ERP customer data and return list of warnings.

    ERP is source of truth so data is stored anyway, but invalid
    fields are logged as warnings for data quality tracking.
    """
    warnings: list[str] = []
    erp_label = f"erp_id={erp_c.erp_id}, name={erp_c.last_name} {erp_c.first_name}"

    # Email format check
    if erp_c.email and "@" not in erp_c.email:
        warnings.append(f"Email invalide ({erp_c.email}) pour {erp_label}")

    # Birth date range check
    if erp_c.birth_date:
        from datetime import date

        if isinstance(erp_c.birth_date, date):
            today = date.today()
            min_date = date(1900, 1, 1)
            if erp_c.birth_date > today:
                warnings.append(f"Date de naissance dans le futur ({erp_c.birth_date}) pour {erp_label}")
            elif erp_c.birth_date < min_date:
                warnings.append(f"Date de naissance avant 1900 ({erp_c.birth_date}) pour {erp_label}")

    # Social security number length check (French JSN: 13-15 digits)
    if erp_c.social_security_number:
        digits_only = "".join(c for c in erp_c.social_security_number if c.isdigit())
        if digits_only and (len(digits_only) < 13 or len(digits_only) > 15):
            warnings.append(
                f"Numero de securite sociale de longueur invalide "
                f"({len(digits_only)} chiffres) pour {erp_label}"
            )

    return warnings


# ---------------------------------------------------------------------------
# Customer field comparison and update
# ---------------------------------------------------------------------------


def _customer_has_changes(existing: Customer, erp_c: ERPCustomer) -> bool:
    """Compare ERP data with existing DB record to detect changes.

    Returns True if ANY field from the ERP would fill a currently-empty
    field on the existing customer, meaning an update is needed.
    Used during incremental sync to skip unchanged records.
    """
    # cosium_id missing = always needs update
    if erp_c.erp_id and not getattr(existing, "cosium_id", None):
        return True
    enriched_fields = (
        "phone", "address", "city", "postal_code", "social_security_number",
        "customer_number", "street_number", "street_name",
        "mobile_phone_country",
    )
    for field in enriched_fields:
        erp_val = getattr(erp_c, field, None)
        if erp_val and not getattr(existing, field, None):
            return True
    if erp_c.site_id is not None and not getattr(existing, "site_id", None):
        return True
    if erp_c.birth_date and not existing.birth_date:
        return True
    # Check if core identity fields differ (e.g. name correction in Cosium)
    if erp_c.first_name and existing.first_name != erp_c.first_name:
        return True
    if erp_c.last_name and existing.last_name != erp_c.last_name:
        return True
    if erp_c.email and (not existing.email or existing.email.lower() != erp_c.email.lower()):
        return True
    return False


def _update_customer_fields(existing: Customer, erp_c: ERPCustomer) -> bool:
    """Met a jour les champs vides d'un client existant."""
    changed = False
    # Always set cosium_id if missing
    if erp_c.erp_id and not getattr(existing, "cosium_id", None):
        existing.cosium_id = str(erp_c.erp_id)
        changed = True
    enriched_fields = (
        "phone", "address", "city", "postal_code", "social_security_number",
        "customer_number", "street_number", "street_name",
        "mobile_phone_country",
    )
    for field in enriched_fields:
        erp_val = getattr(erp_c, field, None)
        if erp_val and not getattr(existing, field, None):
            setattr(existing, field, erp_val)
            changed = True
    if erp_c.site_id is not None and not getattr(existing, "site_id", None):
        existing.site_id = erp_c.site_id
        changed = True
    if erp_c.birth_date and not existing.birth_date:
        existing.birth_date = erp_c.birth_date
        changed = True
    return changed


def _create_customer_from_erp(tenant_id: int, erp_c: ERPCustomer) -> Customer:
    """Cree un nouveau client a partir des donnees ERP.

    Valide les donnees et logue des warnings pour les champs invalides.
    Les donnees sont stockees telles quelles (ERP = source de verite).
    """
    warnings = _validate_erp_customer_data(erp_c)
    for w in warnings:
        logger.warning("erp_customer_data_quality", tenant_id=tenant_id, warning=w)

    return Customer(
        tenant_id=tenant_id,
        cosium_id=str(erp_c.erp_id) if erp_c.erp_id else None,
        first_name=erp_c.first_name,
        last_name=erp_c.last_name,
        phone=_normalize_phone(erp_c.phone),
        email=erp_c.email,
        address=erp_c.address,
        city=erp_c.city,
        postal_code=erp_c.postal_code,
        social_security_number=erp_c.social_security_number,
        birth_date=erp_c.birth_date,
        customer_number=erp_c.customer_number,
        street_number=erp_c.street_number,
        street_name=erp_c.street_name,
        mobile_phone_country=erp_c.mobile_phone_country,
        site_id=erp_c.site_id,
    )
