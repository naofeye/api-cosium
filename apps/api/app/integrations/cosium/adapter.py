"""
Adaptateur Cosium -> OptiFlow.

Mappe les donnees Cosium vers les schemas OptiFlow.
AUCUNE ecriture vers Cosium — lecture seule, mapping unidirectionnel.

Structure reelle des donnees Cosium (verifiee le 2026-04-05) :
- Client: firstName, lastName, email, mobilePhone, birthDate, socialSecurityNumber directement sur l'objet
- Facture: invoiceNumber, totalTI, outstandingBalance, customerName, type, invoiceDate
- Produit: label, sellingPriceTaxIncluded, code, eanCode
"""

from app.core.logging import get_logger

logger = get_logger("cosium_adapter")


def cosium_customer_to_optiflow(data: dict) -> dict:
    """Mappe un client Cosium vers un dict compatible ClientCreate."""
    if not data.get("lastName"):
        logger.warning("cosium_customer_missing_field", field="lastName", cosium_id=data.get("id"))
    if not data.get("firstName"):
        logger.warning("cosium_customer_missing_field", field="firstName", cosium_id=data.get("id"))

    # Structure reelle : les champs sont directement sur l'objet
    # email et mobilePhone sont au niveau racine
    # contact et address sont des sous-ressources (liens HAL)
    # Fallback vers _embedded.contact si present (ancien format)
    contact = data.get("_embedded", {}).get("contact", {})
    address = data.get("_embedded", {}).get("address", {})

    # Build full address string from components if available
    street_number = address.get("streetNumber") or address.get("number")
    street_name_val = address.get("streetName") or address.get("street")
    full_address = street_name_val or ""
    if street_number and street_name_val:
        full_address = f"{street_number} {street_name_val}"

    # Mobile phone country from contact sub-resource
    mobile_country = contact.get("mobilePhoneNumberCountry") or contact.get("e164MobilePhoneNumberCountry")

    # Site ID: direct field or from _links
    site_id = data.get("siteId")
    if site_id is None:
        site_href = data.get("_links", {}).get("site", {}).get("href", "")
        if "/sites/" in site_href:
            try:
                site_id = int(site_href.rsplit("/sites/", 1)[-1].split("?")[0])
            except (ValueError, IndexError):
                pass

    return {
        "first_name": data.get("firstName") or "",
        "last_name": data.get("lastName") or "",
        "birth_date": data.get("birthDate"),
        "phone": data.get("mobilePhone") or contact.get("mobilePhoneNumber") or contact.get("phoneNumber"),
        "email": data.get("email") or contact.get("email"),
        "address": full_address,
        "street_number": street_number,
        "street_name": street_name_val,
        "city": address.get("town") or address.get("city"),
        "postal_code": address.get("postCode") or address.get("zipCode"),
        "social_security_number": data.get("socialSecurityNumber"),
        "cosium_id": str(data.get("id", "")),
        "customer_number": data.get("customerNumber"),
        "site_id": site_id,
        "mobile_phone_country": mobile_country,
    }


def cosium_invoice_to_optiflow(data: dict) -> dict:
    """Mappe une facture Cosium vers un dict pour import."""
    # Structure reelle : invoiceNumber (pas number), totalTI (pas totalAmountTaxIncluded)
    numero = data.get("invoiceNumber") or data.get("number", "")
    if not numero:
        logger.warning("cosium_invoice_missing_field", field="invoiceNumber", cosium_id=data.get("id"))

    # Extract customer_cosium_id: direct field first, then HAL link fallback
    customer_cosium_id = str(data.get("customerId", ""))
    if not customer_cosium_id:
        cust_href = data.get("_links", {}).get("customer", {}).get("href", "")
        if "/customers/" in cust_href:
            try:
                customer_cosium_id = str(int(cust_href.rsplit("/customers/", 1)[-1].split("?")[0]))
            except (ValueError, IndexError):
                pass

    return {
        "cosium_id": str(data.get("id", "")),
        "type": data.get("type", "INVOICE"),
        "numero": numero,
        "date_emission": data.get("invoiceDate") or data.get("date"),
        "montant_ttc": data.get("totalTI") or data.get("totalAmountTaxIncluded", 0),
        "montant_ht": data.get("totalAmountTaxExcluded", 0),
        "tva": data.get("totalTaxAmount", 0),
        "settled": data.get("outstandingBalance", 0) == 0
        if data.get("outstandingBalance") is not None
        else data.get("settled", False),
        "customer_name": data.get("customerName", ""),
        "customer_cosium_id": customer_cosium_id,
        "outstanding_balance": data.get("outstandingBalance", 0),
        "share_social_security": data.get("shareSocialSecurity", 0),
        "share_private_insurance": data.get("sharePrivateInsurance", 0),
    }


