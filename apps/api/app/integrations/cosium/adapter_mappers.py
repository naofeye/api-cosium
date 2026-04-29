"""Secondary Cosium -> OptiFlow mappers.

Extracted from adapter.py to keep files under 300 lines.
Contains mappers for: advantages, fidelity cards, sponsorships,
notes, after-sales services, optical frames/lenses, spectacle files,
and invoiced items.

AUCUNE ecriture vers Cosium — lecture seule, mapping unidirectionnel.
"""


def _extract_id_from_href(href: str, segment: str) -> int | None:
    """Extrait un ID numerique d'une URL HAL .../segment/{id}."""
    if not href or segment not in href:
        return None
    try:
        return int(href.rsplit(segment, 1)[-1].split("?")[0].split("/")[0])
    except (ValueError, IndexError):
        return None


def cosium_advantage_to_optiflow(raw: dict) -> dict:
    """Normalise un avantage commercial Cosium.

    Format Cosium : name, from (ISO date), to (ISO date), links (rel/href).
    """
    links = raw.get("links", []) or []
    self_href = ""
    if isinstance(links, list):
        for link in links:
            if isinstance(link, dict) and link.get("rel") == "self":
                self_href = link.get("href", "")
                break
    advantage_id: int | None = None
    if "/advantages/" in self_href:
        try:
            advantage_id = int(self_href.rsplit("/advantages/", 1)[-1].split("?")[0].split("/")[0])
        except (ValueError, IndexError):
            advantage_id = None
    return {
        "cosium_id": advantage_id,
        "name": raw.get("name"),
        "description": raw.get("description"),
        "valid_from": raw.get("from"),
        "valid_to": raw.get("to"),
    }


def cosium_fidelity_card_to_optiflow(raw: dict) -> dict:
    """Normalise une carte de fidelite Cosium."""
    links = raw.get("_links", {}) or {}
    self_href = links.get("self", {}).get("href", "") if isinstance(links.get("self"), dict) else ""
    return {
        "cosium_id": _extract_id_from_href(self_href, "/customer-fidelity-cards/"),
        "card_number": raw.get("cardNumber"),
        "amount": raw.get("amount"),
        "remaining_amount": raw.get("remainingAmount"),
        "remaining_consumable_amount": raw.get("remainingConsumableAmount"),
        "creation_date": raw.get("creationDateTime") or raw.get("creationDate"),
        "expiration_date": raw.get("expirationDate"),
    }


def cosium_sponsorship_to_optiflow(raw: dict) -> dict:
    """Normalise un parrainage Cosium."""
    links = raw.get("_links", {}) or {}
    self_href = links.get("self", {}).get("href", "") if isinstance(links.get("self"), dict) else ""
    return {
        "cosium_id": _extract_id_from_href(self_href, "/customer-sponsorships/"),
        "sponsored_first_name": raw.get("sponsoredPartyFirstName"),
        "sponsored_last_name": raw.get("sponsoredPartyLastName"),
        "amount": raw.get("amount"),
        "remaining_amount": raw.get("remainingAmount"),
        "creation_date": raw.get("creationDateTime") or raw.get("creationDate"),
        "consumed": bool(raw.get("consumed", False)),
    }


def cosium_note_to_optiflow(raw: dict) -> dict:
    """Normalise une note CRM Cosium.

    Champs Cosium : message, creationDate, customerId, appearance.{value,label}, status.{value,label}.
    """
    links = raw.get("_links", {}) or {}
    self_href = links.get("self", {}).get("href", "") if isinstance(links.get("self"), dict) else ""
    appearance = raw.get("appearance", {}) or {}
    status = raw.get("status", {}) or {}
    return {
        "cosium_id": _extract_id_from_href(self_href, "/notes/"),
        "message": raw.get("message", ""),
        "creation_date": raw.get("creationDate"),
        "modification_date": raw.get("modificationDate"),
        "customer_id": raw.get("customerId"),
        "customer_number": raw.get("customerNumber"),
        "author": raw.get("author") or raw.get("authorName"),
        "appearance_value": appearance.get("value") if isinstance(appearance, dict) else None,
        "appearance_label": appearance.get("label") if isinstance(appearance, dict) else None,
        "status_value": status.get("value") if isinstance(status, dict) else None,
        "status_label": status.get("label") if isinstance(status, dict) else None,
    }


def cosium_after_sales_to_optiflow(raw: dict) -> dict:
    """Normalise un dossier SAV Cosium.

    Mappe les champs metier cles : statut, dates, produit, client, reparateur.
    """
    links = raw.get("_links", {}) or {}
    self_href = links.get("self", {}).get("href", "") if isinstance(links.get("self"), dict) else ""
    sav_id = _extract_id_from_href(self_href, "/after-sales-services/")
    return {
        "cosium_id": sav_id,
        "status": raw.get("status"),
        "resolution_status": raw.get("resolutionStatus"),
        "creation_date": raw.get("creationDate"),
        "processing_date": raw.get("processingDate"),
        "end_date": raw.get("endDate"),
        "description": raw.get("description"),
        "type": raw.get("type"),
        "customer_number": raw.get("customerNumber"),
        "invoice_number": raw.get("invoiceNumber"),
        "invoice_date": raw.get("invoiceDate"),
        "item_serial_number": raw.get("itemSerialNumber"),
        "product_code": raw.get("productCode"),
        "product_ean": raw.get("productEANCode"),
        "product_model": raw.get("productModel"),
        "product_color": raw.get("productColorLabel"),
        "repairer_name": raw.get("repairerName"),
        "site_name": raw.get("siteName"),
    }


