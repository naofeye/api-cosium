"""Tests for client_mutuelle_service — detect and manage client-mutuelle associations."""

import json
from unittest.mock import patch

import pytest

from app.core.exceptions import NotFoundError
from app.domain.schemas.client_mutuelle import ClientMutuelleCreate
from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_data import CosiumDocument, CosiumInvoice, CosiumThirdPartyPayment
from app.models.cosium_reference import CosiumMutuelle
from app.models.document_extraction import DocumentExtraction
from app.services import client_mutuelle_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_customer(db, tenant_id: int, first_name: str = "Jean", last_name: str = "Dupont", cosium_id: str | None = None) -> Customer:
    c = Customer(tenant_id=tenant_id, first_name=first_name, last_name=last_name, cosium_id=cosium_id)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def _make_invoice(db, tenant_id: int, customer_id: int, cosium_id: int, share_private_insurance: float = 0.0) -> CosiumInvoice:
    inv = CosiumInvoice(
        tenant_id=tenant_id,
        cosium_id=cosium_id,
        invoice_number=f"INV-{cosium_id}",
        customer_name="Jean Dupont",
        customer_id=customer_id,
        share_private_insurance=share_private_insurance,
    )
    db.add(inv)
    db.flush()
    db.refresh(inv)
    return inv


def _make_tpp(db, tenant_id: int, invoice_cosium_id: int, amc_amount: float) -> CosiumThirdPartyPayment:
    tpp = CosiumThirdPartyPayment(
        tenant_id=tenant_id,
        cosium_id=invoice_cosium_id + 10000,
        invoice_cosium_id=invoice_cosium_id,
        additional_health_care_amount=amc_amount,
        social_security_amount=0.0,
    )
    db.add(tpp)
    db.flush()
    return tpp


def _make_cosium_document(db, tenant_id: int, customer_cosium_id: int, customer_id: int, cosium_document_id: int) -> CosiumDocument:
    doc = CosiumDocument(
        tenant_id=tenant_id,
        customer_cosium_id=customer_cosium_id,
        customer_id=customer_id,
        cosium_document_id=cosium_document_id,
    )
    db.add(doc)
    db.flush()
    db.refresh(doc)
    return doc


def _make_extraction(db, tenant_id: int, cosium_document_id: int, document_type: str, structured_data: dict) -> DocumentExtraction:
    ext = DocumentExtraction(
        tenant_id=tenant_id,
        cosium_document_id=cosium_document_id,
        document_type=document_type,
        structured_data=json.dumps(structured_data),
    )
    db.add(ext)
    db.flush()
    return ext


# ---------------------------------------------------------------------------
# get_client_mutuelles
# ---------------------------------------------------------------------------

