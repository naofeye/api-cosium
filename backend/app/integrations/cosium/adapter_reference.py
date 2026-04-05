"""Adapter for Cosium reference data — maps raw HAL responses to flat dicts.

LECTURE SEULE : ces fonctions ne font que transformer des donnees lues depuis Cosium.
"""

import re
from datetime import datetime


def _extract_id_from_href(item: dict) -> int | None:
    """Extract numeric ID from HAL _links.self.href.

    Example: "https://c1.cosium.biz/.../calendar-events/3" -> 3
    """
    try:
        href = item.get("_links", {}).get("self", {}).get("href", "")
        if href:
            last_segment = href.rstrip("/").rsplit("/", 1)[-1]
            if last_segment.isdigit():
                return int(last_segment)
    except (AttributeError, ValueError, IndexError):
        pass
    return None


def _extract_str_id_from_href(item: dict) -> str:
    """Extract string ID (e.g. UUID) from HAL _links.self.href."""
    try:
        href = item.get("_links", {}).get("self", {}).get("href", "")
        if href:
            return href.rstrip("/").rsplit("/", 1)[-1]
    except (AttributeError, IndexError):
        pass
    return ""


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string, handling Cosium formats."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        pass
    # Try epoch millis (some Cosium dates come as numbers)
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000.0)
    except (ValueError, TypeError, OSError):
        pass
    return None


def adapt_calendar_event(raw: dict) -> dict:
    """Map raw Cosium calendar event to flat dict for CosiumCalendarEvent model."""
    cosium_id = _extract_id_from_href(raw) or raw.get("id")
    return {
        "cosium_id": int(cosium_id) if cosium_id else 0,
        "start_date": _parse_datetime(raw.get("startDate")),
        "end_date": _parse_datetime(raw.get("endDate")),
        "subject": raw.get("subject", "") or "",
        "customer_fullname": raw.get("customerFullname", "") or "",
        "customer_number": str(raw.get("customerNumber", "") or ""),
        "category_name": raw.get("categoryName", "") or "",
        "category_color": raw.get("categoryColor", "") or "",
        "category_family": raw.get("categoryFamilyName", "") or "",
        "status": raw.get("status", "") or "",
        "canceled": bool(raw.get("canceled", False)),
        "missed": bool(raw.get("missed", False)),
        "customer_arrived": bool(raw.get("customerArrived", False)),
        "observation": raw.get("observation"),
        "site_name": raw.get("siteName"),
        "modification_date": _parse_datetime(raw.get("modificationDate")),
    }


def adapt_mutuelle(raw: dict) -> dict:
    """Map raw Cosium additional-health-care to flat dict for CosiumMutuelle model."""
    cosium_id = _extract_id_from_href(raw) or raw.get("id")
    return {
        "cosium_id": int(cosium_id) if cosium_id else 0,
        "name": raw.get("name", "") or "",
        "code": raw.get("code", "") or "",
        "label": raw.get("label", "") or "",
        "phone": raw.get("phoneNumber", "") or "",
        "email": raw.get("email", "") or "",
        "city": raw.get("city", "") or "",
        "hidden": bool(raw.get("hidden", False)),
        "opto_amc": bool(raw.get("optoAmc", False)),
        "coverage_request_phone": raw.get("coverageRequestPhone", "") or "",
        "coverage_request_email": raw.get("coverageRequestEmail", "") or "",
    }


def adapt_doctor(raw: dict) -> dict:
    """Map raw Cosium doctor to flat dict for CosiumDoctor model."""
    cosium_id = raw.get("cosiumId") or _extract_str_id_from_href(raw) or str(raw.get("id", ""))
    return {
        "cosium_id": str(cosium_id),
        "firstname": raw.get("firstname", "") or "",
        "lastname": raw.get("lastname", "") or "",
        "civility": raw.get("civility", "") or "",
        "email": raw.get("email"),
        "phone": raw.get("mobilePhoneNumber"),
        "rpps_number": raw.get("rppsNumber"),
        "specialty": raw.get("specialityName", "") or "",
        "optic_prescriber": bool(raw.get("opticPrescriber", False)),
        "audio_prescriber": bool(raw.get("audioPrescriber", False)),
        "hidden": bool(raw.get("hidden", False)),
    }


def adapt_brand(raw: dict) -> dict:
    """Map raw Cosium brand to flat dict for CosiumBrand model."""
    name = raw.get("name", "") or ""
    if not name:
        # Some brands only have name in _links
        href = raw.get("_links", {}).get("self", {}).get("href", "")
        if href:
            name = href.rstrip("/").rsplit("/", 1)[-1]
    return {"name": name}


def adapt_supplier(raw: dict) -> dict:
    """Map raw Cosium supplier to flat dict for CosiumSupplier model."""
    name = raw.get("name", "") or ""
    if not name:
        href = raw.get("_links", {}).get("self", {}).get("href", "")
        if href:
            name = href.rstrip("/").rsplit("/", 1)[-1]
    return {"name": name}


def adapt_tag(raw: dict) -> dict:
    """Map raw Cosium tag to flat dict for CosiumTag model."""
    cosium_id = _extract_id_from_href(raw) or raw.get("id")
    return {
        "cosium_id": int(cosium_id) if cosium_id else 0,
        "code": raw.get("code", "") or "",
        "description": raw.get("description", "") or "",
        "hidden": bool(raw.get("hidden", False)),
    }


def adapt_site(raw: dict) -> dict:
    """Map raw Cosium site to flat dict for CosiumSite model."""
    cosium_id = _extract_id_from_href(raw) or raw.get("id")
    return {
        "cosium_id": int(cosium_id) if cosium_id else 0,
        "name": raw.get("name", "") or "",
        "code": raw.get("code", "") or "",
        "long_label": raw.get("longLabel", "") or "",
        "address": raw.get("address", "") or "",
        "postcode": raw.get("postcode", "") or "",
        "city": raw.get("city", "") or "",
        "country": raw.get("country", "") or "",
        "phone": raw.get("phone", "") or "",
    }
