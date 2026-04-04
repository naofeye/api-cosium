"""
CosiumConnector — Implementation de ERPConnector pour Cosium.

REGLES DE SECURITE ABSOLUES :
- LECTURE SEULE : seul POST autorise = /authenticate/basic
- Toutes les lectures via GET uniquement
- INTERDIT : put, post (sauf auth), delete, patch
"""

from app.core.logging import get_logger
from app.integrations.cosium.adapter import (
    cosium_customer_to_optiflow,
    cosium_invoice_to_optiflow,
    cosium_product_to_optiflow,
)
from app.integrations.cosium.client import CosiumClient
from app.integrations.erp_connector import ERPConnector
from app.integrations.erp_models import (
    ERPCustomer,
    ERPInvoice,
    ERPPaymentType,
    ERPProduct,
    ERPStock,
)

logger = get_logger("cosium_connector")


class CosiumConnector(ERPConnector):
    """Connecteur Cosium implementant l'interface ERPConnector.

    Encapsule le CosiumClient existant et mappe les reponses HAL
    vers les modeles generiques ERP.
    """

    def __init__(self) -> None:
        self._client = CosiumClient()

    @property
    def erp_type(self) -> str:
        return "cosium"

    @property
    def is_authenticated(self) -> bool:
        return bool(self._client.token)

    def authenticate(self, base_url: str, tenant: str, login: str, password: str) -> str:
        self._client.base_url = base_url
        token = self._client.authenticate(tenant=tenant, login=login, password=password)
        logger.info("cosium_connector_authenticated", tenant=tenant)
        return token

    def get_customers(self, page: int = 0, page_size: int = 100) -> list[ERPCustomer]:
        items = self._client.get_paginated("/customers", page_size=page_size, max_pages=10)
        customers: list[ERPCustomer] = []
        for raw in items:
            mapped = cosium_customer_to_optiflow(raw)
            if not mapped.get("last_name"):
                continue
            customers.append(
                ERPCustomer(
                    erp_id=mapped.get("cosium_id", ""),
                    first_name=mapped.get("first_name", ""),
                    last_name=mapped.get("last_name", ""),
                    birth_date=mapped.get("birth_date"),
                    phone=mapped.get("phone"),
                    email=mapped.get("email"),
                    address=mapped.get("address"),
                    city=mapped.get("city"),
                    postal_code=mapped.get("postal_code"),
                    social_security_number=mapped.get("social_security_number"),
                )
            )
        return customers

    def get_invoices(self, page: int = 0, page_size: int = 100) -> list[ERPInvoice]:
        items = self._client.get_paginated("/invoices", page_size=page_size, max_pages=10)
        invoices: list[ERPInvoice] = []
        for raw in items:
            mapped = cosium_invoice_to_optiflow(raw)
            invoices.append(
                ERPInvoice(
                    erp_id=mapped.get("cosium_id", ""),
                    type=mapped.get("type", "INVOICE"),
                    number=mapped.get("numero", ""),
                    date=mapped.get("date_emission"),
                    total_ttc=mapped.get("montant_ttc", 0),
                    total_ht=mapped.get("montant_ht", 0),
                    total_tax=mapped.get("tva", 0),
                    settled=mapped.get("settled", False),
                    customer_erp_id=mapped.get("customer_cosium_id", ""),
                )
            )
        return invoices

    def get_invoiced_items(self, invoice_erp_id: str) -> list[dict]:
        data = self._client.get("/invoiced-items", params={"invoiceId": invoice_erp_id})
        embedded = data.get("_embedded", data)
        items = embedded.get("invoicedItems", [])
        return items if isinstance(items, list) else [items]

    def get_products(self, page: int = 0, page_size: int = 100) -> list[ERPProduct]:
        items = self._client.get_paginated("/products", page_size=page_size, max_pages=10)
        products: list[ERPProduct] = []
        for raw in items:
            mapped = cosium_product_to_optiflow(raw)
            products.append(
                ERPProduct(
                    erp_id=mapped.get("cosium_id", ""),
                    code=mapped.get("code", ""),
                    ean=mapped.get("ean", ""),
                    gtin=mapped.get("gtin", ""),
                    label=mapped.get("label", ""),
                    family=mapped.get("family", ""),
                    price=mapped.get("price", 0),
                )
            )
        return products

    def get_product_stock(self, product_erp_id: str) -> list[ERPStock]:
        data = self._client.get(f"/products/{product_erp_id}/stock")
        stocks: list[ERPStock] = []
        embedded = data.get("_embedded", data)
        stock_list = embedded.get("stocks", embedded.get("items", []))
        if isinstance(stock_list, list):
            for s in stock_list:
                stocks.append(
                    ERPStock(
                        product_erp_id=product_erp_id,
                        site=s.get("site", s.get("siteName", "")),
                        quantity=s.get("quantity", s.get("availableQuantity", 0)),
                    )
                )
        return stocks

    def get_payment_types(self) -> list[ERPPaymentType]:
        data = self._client.get("/payment-types")
        embedded = data.get("_embedded", data)
        types_list = embedded.get("paymentTypes", [])
        payment_types: list[ERPPaymentType] = []
        if isinstance(types_list, list):
            for pt in types_list:
                payment_types.append(
                    ERPPaymentType(
                        erp_id=str(pt.get("id", "")),
                        label=pt.get("label", pt.get("name", "")),
                        code=pt.get("code", ""),
                    )
                )
        return payment_types