class TestGetClientMutuelles:
    def test_returns_empty_for_client_without_mutuelles(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        db.commit()

        result = client_mutuelle_service.get_client_mutuelles(db, default_tenant.id, customer.id)
        assert result == []

    def test_returns_mutuelles_for_client(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        mut = ClientMutuelle(
            tenant_id=default_tenant.id,
            customer_id=customer.id,
            mutuelle_name="MGEN",
            source="manual",
            confidence=1.0,
        )
        db.add(mut)
        db.commit()

        result = client_mutuelle_service.get_client_mutuelles(db, default_tenant.id, customer.id)
        assert len(result) == 1
        assert result[0].mutuelle_name == "MGEN"

    def test_raises_not_found_for_unknown_customer(self, db, default_tenant):
        with pytest.raises(NotFoundError):
            client_mutuelle_service.get_client_mutuelles(db, default_tenant.id, 99999)

    def test_does_not_return_other_tenant_mutuelles(self, db, default_tenant):
        from app.models import Organization, Tenant

        org2 = Organization(name="Org2", slug="org2-cm", plan="solo")
        db.add(org2)
        db.flush()
        tenant2 = Tenant(organization_id=org2.id, name="Mag2", slug="mag2-cm")
        db.add(tenant2)
        db.flush()

        customer1 = _make_customer(db, default_tenant.id)
        customer2 = _make_customer(db, tenant2.id)

        # Mutuelle on customer2 of tenant2 — should not leak into tenant1 query
        mut = ClientMutuelle(
            tenant_id=tenant2.id,
            customer_id=customer2.id,
            mutuelle_name="Harmonie",
            source="manual",
            confidence=1.0,
        )
        db.add(mut)
        db.commit()

        result = client_mutuelle_service.get_client_mutuelles(db, default_tenant.id, customer1.id)
        assert result == []


# ---------------------------------------------------------------------------
# add_client_mutuelle
# ---------------------------------------------------------------------------

class TestAddClientMutuelle:
    def test_adds_mutuelle_to_client(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        db.commit()

        payload = ClientMutuelleCreate(mutuelle_name="Malakoff", source="manual")
        result = client_mutuelle_service.add_client_mutuelle(
            db, default_tenant.id, customer.id, payload
        )

        assert result.mutuelle_name == "Malakoff"
        assert result.customer_id == customer.id
        assert result.tenant_id == default_tenant.id

    def test_raises_not_found_for_unknown_customer(self, db, default_tenant):
        payload = ClientMutuelleCreate(mutuelle_name="MGEN", source="manual")
        with pytest.raises(NotFoundError):
            client_mutuelle_service.add_client_mutuelle(db, default_tenant.id, 99999, payload)

    def test_mutuelle_persisted_in_db(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        db.commit()

        payload = ClientMutuelleCreate(mutuelle_name="April", source="cosium_invoice")
        client_mutuelle_service.add_client_mutuelle(db, default_tenant.id, customer.id, payload)

        mutuelles = client_mutuelle_service.get_client_mutuelles(db, default_tenant.id, customer.id)
        assert len(mutuelles) == 1
        assert mutuelles[0].source == "cosium_invoice"


# ---------------------------------------------------------------------------
# delete_client_mutuelle
# ---------------------------------------------------------------------------

class TestDeleteClientMutuelle:
    def test_deletes_mutuelle(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        mut = ClientMutuelle(
            tenant_id=default_tenant.id,
            customer_id=customer.id,
            mutuelle_name="MGEN",
            source="manual",
            confidence=1.0,
        )
        db.add(mut)
        db.commit()

        result = client_mutuelle_service.delete_client_mutuelle(
            db, default_tenant.id, customer.id, mut.id
        )

        assert result is True
        remaining = client_mutuelle_service.get_client_mutuelles(db, default_tenant.id, customer.id)
        assert remaining == []

    def test_raises_not_found_for_unknown_mutuelle(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id)
        db.commit()

        with pytest.raises(NotFoundError):
            client_mutuelle_service.delete_client_mutuelle(
                db, default_tenant.id, customer.id, 99999
            )

    def test_raises_not_found_when_mutuelle_belongs_to_different_customer(self, db, default_tenant):
        customer1 = _make_customer(db, default_tenant.id, "Jean", "Un")
        customer2 = _make_customer(db, default_tenant.id, "Paul", "Deux")
        mut = ClientMutuelle(
            tenant_id=default_tenant.id,
            customer_id=customer2.id,
            mutuelle_name="AXA",
            source="manual",
            confidence=1.0,
        )
        db.add(mut)
        db.commit()

        with pytest.raises(NotFoundError):
            client_mutuelle_service.delete_client_mutuelle(
                db, default_tenant.id, customer1.id, mut.id
            )


# ---------------------------------------------------------------------------
# detect_client_mutuelles — source: tiers payant
# ---------------------------------------------------------------------------

class TestDetectFromThirdPartyPayments:
    def test_detects_mutuelle_from_tpp(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id, cosium_id="42")
        invoice = _make_invoice(db, default_tenant.id, customer.id, cosium_id=101)
        _make_tpp(db, default_tenant.id, invoice_cosium_id=invoice.cosium_id, amc_amount=75.0)
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        assert len(result) >= 1
        tpp_detection = next((d for d in result if d["source"] == "cosium_tpp"), None)
        assert tpp_detection is not None
        assert tpp_detection["confidence"] == 1.0

    def test_no_tpp_returns_empty_for_source_1(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id, cosium_id="42")
        _make_invoice(db, default_tenant.id, customer.id, cosium_id=102, share_private_insurance=0.0)
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        tpp_results = [d for d in result if d["source"] == "cosium_tpp"]
        assert tpp_results == []

    def test_tpp_with_zero_amc_not_detected(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id, cosium_id="43")
        invoice = _make_invoice(db, default_tenant.id, customer.id, cosium_id=103)
        _make_tpp(db, default_tenant.id, invoice_cosium_id=invoice.cosium_id, amc_amount=0.0)
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        tpp_results = [d for d in result if d["source"] == "cosium_tpp"]
        assert tpp_results == []


# ---------------------------------------------------------------------------
# detect_client_mutuelles — source: invoice insurance
# ---------------------------------------------------------------------------

class TestDetectFromInvoiceInsurance:
    def test_detects_from_invoice_share_private_insurance(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id, cosium_id="50")
        _make_invoice(db, default_tenant.id, customer.id, cosium_id=200, share_private_insurance=120.0)
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        inv_det = next((d for d in result if d["source"] == "cosium_invoice"), None)
        assert inv_det is not None
        assert inv_det["confidence"] == 0.7

    def test_invoice_detection_skipped_when_tpp_found(self, db, default_tenant):
        """TPP (source 1) has priority — invoice (source 2) not added when tpp found."""
        customer = _make_customer(db, default_tenant.id, cosium_id="51")
        invoice = _make_invoice(db, default_tenant.id, customer.id, cosium_id=201, share_private_insurance=80.0)
        _make_tpp(db, default_tenant.id, invoice_cosium_id=invoice.cosium_id, amc_amount=50.0)
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        inv_results = [d for d in result if d["source"] == "cosium_invoice"]
        assert inv_results == []
        tpp_results = [d for d in result if d["source"] == "cosium_tpp"]
        assert len(tpp_results) == 1

    def test_no_insurance_in_invoices_returns_empty(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id, cosium_id="52")
        _make_invoice(db, default_tenant.id, customer.id, cosium_id=202, share_private_insurance=0.0)
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        inv_results = [d for d in result if d["source"] == "cosium_invoice"]
        assert inv_results == []


# ---------------------------------------------------------------------------
# detect_client_mutuelles — source: OCR documents
# ---------------------------------------------------------------------------

class TestDetectFromOcrDocuments:
    def test_detects_mutuelle_from_attestation_ocr(self, db, default_tenant):
        COSIUM_ID = 60
        customer = _make_customer(db, default_tenant.id, cosium_id=str(COSIUM_ID))
        doc = _make_cosium_document(
            db, default_tenant.id,
            customer_cosium_id=COSIUM_ID,
            customer_id=customer.id,
            cosium_document_id=300,
        )
        _make_extraction(
            db, default_tenant.id,
            cosium_document_id=doc.cosium_document_id,
            document_type="attestation_mutuelle",
            structured_data={"nom_mutuelle": "MGEN", "numero_adherent": "123456"},
        )
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        ocr_results = [d for d in result if d["source"] == "document_ocr"]
        assert len(ocr_results) == 1
        assert ocr_results[0]["mutuelle_name"] == "MGEN"
        assert ocr_results[0]["confidence"] == 0.9
        assert ocr_results[0]["numero_adherent"] == "123456"

    def test_detects_from_carte_mutuelle(self, db, default_tenant):
        COSIUM_ID = 61
        customer = _make_customer(db, default_tenant.id, cosium_id=str(COSIUM_ID))
        doc = _make_cosium_document(
            db, default_tenant.id,
            customer_cosium_id=COSIUM_ID,
            customer_id=customer.id,
            cosium_document_id=301,
        )
        _make_extraction(
            db, default_tenant.id,
            cosium_document_id=doc.cosium_document_id,
            document_type="carte_mutuelle",
            structured_data={"mutuelle": "Harmonie Mutuelle"},
        )
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        ocr_results = [d for d in result if d["source"] == "document_ocr"]
        assert len(ocr_results) == 1
        assert "Harmonie" in ocr_results[0]["mutuelle_name"]

    def test_ocr_deduplicates_same_mutuelle(self, db, default_tenant):
        """Two OCR documents with the same mutuelle name are deduplicated."""
        COSIUM_ID = 62
        customer = _make_customer(db, default_tenant.id, cosium_id=str(COSIUM_ID))
        for doc_id in [302, 303]:
            doc = _make_cosium_document(
                db, default_tenant.id,
                customer_cosium_id=COSIUM_ID,
                customer_id=customer.id,
                cosium_document_id=doc_id,
            )
            _make_extraction(
                db, default_tenant.id,
                cosium_document_id=doc.cosium_document_id,
                document_type="attestation_mutuelle",
                structured_data={"nom_mutuelle": "MGEN"},
            )
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        ocr_results = [d for d in result if d["source"] == "document_ocr" and d["mutuelle_name"] == "MGEN"]
        assert len(ocr_results) == 1

    def test_ocr_skipped_when_no_cosium_id(self, db, default_tenant):
        """Customer without cosium_id returns no OCR detections."""
        customer = _make_customer(db, default_tenant.id, cosium_id=None)
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        ocr_results = [d for d in result if d["source"] == "document_ocr"]
        assert ocr_results == []

    def test_ocr_extraction_with_empty_mutuelle_name_ignored(self, db, default_tenant):
        COSIUM_ID = 63
        customer = _make_customer(db, default_tenant.id, cosium_id=str(COSIUM_ID))
        doc = _make_cosium_document(
            db, default_tenant.id,
            customer_cosium_id=COSIUM_ID,
            customer_id=customer.id,
            cosium_document_id=304,
        )
        _make_extraction(
            db, default_tenant.id,
            cosium_document_id=doc.cosium_document_id,
            document_type="attestation_mutuelle",
            structured_data={"nom_mutuelle": ""},  # empty name
        )
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        ocr_results = [d for d in result if d["source"] == "document_ocr"]
        assert ocr_results == []


# ---------------------------------------------------------------------------
# detect_client_mutuelles — unknown client
# ---------------------------------------------------------------------------

class TestDetectClientMutuellesErrors:
    def test_raises_not_found_for_unknown_customer(self, db, default_tenant):
        with pytest.raises(NotFoundError):
            client_mutuelle_service.detect_client_mutuelles(
                db, default_tenant.id, 99999
            )

    def test_customer_with_no_invoices_returns_empty(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id, cosium_id="70")
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        assert result == []


# ---------------------------------------------------------------------------
# try_match_cosium_mutuelle — enrichissement avec organisme de reference
# ---------------------------------------------------------------------------

class TestTryMatchCosiumMutuelle:
    def test_matches_known_payer_organization(self, db, default_tenant):
        cosium_mut = CosiumMutuelle(
            tenant_id=default_tenant.id,
            cosium_id=9001,
            name="MGEN Mutuelle",
            code="MGEN",
            label="MGEN",
        )
        db.add(cosium_mut)
        db.commit()

        COSIUM_ID = 80
        customer = _make_customer(db, default_tenant.id, cosium_id=str(COSIUM_ID))
        doc = _make_cosium_document(
            db, default_tenant.id,
            customer_cosium_id=COSIUM_ID,
            customer_id=customer.id,
            cosium_document_id=400,
        )
        _make_extraction(
            db, default_tenant.id,
            cosium_document_id=doc.cosium_document_id,
            document_type="attestation_mutuelle",
            structured_data={"nom_mutuelle": "MGEN"},
        )
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        ocr_det = next((d for d in result if d["source"] == "document_ocr"), None)
        assert ocr_det is not None
        assert ocr_det.get("mutuelle_id") == cosium_mut.id
        assert ocr_det["mutuelle_name"] == "MGEN Mutuelle"

    def test_unknown_mutuelle_keeps_original_name(self, db, default_tenant):
        COSIUM_ID = 81
        customer = _make_customer(db, default_tenant.id, cosium_id=str(COSIUM_ID))
        doc = _make_cosium_document(
            db, default_tenant.id,
            customer_cosium_id=COSIUM_ID,
            customer_id=customer.id,
            cosium_document_id=401,
        )
        _make_extraction(
            db, default_tenant.id,
            cosium_document_id=doc.cosium_document_id,
            document_type="attestation_mutuelle",
            structured_data={"nom_mutuelle": "Mutuelle Inconnue XYZ"},
        )
        db.commit()

        result = client_mutuelle_service.detect_client_mutuelles(
            db, default_tenant.id, customer.id
        )

        ocr_det = next((d for d in result if d["source"] == "document_ocr"), None)
        assert ocr_det is not None
        assert ocr_det.get("mutuelle_id") is None
        assert ocr_det["mutuelle_name"] == "Mutuelle Inconnue XYZ"


# ---------------------------------------------------------------------------
# detect_all_clients_mutuelles (batch)
# ---------------------------------------------------------------------------

class TestDetectAllClientsMutuelles:
    def test_batch_scans_clients_with_invoices(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id, cosium_id="90")
        _make_invoice(db, default_tenant.id, customer.id, cosium_id=500, share_private_insurance=60.0)
        db.commit()

        result = client_mutuelle_service.detect_all_clients_mutuelles(db, default_tenant.id)

        assert result.total_clients_scanned >= 1

    def test_batch_creates_new_mutuelle_records(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id, cosium_id="91")
        invoice = _make_invoice(db, default_tenant.id, customer.id, cosium_id=501)
        _make_tpp(db, default_tenant.id, invoice_cosium_id=invoice.cosium_id, amc_amount=40.0)
        db.commit()

        result = client_mutuelle_service.detect_all_clients_mutuelles(db, default_tenant.id)

        assert result.new_mutuelles_created >= 1

    def test_batch_skips_existing_mutuelles(self, db, default_tenant):
        customer = _make_customer(db, default_tenant.id, cosium_id="92")
        invoice = _make_invoice(db, default_tenant.id, customer.id, cosium_id=502)
        _make_tpp(db, default_tenant.id, invoice_cosium_id=invoice.cosium_id, amc_amount=30.0)

        # Pre-populate the mutuelle that would be detected
        existing = ClientMutuelle(
            tenant_id=default_tenant.id,
            customer_id=customer.id,
            mutuelle_name="Mutuelle (tiers payant detecte)",
            source="cosium_tpp",
            confidence=1.0,
        )
        db.add(existing)
        db.commit()

        result = client_mutuelle_service.detect_all_clients_mutuelles(db, default_tenant.id)

        assert result.existing_mutuelles_skipped >= 1
        assert result.new_mutuelles_created == 0

    def test_batch_with_no_scannable_clients_returns_zero(self, db, default_tenant):
        # No invoices, no OCR documents
        _make_customer(db, default_tenant.id)
        db.commit()

        result = client_mutuelle_service.detect_all_clients_mutuelles(db, default_tenant.id)

        assert result.total_clients_scanned == 0
        assert result.new_mutuelles_created == 0