def cosium_product_to_optiflow(data: dict) -> dict:
    """Mappe un produit Cosium vers un dict pour import.

    Product IDs are NOT at top-level; they must be extracted from _links.self.href.
    Field mapping: productCode (not code), barcode, eanCode, gtinCode, familyType.
    sellingPriceTaxIncluded may be absent on some products.
    """
    # Extract ID from HAL self link: .../products/{id}
    cosium_id = str(data.get("id", ""))
    if not cosium_id:
        self_href = data.get("_links", {}).get("self", {}).get("href", "")
        if "/products/" in self_href:
            cosium_id = self_href.rsplit("/products/", 1)[-1].split("?")[0]

    return {
        "cosium_id": cosium_id,
        "code": data.get("productCode", data.get("code", data.get("barcode", ""))),
        "ean": data.get("eanCode", ""),
        "gtin": data.get("gtinCode", ""),
        "label": data.get("label", data.get("designation", "")),
        "family": data.get("familyType", ""),
        "price": data.get("sellingPriceTaxIncluded", 0) or 0,
    }


def cosium_payment_to_optiflow(data: dict) -> dict:
    """Mappe un paiement de facture Cosium vers un dict pour import.

    Structure Cosium: {id, paymentTypeId, amount, originalAmount, type,
    dueDate, issuerName, bank, siteName, comment, paymentNumber,
    accountingDocumentNumber}
    """
    cosium_id = data.get("id")
    if not cosium_id:
        logger.warning("cosium_payment_missing_id", data_keys=list(data.keys()))

    # Extract customer link from _links.customer.href
    customer_cosium_id = None
    cust_href = data.get("_links", {}).get("customer", {}).get("href", "")
    if "/customers/" in cust_href:
        try:
            customer_cosium_id = str(int(cust_href.rsplit("/customers/", 1)[-1].split("?")[0]))
        except (ValueError, IndexError):
            pass

    # Extract invoice link from _links or accountingDocumentNumber
    invoice_cosium_id = None
    acc_doc_num = data.get("accountingDocumentNumber", "")
    if acc_doc_num and str(acc_doc_num).strip().isdigit():
        invoice_cosium_id = int(acc_doc_num)
    if not invoice_cosium_id:
        acc_href = data.get("_links", {}).get("accounting-document", {}).get("href", "")
        if "/invoices/" in acc_href:
            try:
                invoice_cosium_id = int(acc_href.rsplit("/invoices/", 1)[-1].split("?")[0])
            except (ValueError, IndexError):
                pass

    return {
        "cosium_id": cosium_id,
        "payment_type_id": data.get("paymentTypeId"),
        "amount": data.get("amount", 0) or 0,
        "original_amount": data.get("originalAmount"),
        "type": data.get("type", ""),
        "due_date": data.get("dueDate"),
        "issuer_name": data.get("issuerName", ""),
        "bank": data.get("bank", ""),
        "site_name": data.get("siteName", ""),
        "comment": data.get("comment"),
        "payment_number": data.get("paymentNumber", ""),
        "invoice_cosium_id": invoice_cosium_id,
        "customer_cosium_id": customer_cosium_id,
    }


def cosium_tpp_to_optiflow(data: dict) -> dict:
    """Mappe un tiers payant Cosium vers un dict pour import.

    Structure Cosium: {additionalHealthCareAmount, additionalHealthCareThirdPartyPayment,
    socialSecurityAmount, socialSecurityThirdPartyPayment}
    + _links.accounting-document.href pour l'ID facture.
    """
    cosium_id = data.get("id")
    if not cosium_id:
        # Try extracting from self link
        self_href = data.get("_links", {}).get("self", {}).get("href", "")
        if "/third-party-payments/" in self_href:
            try:
                cosium_id = int(self_href.rsplit("/third-party-payments/", 1)[-1].split("?")[0])
            except (ValueError, IndexError):
                pass

    # Extract invoice ID from _links.accounting-document
    invoice_cosium_id = None
    acc_href = data.get("_links", {}).get("accounting-document", {}).get("href", "")
    if "/invoices/" in acc_href:
        try:
            invoice_cosium_id = int(acc_href.rsplit("/invoices/", 1)[-1].split("?")[0])
        except (ValueError, IndexError):
            pass

    return {
        "cosium_id": cosium_id,
        "social_security_amount": data.get("socialSecurityAmount", 0) or 0,
        "social_security_tpp": bool(data.get("socialSecurityThirdPartyPayment", False)),
        "additional_health_care_amount": data.get("additionalHealthCareAmount", 0) or 0,
        "additional_health_care_tpp": bool(data.get("additionalHealthCareThirdPartyPayment", False)),
        "invoice_cosium_id": invoice_cosium_id,
    }


