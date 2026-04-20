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


# Les adaptateurs prescription + diopter sont extraits dans adapter_prescription.py
# pour maintenir adapter.py sous la limite de 500 lignes.
from app.integrations.cosium.adapter_prescription import (  # noqa: E402
    _hundredths_to_diopter,
    cosium_diopter_to_optiflow,
    cosium_prescription_to_optiflow,
)

# Re-export pour retro-compat (imports existants `from adapter import cosium_prescription_to_optiflow`)
__all__ = [
    "cosium_prescription_to_optiflow",
    "cosium_diopter_to_optiflow",
    "_hundredths_to_diopter",
]


# Secondary mappers extracted to adapter_mappers.py for file size compliance.
# Re-exported here for backward compatibility.
from app.integrations.cosium.adapter_mappers import (  # noqa: E402, F401
    _extract_id_from_href,
    cosium_advantage_to_optiflow,
    cosium_after_sales_to_optiflow,
    cosium_fidelity_card_to_optiflow,
    cosium_invoiced_item_to_optiflow,
    cosium_note_to_optiflow,
    cosium_optical_frame_to_optiflow,
    cosium_optical_lens_to_optiflow,
    cosium_spectacle_file_to_optiflow,
    cosium_sponsorship_to_optiflow,
)
