"""Tests for extended Cosium sync: payments, TPP, prescriptions, documents."""

from unittest.mock import MagicMock, patch

import pytest

from app.integrations.cosium.adapter import (
    cosium_payment_to_optiflow,
    cosium_prescription_to_optiflow,
    cosium_tpp_to_optiflow,
)
from app.integrations.cosium.cosium_connector import CosiumConnector


# ─── Adapter: Payment mapping ──────────────────────────────────────


class TestPaymentAdapter:
    def test_basic_payment_mapping(self):
        raw = {
            "id": 101,
            "paymentTypeId": 5,
            "amount": 150.50,
            "originalAmount": 200.0,
            "type": "CB",
            "dueDate": "2026-04-01T00:00:00.000Z",
            "issuerName": "DUPONT Jean",
            "bank": "BNP Paribas",
            "siteName": "Paris Centre",
            "comment": "Paiement partiel",
            "paymentNumber": "PAY-001",
            "accountingDocumentNumber": 42,
        }
        result = cosium_payment_to_optiflow(raw)
        assert result["cosium_id"] == 101
        assert result["payment_type_id"] == 5
        assert result["amount"] == 150.50
        assert result["original_amount"] == 200.0
        assert result["type"] == "CB"
        assert result["issuer_name"] == "DUPONT Jean"
        assert result["bank"] == "BNP Paribas"
        assert result["site_name"] == "Paris Centre"
        assert result["comment"] == "Paiement partiel"
        assert result["payment_number"] == "PAY-001"
        assert result["invoice_cosium_id"] == 42

    def test_invoice_id_from_links(self):
        raw = {
            "id": 102,
            "amount": 50,
            "_links": {
                "accounting-document": {"href": "https://c1.cosium.biz/tenant/api/invoices/22"}
            },
        }
        result = cosium_payment_to_optiflow(raw)
        assert result["invoice_cosium_id"] == 22

    def test_missing_fields_defaults(self):
        raw = {"id": 103}
        result = cosium_payment_to_optiflow(raw)
        assert result["cosium_id"] == 103
        assert result["amount"] == 0
        assert result["type"] == ""
        assert result["issuer_name"] == ""
        assert result["invoice_cosium_id"] is None


# ─── Adapter: TPP mapping ──────────────────────────────────────────


class TestTPPAdapter:
    def test_basic_tpp_mapping(self):
        raw = {
            "id": 201,
            "socialSecurityAmount": 125.30,
            "socialSecurityThirdPartyPayment": True,
            "additionalHealthCareAmount": 75.00,
            "additionalHealthCareThirdPartyPayment": False,
            "_links": {
                "accounting-document": {"href": "https://c1.cosium.biz/tenant/api/invoices/55"}
            },
        }
        result = cosium_tpp_to_optiflow(raw)
        assert result["cosium_id"] == 201
        assert result["social_security_amount"] == 125.30
        assert result["social_security_tpp"] is True
        assert result["additional_health_care_amount"] == 75.00
        assert result["additional_health_care_tpp"] is False
        assert result["invoice_cosium_id"] == 55

    def test_id_from_self_link(self):
        raw = {
            "socialSecurityAmount": 0,
            "_links": {
                "self": {"href": "https://c1.cosium.biz/tenant/api/third-party-payments/305"},
                "accounting-document": {"href": "https://c1.cosium.biz/tenant/api/invoices/10"},
            },
        }
        result = cosium_tpp_to_optiflow(raw)
        assert result["cosium_id"] == 305
        assert result["invoice_cosium_id"] == 10

    def test_defaults_when_empty(self):
        raw = {"id": 202}
        result = cosium_tpp_to_optiflow(raw)
        assert result["social_security_amount"] == 0
        assert result["social_security_tpp"] is False
        assert result["additional_health_care_amount"] == 0
        assert result["additional_health_care_tpp"] is False
        assert result["invoice_cosium_id"] is None


# ─── Adapter: Prescription mapping ──────────────────────────────────


