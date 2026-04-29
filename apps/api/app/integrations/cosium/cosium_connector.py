"""
CosiumConnector — Implementation de ERPConnector pour Cosium.

REGLES DE SECURITE ABSOLUES :
- LECTURE SEULE : seul POST autorise = /authenticate/basic
- Toutes les lectures via GET uniquement
- INTERDIT : put, post (sauf auth), delete, patch
"""

from app.core.logging import get_logger
from app.integrations.cosium.adapter import (
    cosium_invoice_to_optiflow,
    cosium_payment_to_optiflow,
    cosium_prescription_to_optiflow,
    cosium_product_to_optiflow,
    cosium_tpp_to_optiflow,
)
from app.integrations.cosium.client import CosiumClient
from app.integrations.cosium.cosium_connector_extras import CosiumConnectorExtrasMixin
from app.integrations.erp_connector import ERPConnector
from app.integrations.erp_models import (
    ERPCustomer,
    ERPInvoice,
    ERPPaymentType,
    ERPProduct,
    ERPStock,
)

logger = get_logger("cosium_connector")


class CosiumConnector(CosiumConnectorExtrasMixin, ERPConnector):
    """Connecteur Cosium implementant l'interface ERPConnector.

    Encapsule le CosiumClient existant et mappe les reponses HAL
    vers les modeles generiques ERP.
    """

    def __init__(self, client: CosiumClient | None = None) -> None:
        self._client = client or CosiumClient()

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

    def get_customers(self, page: int = 0, page_size: int = 50) -> list[ERPCustomer]:
        """Delegation vers customer_fetcher pour la strategie de parcours exhaustif."""
        from app.integrations.cosium.customer_fetcher import fetch_all_customers

        return fetch_all_customers(self._client)

    def get_invoices(self, page: int = 0, page_size: int = 50) -> list[ERPInvoice]:
        items = self._client.get_paginated("/invoices", page_size=page_size, max_pages=600)
        return self._map_invoices(items)

    def get_invoices_by_date_range(self, date_from: str, date_to: str, page_size: int = 50) -> list[ERPInvoice]:
        """Fetch invoices within a date range (ISO format strings).

        Used for month-by-month pagination to bypass the 50-item offset limit.
        """
        items = self._client.get_paginated(
            "/invoices",
            params={"invoiceDateFrom": date_from, "invoiceDateTo": date_to},
            page_size=page_size,
            max_pages=100,
        )
        return self._map_invoices(items)

    def _map_invoices(self, items: list[dict]) -> list[ERPInvoice]:
        """Map raw Cosium invoice dicts to ERPInvoice models."""
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
                    customer_name=mapped.get("customer_name", ""),
                    outstanding_balance=mapped.get("outstanding_balance", 0),
                    share_social_security=mapped.get("share_social_security", 0),
                    share_private_insurance=mapped.get("share_private_insurance", 0),
                    archived=raw.get("archived", False),
                    site_id=raw.get("siteId"),
                )
            )
        return invoices

    def get_invoiced_items(self, invoice_erp_id: str) -> list[dict]:
        data = self._client.get("/invoiced-items", params={"invoiceId": invoice_erp_id})
        embedded = data.get("_embedded", data)
        items = embedded.get("invoicedItems", [])
        return items if isinstance(items, list) else [items]

    def get_products(self, page: int = 0, page_size: int = 50) -> list[ERPProduct]:
        # Catalog has 398k+ products. Limit to 1 page for sample sync.
        items = self._client.get_paginated("/products", page_size=page_size, max_pages=1)
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

    def get_product_latent_sales(
        self, product_erp_id: str, max_age_days: int = 10
    ) -> int:
        """GET /products/{id}/latent-sales : quantite dans des devis non
        encore factures (ventes potentielles).

        Documente officiellement par Cosium (Products API.pdf). Retourne 0 si
        l'endpoint n'est pas disponible ou si la reponse est malformee.
        """
        data = self._client.get(
            f"/products/{product_erp_id}/latent-sales",
            params={"quotations_max_age_in_days": max_age_days},
        )
        if isinstance(data, dict):
            qty = data.get("quantity", 0)
            try:
                return int(qty)
            except (TypeError, ValueError):
                return 0
        return 0

    def get_invoice_payments(self, page: int = 0, page_size: int = 50, max_pages: int = 600) -> list[dict]:
        """GET /invoice-payments — paiements de factures (lecture seule)."""
        items = self._client.get_paginated("/invoice-payments", page_size=page_size, max_pages=max_pages)
        result: list[dict] = []
        for raw in items:
            mapped = cosium_payment_to_optiflow(raw)
            if mapped.get("cosium_id"):
                result.append(mapped)
        logger.info("cosium_invoice_payments_fetched", total=len(result))
        return result

    def list_invoiced_items(self, page_size: int = 100, max_pages: int = 500) -> list[dict]:
        """GET /invoiced-items (liste paginee) — lignes de factures. Lecture seule."""
        from app.integrations.cosium.adapter import cosium_invoiced_item_to_optiflow

        items = self._client.get_paginated("/invoiced-items", page_size=page_size, max_pages=max_pages)
        result = [m for m in (cosium_invoiced_item_to_optiflow(r) for r in items) if m.get("cosium_id")]
        logger.info("cosium_invoiced_items_fetched", total=len(result))
        return result

    def get_third_party_payments(self, page: int = 0, page_size: int = 50) -> list[dict]:
        """GET /third-party-payments — tiers payant secu + mutuelle (lecture seule)."""
        # TPP endpoint is very slow on Cosium servers — limit to avoid timeouts
        items = self._client.get_paginated("/third-party-payments", page_size=page_size, max_pages=5)
        result: list[dict] = []
        for raw in items:
            mapped = cosium_tpp_to_optiflow(raw)
            if mapped.get("cosium_id"):
                result.append(mapped)
        logger.info("cosium_tpp_fetched", total=len(result))
        return result

    def get_optical_prescriptions(self, page: int = 0, page_size: int = 50, max_pages: int = 600) -> list[dict]:
        """GET /optical-prescriptions — ordonnances optiques (lecture seule)."""
        items = self._client.get_paginated("/optical-prescriptions", page_size=page_size, max_pages=max_pages)
        result: list[dict] = []
        for raw in items:
            mapped = cosium_prescription_to_optiflow(raw)
            if mapped.get("cosium_id"):
                result.append(mapped)
        logger.info("cosium_prescriptions_fetched", total=len(result))
        return result

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
