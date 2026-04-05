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

    return {
        "first_name": data.get("firstName") or "",
        "last_name": data.get("lastName") or "",
        "birth_date": data.get("birthDate"),
        "phone": data.get("mobilePhone") or contact.get("mobilePhoneNumber") or contact.get("phoneNumber"),
        "email": data.get("email") or contact.get("email"),
        "address": address.get("streetName") or address.get("street"),
        "city": address.get("town") or address.get("city"),
        "postal_code": address.get("postCode") or address.get("zipCode"),
        "social_security_number": data.get("socialSecurityNumber"),
        "cosium_id": str(data.get("id", "")),
    }


def cosium_invoice_to_optiflow(data: dict) -> dict:
    """Mappe une facture Cosium vers un dict pour import."""
    # Structure reelle : invoiceNumber (pas number), totalTI (pas totalAmountTaxIncluded)
    numero = data.get("invoiceNumber") or data.get("number", "")
    if not numero:
        logger.warning("cosium_invoice_missing_field", field="invoiceNumber", cosium_id=data.get("id"))

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
        "customer_cosium_id": str(data.get("customerId", "")),
        "outstanding_balance": data.get("outstandingBalance", 0),
        "share_social_security": data.get("shareSocialSecurity", 0),
        "share_private_insurance": data.get("sharePrivateInsurance", 0),
    }


def cosium_product_to_optiflow(data: dict) -> dict:
    """Mappe un produit Cosium vers un dict pour import."""
    return {
        "cosium_id": str(data.get("id", "")),
        "code": data.get("code", ""),
        "ean": data.get("eanCode", ""),
        "gtin": data.get("gtinCode", ""),
        "label": data.get("label", data.get("designation", "")),
        "family": data.get("familyType", ""),
        "price": data.get("sellingPriceTaxIncluded", 0),
    }
