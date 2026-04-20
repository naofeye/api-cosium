"""Extra CosiumConnector methods — secondary/extended endpoints.

Extracted from cosium_connector.py to keep files under 300 lines.
Contains methods for: spectacles, catalog (frames/lenses), SAV,
notes, fidelity cards, sponsorships, commercial operations.

All methods are READ-ONLY (GET only) per security rules.
"""

from app.core.logging import get_logger

logger = get_logger("cosium_connector_extras")


class CosiumConnectorExtrasMixin:
    """Mixin providing secondary Cosium API endpoints.

    Must be used with CosiumConnector (requires self._client).
    """

    def get_customer_documents(self, customer_cosium_id: int) -> list[dict]:
        """GET /customers/{id}/documents — liste des documents d'un client (lecture seule)."""
        data = self._client.get(f"/customers/{customer_cosium_id}/documents")
        embedded = data.get("_embedded", data)
        docs = embedded.get("documents", embedded.get("content", []))
        if not isinstance(docs, list):
            docs = [docs] if docs else []
        result: list[dict] = []
        for doc in docs:
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
        except Exception as exc:
            logger.debug("cosium_optician_not_found", customer_id=customer_erp_id, error=str(exc), error_type=type(exc).__name__)
            return None

    def get_customer_ophthalmologist_id(self, customer_erp_id: str) -> str | None:
        """Extract ophthalmologist reference from customer _links."""
        try:
            data = self._client.get(f"/customers/{customer_erp_id}")
            oph_href = data.get("_links", {}).get("ophthalmologist", {}).get("href", "")
            if "/doctors/" in oph_href:
                return oph_href.rsplit("/doctors/", 1)[-1].split("?")[0]
            return None
        except Exception as exc:
            logger.debug("cosium_ophthalmologist_not_found", customer_id=customer_erp_id, error=str(exc), error_type=type(exc).__name__)
            return None

    def get_spectacle_file(self, file_id: int) -> dict:
        """GET /end-consumer/spectacles-files/{id} — dossier lunettes (container HAL)."""
        return self._client.get(f"/v1/end-consumer/spectacles-files/{file_id}")

    def get_spectacle_diopters(self, file_id: int) -> list[dict]:
        """GET /end-consumer/spectacles-files/{id}/diopters — dioptries du dossier lunettes."""
        data = self._client.get(f"/v1/end-consumer/spectacles-files/{file_id}/diopters")
        embedded = data.get("_embedded", {}) or {}
        items = embedded.get("content", []) if isinstance(embedded, dict) else []
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def get_spectacle_selection(self, file_id: int) -> dict:
        """GET /end-consumer/spectacles-files/{id}/spectacles-selection."""
        return self._client.get(f"/v1/end-consumer/spectacles-files/{file_id}/spectacles-selection")

    def list_spectacle_files_for_customer(self, customer_cosium_id: int) -> list[dict]:
        """GET /end-consumer/spectacles-files/?customerId=... — liste des dossiers lunettes."""
        customer_ref = f"/{self._client.tenant}/api/v1/end-consumer/customers/{customer_cosium_id}"
        data = self._client.get("/v1/end-consumer/spectacles-files/", params={"customerId": customer_ref})
        embedded = data.get("_embedded", {}) or {}
        items = embedded.get("content", []) if isinstance(embedded, dict) else []
        if not isinstance(items, list):
            items = [items] if items else []
        return items

    def list_commercial_operation_advantages(self, operation_id: int) -> list[dict]:
        """GET /commercial-operations/{id}/advantages — avantages d'une operation commerciale."""
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
        """GET /customers — recherche fuzzy via loose_* (lecture seule)."""
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

    def get_customer_detail(self, customer_cosium_id: int, embeds: list[str] | None = None) -> dict:
        """GET /customers/{id}?embed=... — detail client complet (lecture seule)."""
        params = {}
        if embeds:
            params["embed"] = ",".join(embeds)
        return self._client.get(f"/customers/{customer_cosium_id}", params=params or None)

    def get_invoice_payment_links(self, invoice_cosium_id: int) -> dict:
        """GET /invoices/{id}/payment-links — liens de paiement en ligne (lecture seule)."""
        return self._client.get(f"/invoices/{invoice_cosium_id}/payment-links")

    def get_invoice_payment(self, payment_id: int) -> dict:
        """GET /invoice-payments/{id} — detail d'un reglement de facture (lecture seule)."""
        return self._client.get(f"/invoice-payments/{payment_id}")

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
        """GET /after-sales-services — liste des dossiers SAV avec filtres (lecture seule)."""
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