def cosium_optical_frame_to_optiflow(raw: dict) -> dict:
    """Normalise une monture du catalogue Cosium."""
    links = raw.get("_links", {}) or {}
    self_href = links.get("self", {}).get("href", "") if isinstance(links.get("self"), dict) else ""
    return {
        "cosium_id": _extract_id_from_href(self_href, "/optical-frames/"),
        "brand": raw.get("brand"),
        "model": raw.get("model"),
        "color": raw.get("color"),
        "material": raw.get("material"),
        "style": raw.get("style"),
        "size": raw.get("size"),
        "nose_width": raw.get("noseWidth"),
        "arm_size": raw.get("armSize"),
        "price": raw.get("price"),
    }


def cosium_optical_lens_to_optiflow(raw: dict) -> dict:
    """Normalise un verre du catalogue Cosium."""
    links = raw.get("_links", {}) or {}
    self_href = links.get("self", {}).get("href", "") if isinstance(links.get("self"), dict) else ""
    return {
        "cosium_id": _extract_id_from_href(self_href, "/optical-lenses/"),
        "brand": raw.get("brand"),
        "model": raw.get("model"),
        "price": raw.get("price"),
        "material": raw.get("material"),
        "index": raw.get("index"),
        "treatment": raw.get("treatment"),
        "tint": raw.get("tint"),
        "photochromic": raw.get("photochromic"),
        "has_options": "available-options" in links,
    }


def cosium_spectacle_file_to_optiflow(raw: dict) -> dict:
    """Normalise un dossier lunettes Cosium (spectacles-files/{id}).

    Extrait l'ID du _links.self.href et retourne les metadonnees utiles.
    """
    links = raw.get("_links", {}) or {}
    self_href = links.get("self", {}).get("href", "") if isinstance(links.get("self"), dict) else ""
    file_id: int | None = None
    if "/spectacles-files/" in self_href:
        try:
            file_id = int(self_href.rsplit("/spectacles-files/", 1)[-1].split("?")[0].split("/")[0])
        except (ValueError, IndexError):
            file_id = None
    return {
        "cosium_id": file_id,
        "has_diopters": "diopters" in links,
        "has_selection": "spectacles-selection" in links,
        "has_doctor_address": "doctor-address" in links,
        "creation_date": raw.get("creationDate") or raw.get("date"),
    }


def cosium_invoiced_item_to_optiflow(raw: dict) -> dict:
    """Mappe un `/invoiced-items` Cosium vers la shape CosiumInvoicedItem."""
    try:
        cid = int(raw.get("id") or raw.get("invoicedItemId") or 0)
    except (TypeError, ValueError):
        return {}
    invoice_raw = raw.get("invoiceId")
    if invoice_raw is None and isinstance(raw.get("invoice"), dict):
        invoice_raw = raw["invoice"].get("id")
    try:
        invoice_cosium_id = int(invoice_raw) if invoice_raw else 0
    except (TypeError, ValueError):
        invoice_cosium_id = 0
    # Champs Cosium officiels (cf docs/cosium/Invoiced Items API.pdf) :
    # - unitPriceIncludingTaxes (TTC)
    # - totalPriceIncludingTaxes (TTC)
    # - unitPriceExcludingTaxes (HT)
    # - vatPercentage, discount, discountType, rank, productCode
    # Fallbacks legacy gardes pour compat avec d'eventuels seeds tests.
    quantity = int(raw.get("quantity") or 1)
    unit_ti = float(
        raw.get("unitPriceIncludingTaxes")
        or raw.get("unitPriceTI")
        or raw.get("unitPrice")
        or 0
    )
    total_ti = float(
        raw.get("totalPriceIncludingTaxes")
        or raw.get("totalTI")
        or raw.get("totalPrice")
        or 0
    )
    unit_te = float(raw.get("unitPriceExcludingTaxes") or 0)
    # totalPriceExcludingTaxes pas toujours present : fallback unit_te * qty
    total_te_raw = raw.get("totalPriceExcludingTaxes")
    total_te = float(total_te_raw) if total_te_raw is not None else round(unit_te * quantity, 2)
    vat_pct = float(raw.get("vatPercentage") or 0)
    discount = float(raw.get("discount") or 0)
    discount_type = raw.get("discountType")
    rank_raw = raw.get("rank")
    rank = int(rank_raw) if isinstance(rank_raw, int | float) else None
    return {
        "cosium_id": cid,
        "invoice_cosium_id": invoice_cosium_id,
        "product_cosium_id": (
            str(raw.get("productCode") or raw.get("productId") or "") or None
        ),
        "product_label": raw.get("label") or raw.get("productLabel") or "",
        "product_family": raw.get("productFamily") or raw.get("familyType") or "",
        "quantity": quantity,
        "unit_price_ti": unit_ti,
        "total_ti": total_ti,
        "unit_price_te": unit_te,
        "total_te": total_te,
        "vat_percentage": vat_pct,
        "discount": discount,
        "discount_type": discount_type if isinstance(discount_type, str) else None,
        "rank": rank,
    }