def cosium_prescription_to_optiflow(data: dict) -> dict:
    """Mappe une ordonnance optique Cosium vers un dict pour import.

    Structure Cosium: {diopters: [{sphere100Left, sphere100Right, cylinder100Left,
    cylinder100Right, axisLeft, axisRight, addition100Left, addition100Right,
    visionType}], prescriptionDate, fileDate, selectedSpectacles: [...]}

    Note: diopter values are in hundredths — divide by 100 for actual value.
    E.g. sphere100Left=-50 means -0.50 diopters.
    """
    cosium_id = data.get("id")
    if not cosium_id:
        self_href = data.get("_links", {}).get("self", {}).get("href", "")
        if "/optical-prescriptions/" in self_href:
            try:
                cosium_id = int(self_href.rsplit("/optical-prescriptions/", 1)[-1].split("?")[0])
            except (ValueError, IndexError):
                pass

    # Extract customer ID from _links
    customer_cosium_id = None
    cust_href = data.get("_links", {}).get("customer", {}).get("href", "")
    if "/customers/" in cust_href:
        try:
            customer_cosium_id = int(cust_href.rsplit("/customers/", 1)[-1].split("?")[0])
        except (ValueError, IndexError):
            pass

    # Parse first diopter entry (distance vision by default)
    diopters = data.get("diopters", [])
    sphere_right = None
    cylinder_right = None
    axis_right = None
    addition_right = None
    sphere_left = None
    cylinder_left = None
    axis_left = None
    addition_left = None

    if diopters and isinstance(diopters, list) and len(diopters) > 0:
        d = diopters[0]
        # Diopter values in hundredths: divide by 100
        sphere_right = _hundredths_to_diopter(d.get("sphere100Right"))
        cylinder_right = _hundredths_to_diopter(d.get("cylinder100Right"))
        axis_right = d.get("axisRight")  # axis is in degrees, not hundredths
        addition_right = _hundredths_to_diopter(d.get("addition100Right"))
        sphere_left = _hundredths_to_diopter(d.get("sphere100Left"))
        cylinder_left = _hundredths_to_diopter(d.get("cylinder100Left"))
        axis_left = d.get("axisLeft")
        addition_left = _hundredths_to_diopter(d.get("addition100Left"))

    # Selected spectacles as JSON string
    import json

    spectacles = data.get("selectedSpectacles", [])
    spectacles_json = json.dumps(spectacles) if spectacles else None

    # Prescriber name from _embedded or _links
    prescriber_name = None
    prescriber = data.get("_embedded", {}).get("prescriber", {})
    if prescriber:
        prescriber_name = f"{prescriber.get('firstName', '')} {prescriber.get('lastName', '')}".strip() or None

    return {
        "cosium_id": cosium_id,
        "prescription_date": data.get("prescriptionDate"),
        "file_date": data.get("fileDate"),
        "customer_cosium_id": customer_cosium_id,
        "sphere_right": sphere_right,
        "cylinder_right": cylinder_right,
        "axis_right": axis_right,
        "addition_right": addition_right,
        "sphere_left": sphere_left,
        "cylinder_left": cylinder_left,
        "axis_left": axis_left,
        "addition_left": addition_left,
        "spectacles_json": spectacles_json,
        "prescriber_name": prescriber_name,
    }


def _hundredths_to_diopter(value: int | float | None) -> float | None:
    """Convert a Cosium hundredths value to actual diopter.

    E.g. -50 -> -0.50, 225 -> 2.25
    """
    if value is None:
        return None
    return round(float(value) / 100.0, 2)


def cosium_diopter_to_optiflow(raw: dict) -> dict:
    """Normalise une entree de dioptrie Cosium (spectacles-files/{id}/diopters).

    Cosium stocke les valeurs en centiemes (sphere100Right=-50 -> -0.50 dioptrie).
    Retourne un dict avec les valeurs OD (right) et OG (left) en format standard.
    """
    return {
        "sphere_right": _hundredths_to_diopter(raw.get("sphere100Right")),
        "cylinder_right": _hundredths_to_diopter(raw.get("cylinder100Right")),
        "axis_right": raw.get("axisRight"),
        "addition_right": _hundredths_to_diopter(raw.get("addition100Right")),
        "prism_right": _hundredths_to_diopter(raw.get("prism100Right")),
        "sphere_left": _hundredths_to_diopter(raw.get("sphere100Left")),
        "cylinder_left": _hundredths_to_diopter(raw.get("cylinder100Left")),
        "axis_left": raw.get("axisLeft"),
        "addition_left": _hundredths_to_diopter(raw.get("addition100Left")),
        "prism_left": _hundredths_to_diopter(raw.get("prism100Left")),
        "vision_type": raw.get("visionType") or raw.get("type"),
    }


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
