"""
Adaptateur Cosium -> OptiFlow.

Mappe les donnees HAL Cosium vers les schemas OptiFlow.
AUCUNE ecriture vers Cosium — lecture seule, mapping unidirectionnel.
"""

from app.core.logging import get_logger

logger = get_logger("cosium_adapter")


def cosium_customer_to_optiflow(data: dict) -> dict:
    """Mappe un client Cosium (HAL) vers un dict compatible ClientCreate."""
    if not data.get("lastName"):
        logger.warning("cosium_customer_missing_field", field="lastName", cosium_id=data.get("id"))
    if not data.get("firstName"):
        logger.warning("cosium_customer_missing_field", field="firstName", cosium_id=data.get("id"))

    contact = data.get("_embedded", {}).get("contact", data.get("contact", {}))
    address = data.get("_embedded", {}).get("address", data.get("address", {}))

    return {
        "first_name": data.get("firstName", ""),
        "last_name": data.get("lastName", ""),
        "birth_date": data.get("birthDate"),
        "phone": contact.get("mobilePhoneNumber") or contact.get("phoneNumber"),
        "email": contact.get("email"),
        "address": address.get("street"),
        "city": address.get("city"),
        "postal_code": address.get("zipCode"),
        "social_security_number": data.get("socialSecurityNumber"),
        "cosium_id": str(data.get("id", "")),
    }


def cosium_invoice_to_optiflow(data: dict) -> dict:
    """Mappe une facture Cosium vers un dict pour import."""
    if not data.get("number"):
        logger.warning("cosium_invoice_missing_field", field="number", cosium_id=data.get("id"))

    return {
        "cosium_id": str(data.get("id", "")),
        "type": data.get("type", "INVOICE"),
        "numero": data.get("number", ""),
        "date_emission": data.get("date"),
        "montant_ttc": data.get("totalAmountTaxIncluded", 0),
        "montant_ht": data.get("totalAmountTaxExcluded", 0),
        "tva": data.get("totalTaxAmount", 0),
        "settled": data.get("settled", False),
        "customer_cosium_id": str(data.get("customerId", "")),
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
