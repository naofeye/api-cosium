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
    cosium_payment_to_optiflow,
    cosium_prescription_to_optiflow,
    cosium_product_to_optiflow,
    cosium_tpp_to_optiflow,
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

    def get_customers(self, page: int = 0, page_size: int = 50) -> list[ERPCustomer]:
        # Cosium API has a hard offset limit of ~50 items per listing.
        # Strategy: filter by loose_last_name letter-by-letter to bypass the limit,
        # then sweep non-alpha prefixes (digits, accents, special chars) to catch all.
        import string

        seen_ids: set[str] = set()
        items: list[dict] = []

        # First: fetch without filter (first 50 clients)
        batch = self._client.get_paginated("/customers", page_size=50, max_pages=1)
        for raw in batch:
            cid = str(raw.get("id", ""))
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                items.append(raw)

        # Then: filter by each letter A-Z
        for letter in string.ascii_uppercase:
            data = self._client.get("/customers", {"loose_last_name": letter, "page_number": 0, "page_size": 1})
            total = data.get("page", {}).get("totalElements", 0)
            if total == 0:
                continue

            if total <= 50:
                batch = self._client.get_paginated(
                    "/customers", params={"loose_last_name": letter}, page_size=50, max_pages=1
                )
            else:
                # Sub-filter with 2-char prefix for letters with > 50 results
                batch = []
                for second in string.ascii_uppercase:
                    sub = self._client.get_paginated(
                        "/customers", params={"loose_last_name": f"{letter}{second}"}, page_size=50, max_pages=1
                    )
                    batch.extend(sub)

            for raw in batch:
                cid = str(raw.get("id", ""))
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    items.append(raw)

        # --- Recover missing clients: digits, special chars, accented letters ---
        non_alpha_prefixes = (
            list("0123456789") + ["-", "'", ".", " "] + list("ÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ") + list("àâäéèêëïîôùûüçœæ")
        )
        for prefix in non_alpha_prefixes:
            try:
                data = self._client.get(
                    "/customers",
                    {"loose_last_name": prefix, "page_number": 0, "page_size": 1},
                )
                total = data.get("page", {}).get("totalElements", 0)
                if total == 0:
                    continue
                batch = self._client.get_paginated(
                    "/customers",
                    params={"loose_last_name": prefix},
                    page_size=50,
                    max_pages=20,
                )
                for raw in batch:
                    cid = str(raw.get("id", ""))
                    if cid and cid not in seen_ids:
                        seen_ids.add(cid)
                        items.append(raw)
            except Exception:
                logger.warning("cosium_customer_prefix_failed", prefix=prefix)

        # --- Catch-all: multiple sort orders without filter to find remaining ---
        for sort_param in ["lastName", "firstName", "id"]:
            try:
                batch = self._client.get_paginated(
                    "/customers",
                    params={"sort": sort_param},
                    page_size=50,
                    max_pages=5,
                )
                for raw in batch:
                    cid = str(raw.get("id", ""))
                    if cid and cid not in seen_ids:
                        seen_ids.add(cid)
                        items.append(raw)
            except Exception:
                logger.warning("cosium_customer_sort_failed", sort=sort_param)

        # --- Try fetching with include_hidden to get hidden/inactive clients ---
        try:
            batch = self._client.get_paginated(
                "/customers",
                params={"include_hidden": "true"},
                page_size=50,
                max_pages=5,
            )
            for raw in batch:
                cid = str(raw.get("id", ""))
                if cid and cid not in seen_ids:
                    seen_ids.add(cid)
                    items.append(raw)
        except Exception:
            logger.warning("cosium_customer_hidden_failed")

        logger.info("cosium_customers_fetched", total_unique=len(items))
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
                    customer_number=mapped.get("customer_number"),
                    street_number=mapped.get("street_number"),
                    street_name=mapped.get("street_name"),
                    mobile_phone_country=mapped.get("mobile_phone_country"),
                    site_id=mapped.get("site_id"),
                )
            )
        return customers

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

    def get_customer_documents(self, customer_cosium_id: int) -> list[dict]:
        """GET /customers/{id}/documents — liste des documents d'un client (lecture seule)."""
        data = self._client.get(f"/customers/{customer_cosium_id}/documents")
        embedded = data.get("_embedded", data)
        docs = embedded.get("documents", embedded.get("content", []))
        if not isinstance(docs, list):
            docs = [docs] if docs else []
        result: list[dict] = []
        for doc in docs:
            # Extract document ID from _links.self.href: .../documents/{id}
            doc_id = doc.get("id", 0)
            if not doc_id:
                self_href = doc.get("_links", {}).get("self", {}).get("href", "")
                if "/documents/" in self_href:
                    try:
                        doc_id = int(self_href.rsplit("/documents/", 1)[-1].split("?")[0].split("/")[0])
                    except (ValueError, IndexError):
                        pass
            result.append({
                "document_id": doc_id,
                "label": doc.get("name", doc.get("label", "")),
                "type": doc.get("type", doc.get("documentType", "")),
                "date": doc.get("date", doc.get("creationDate")),
                "size": doc.get("size"),
            })
        logger.info("cosium_customer_documents_fetched", customer_id=customer_cosium_id, total=len(result))
        return result

    def get_document_content(self, customer_cosium_id: int, document_id: int) -> bytes:
        """GET /customers/{id}/documents/{id}/content — contenu binaire du document."""
        return self._client.get_raw(f"/customers/{customer_cosium_id}/documents/{document_id}/content")

    def get_customer_optician(self, customer_erp_id: str) -> str | None:
        """GET /customers/{id}/optician — retourne le nom de l'opticien referent."""
        try:
            data = self._client.get(f"/customers/{customer_erp_id}/optician")
            first = data.get("firstName", "")
            last = data.get("lastName", "")
            name = f"{first} {last}".strip()
            return name if name else None
        except Exception:
            logger.debug("cosium_optician_not_found", customer_id=customer_erp_id)
            return None

    def get_customer_ophthalmologist_id(self, customer_erp_id: str) -> str | None:
        """Extract ophthalmologist reference from customer _links."""
        try:
            data = self._client.get(f"/customers/{customer_erp_id}")
            oph_href = data.get("_links", {}).get("ophthalmologist", {}).get("href", "")
            if "/doctors/" in oph_href:
                return oph_href.rsplit("/doctors/", 1)[-1].split("?")[0]
            return None
        except Exception:
            logger.debug("cosium_ophthalmologist_not_found", customer_id=customer_erp_id)
            return None

    def get_spectacle_file(self, file_id: int) -> dict:
        """GET /end-consumer/spectacles-files/{id} — dossier lunettes (container HAL).

        Retourne le container avec liens vers diopters, spectacles-selection, doctor-address.
        Lecture seule.
        """
        return self._client.get(f"/v1/end-consumer/spectacles-files/{file_id}")

    def get_spectacle_diopters(self, file_id: int) -> list[dict]:
        """GET /end-consumer/spectacles-files/{id}/diopters — dioptries du dossier lunettes.

        Retourne la liste des entrees de dioptries (sphere, cylinder, axis, addition, prism).
        Lecture seule.
        """
        data = self._client.get(f"/v1/end-consumer/spectacles-files/{file_id}/diopters")
        embedded = data.get("_embedded", {}) or {}
        items = embedded.get("content", []) if isinstance(embedded, dict) else []
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def get_spectacle_selection(self, file_id: int) -> dict:
        """GET /end-consumer/spectacles-files/{id}/spectacles-selection — selection courante du client.

        Retourne la liste des paires de lunettes en cours de selection.
        Lecture seule.
        """
        return self._client.get(f"/v1/end-consumer/spectacles-files/{file_id}/spectacles-selection")

    def list_spectacle_files_for_customer(self, customer_cosium_id: int) -> list[dict]:
        """GET /end-consumer/spectacles-files/?customerId=... — liste des dossiers lunettes d'un client.

        Le parametre customerId attend une reference HAL complete vers le client.
        Lecture seule.
        """
        customer_ref = f"/{self._client.tenant}/api/v1/end-consumer/customers/{customer_cosium_id}"
        data = self._client.get("/v1/end-consumer/spectacles-files/", params={"customerId": customer_ref})
        embedded = data.get("_embedded", {}) or {}
        items = embedded.get("content", []) if isinstance(embedded, dict) else []
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def list_commercial_operation_advantages(self, operation_id: int) -> list[dict]:
        """GET /commercial-operations/{id}/advantages — avantages d'une operation commerciale.

        Lecture seule. Note : les endpoints /vouchers et /carts existent uniquement
        en PUT/DELETE chez Cosium, donc INTERDITS par notre charte.
        """
        data = self._client.get(f"/commercial-operations/{operation_id}/advantages")
        items = data.get("content", []) if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def get_commercial_operation_advantage(self, operation_id: int, advantage_id: int) -> dict:
        """GET /commercial-operations/{op_id}/advantages/{adv_id} — detail d'un avantage."""
        return self._client.get(f"/commercial-operations/{operation_id}/advantages/{advantage_id}")

    def search_customers_loose(
        self,
        last_name: str | None = None,
        first_name: str | None = None,
        customer_number: str | None = None,
        page_size: int = 25,
    ) -> list[dict]:
        """GET /customers — recherche fuzzy via loose_* (lecture seule).

        Au moins un parametre doit etre fourni. Cosium fait du matching approximatif.
        """
        params: dict = {"page_number": 0, "page_size": page_size}
        if last_name:
            params["loose_last_name"] = last_name
        if first_name:
            params["loose_first_name"] = first_name
        if customer_number:
            params["loose_customer_number"] = customer_number
        data = self._client.get("/customers", params=params)
        embedded = data.get("_embedded", {}) or {}
        items = (
            embedded.get("customers", embedded.get("content", []))
            if isinstance(embedded, dict) else []
        )
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def get_customer_consents(self, customer_cosium_id: int) -> dict:
        """GET /customers/{id}/consents — flags marketing (lecture seule)."""
        return self._client.get(f"/customers/{customer_cosium_id}/consents")

    def list_customer_fidelity_cards(self, customer_cosium_id: int) -> list[dict]:
        """GET /customers/{id}/fidelity-cards — cartes de fidelite du client (lecture seule)."""
        data = self._client.get(f"/customers/{customer_cosium_id}/fidelity-cards")
        embedded = data.get("_embedded", {}) or {}
        items = embedded.get("content", []) if isinstance(embedded, dict) else []
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def list_customer_sponsorships(self, customer_cosium_id: int) -> list[dict]:
        """GET /customers/{id}/sponsorships — parrainages du client (lecture seule)."""
        data = self._client.get(f"/customers/{customer_cosium_id}/sponsorships")
        embedded = data.get("_embedded", {}) or {}
        items = embedded.get("content", []) if isinstance(embedded, dict) else []
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def list_notes_for_customer(self, customer_cosium_id: int) -> list[dict]:
        """GET /notes?customer_id={id} — notes CRM d'un client (lecture seule)."""
        data = self._client.get("/notes", params={"customer_id": customer_cosium_id})
        embedded = data.get("_embedded", {}) or {}
        items = embedded.get("content", []) if isinstance(embedded, dict) else []
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def get_note(self, note_id: int) -> dict:
        """GET /notes/{id} — detail d'une note (lecture seule)."""
        return self._client.get(f"/notes/{note_id}")

    def list_note_statuses(self) -> list[dict]:
        """GET /notes/statuses — reference des statuts de notes (lecture seule)."""
        data = self._client.get("/notes/statuses")
        embedded = data.get("_embedded", {}) or {}
        items = embedded.get("content", []) if isinstance(embedded, dict) else data
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def list_after_sales_services(
        self,
        status: str | None = None,
        resolution_status: str | None = None,
        creation_date: str | None = None,
        site_name: str | None = None,
        page: int = 0,
        page_size: int = 50,
        max_pages: int = 20,
    ) -> list[dict]:
        """GET /after-sales-services — liste des dossiers SAV avec filtres (lecture seule).

        Statuts possibles : TO_REPAIR, IN_PROCESS, REPAIR_IN_PROCESS, FINISHED
        Resolution : RESOLVED, SOLD_OUT
        Dates format : yyyy-mm-dd
        """
        params: dict = {}
        if status:
            params["status"] = status
        if resolution_status:
            params["resolution_status"] = resolution_status
        if creation_date:
            params["creation_date"] = creation_date
        if site_name:
            params["site_name"] = site_name
        return self._client.get_paginated(
            "/after-sales-services", params=params, page_size=page_size, max_pages=max_pages
        )

    def get_after_sales_service(self, sav_id: int) -> dict:
        """GET /after-sales-services/{id} — detail d'un dossier SAV (lecture seule)."""
        return self._client.get(f"/after-sales-services/{sav_id}")

    def list_optical_frames(self, page: int = 0, page_size: int = 50, max_pages: int = 20) -> list[dict]:
        """GET /end-consumer/catalog/optical-frames — catalogue montures (lecture seule)."""
        return self._client.get_paginated(
            "/v1/end-consumer/catalog/optical-frames", page_size=page_size, max_pages=max_pages
        )

    def get_optical_frame(self, frame_id: int) -> dict:
        """GET /end-consumer/catalog/optical-frames/{id} — detail d'une monture (lecture seule)."""
        return self._client.get(f"/v1/end-consumer/catalog/optical-frames/{frame_id}")

    def list_optical_lenses(self, page: int = 0, page_size: int = 50, max_pages: int = 20) -> list[dict]:
        """GET /end-consumer/catalog/optical-lenses — catalogue verres (lecture seule)."""
        return self._client.get_paginated(
            "/v1/end-consumer/catalog/optical-lenses", page_size=page_size, max_pages=max_pages
        )

    def get_optical_lens(self, lens_id: int) -> dict:
        """GET /end-consumer/catalog/optical-lenses/{id} — detail d'un verre (lecture seule)."""
        return self._client.get(f"/v1/end-consumer/catalog/optical-lenses/{lens_id}")

    def get_optical_lens_options(self, lens_id: int, code: str | None = None) -> dict:
        """GET /end-consumer/catalog/optical-lenses/{id}/available-options — options du verre."""
        params = {"code": code} if code else None
        return self._client.get(f"/v1/end-consumer/catalog/optical-lenses/{lens_id}/available-options", params=params)

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