class TestPrescriptionAdapter:
    def test_diopter_conversion(self):
        """Diopter values in hundredths must be divided by 100."""
        raw = {
            "id": 301,
            "prescriptionDate": "2026-03-15",
            "fileDate": "2026-03-16T10:00:00.000Z",
            "diopters": [
                {
                    "sphere100Right": -50,
                    "sphere100Left": -75,
                    "cylinder100Right": -25,
                    "cylinder100Left": -50,
                    "axisRight": 90,
                    "axisLeft": 180,
                    "addition100Right": 225,
                    "addition100Left": 225,
                    "visionType": "DISTANCE",
                }
            ],
            "selectedSpectacles": [
                {"frameBrandName": "Ray-Ban", "frameLabel": "Aviator", "invoiceNumber": "F-001"}
            ],
            "_links": {
                "customer": {"href": "https://c1.cosium.biz/tenant/api/customers/99"}
            },
            "_embedded": {
                "prescriber": {"firstName": "Dr", "lastName": "Martin"}
            },
        }
        result = cosium_prescription_to_optiflow(raw)

        assert result["cosium_id"] == 301
        assert result["prescription_date"] == "2026-03-15"
        assert result["customer_cosium_id"] == 99
        assert result["prescriber_name"] == "Dr Martin"

        # Diopters converted from hundredths
        assert result["sphere_right"] == -0.50
        assert result["sphere_left"] == -0.75
        assert result["cylinder_right"] == -0.25
        assert result["cylinder_left"] == -0.50
        assert result["axis_right"] == 90  # axis is degrees, not hundredths
        assert result["axis_left"] == 180
        assert result["addition_right"] == 2.25
        assert result["addition_left"] == 2.25

        # Spectacles stored as JSON
        assert "Ray-Ban" in result["spectacles_json"]

    def test_no_diopters(self):
        raw = {"id": 302, "diopters": []}
        result = cosium_prescription_to_optiflow(raw)
        assert result["sphere_right"] is None
        assert result["sphere_left"] is None

    def test_zero_diopters(self):
        raw = {
            "id": 303,
            "diopters": [{"sphere100Right": 0, "sphere100Left": 0}],
        }
        result = cosium_prescription_to_optiflow(raw)
        assert result["sphere_right"] == 0.0
        assert result["sphere_left"] == 0.0


# ─── Document proxy endpoint ───────────────────────────────────────


class TestDocumentProxy:
    def test_list_documents(self, client, auth_headers, db, default_tenant):
        """GET /api/v1/cosium-documents/{id} returns documents list."""
        mock_connector = MagicMock(spec=CosiumConnector)
        mock_connector.get_customer_documents.return_value = [
            {"document_id": 1, "label": "Ordonnance", "type": "PRESCRIPTION", "date": "2026-03-20", "size": 12345},
            {"document_id": 2, "label": "Devis", "type": "QUOTE", "date": "2026-03-21", "size": None},
        ]

        with patch(
            "app.api.routers.cosium_documents._get_connector_for_tenant"
        ) as mock_get, patch(
            "app.api.routers.cosium_documents._authenticate_connector"
        ):
            mock_get.return_value = (mock_connector, default_tenant)
            resp = client.get("/api/v1/cosium-documents/99", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["items"][0]["label"] == "Ordonnance"
        assert data["items"][1]["document_id"] == 2

    def test_download_document(self, client, auth_headers, db, default_tenant):
        """GET /api/v1/cosium-documents/{id}/{doc_id}/download proxies binary content."""
        mock_connector = MagicMock(spec=CosiumConnector)
        mock_connector.get_document_content.return_value = b"%PDF-1.4 fake content"

        with patch(
            "app.api.routers.cosium_documents._get_connector_for_tenant"
        ) as mock_get, patch(
            "app.api.routers.cosium_documents._authenticate_connector"
        ):
            mock_get.return_value = (mock_connector, default_tenant)
            resp = client.get("/api/v1/cosium-documents/99/1/download", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.content == b"%PDF-1.4 fake content"
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_download_cosium_error(self, client, auth_headers, db, default_tenant):
        """Download returns 502 when Cosium fails."""
        mock_connector = MagicMock(spec=CosiumConnector)
        mock_connector.get_document_content.side_effect = Exception("Cosium timeout")

        with patch(
            "app.api.routers.cosium_documents._get_connector_for_tenant"
        ) as mock_get, patch(
            "app.api.routers.cosium_documents._authenticate_connector"
        ):
            mock_get.return_value = (mock_connector, default_tenant)
            resp = client.get("/api/v1/cosium-documents/99/1/download", headers=auth_headers)

        assert resp.status_code == 502
