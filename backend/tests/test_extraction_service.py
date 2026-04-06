"""Tests for extraction_service (OCR + classification + persistence)."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from app.domain.schemas.ocr import DocumentClassification, ExtractedDocument
from app.models import Tenant
from app.models.case import Case
from app.models.client import Customer
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction


def _make_doc(db: Session, tenant_id: int) -> Document:
    """Helper to create a customer -> case -> document chain."""
    cust = Customer(tenant_id=tenant_id, first_name="Test", last_name="Client")
    db.add(cust)
    db.flush()
    case = Case(tenant_id=tenant_id, customer_id=cust.id, status="en_cours")
    db.add(case)
    db.flush()
    doc = Document(
        tenant_id=tenant_id, case_id=case.id,
        type="ordonnance", filename="scan.pdf", storage_key="docs/scan.pdf",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ---------- 1. Extract from PDF (mock pdfplumber) ----------

@patch("app.services.extraction_service.storage")
@patch("app.services.extraction_service.ocr_service")
@patch("app.services.extraction_service.parse_document", return_value=None)
def test_extract_pdf_document(mock_parse, mock_ocr, mock_storage, db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    doc = _make_doc(db, tid)

    mock_storage.download_file.return_value = b"%PDF-fake"
    mock_ocr.extract_and_classify.return_value = (
        ExtractedDocument(
            raw_text="Ordonnance Dr Martin", page_count=1,
            extraction_method="pdfplumber", confidence=None, language="fra",
        ),
        DocumentClassification(
            document_type="ordonnance", confidence=0.9, keywords_found=["ordonnance"],
        ),
    )

    from app.services.extraction_service import extract_document

    result = extract_document(db, tid, doc.id)

    assert result.raw_text == "Ordonnance Dr Martin"
    assert result.extraction_method == "pdfplumber"
    assert result.document_type == "ordonnance"


# ---------- 2. Extract and classify as ordonnance ----------

@patch("app.services.extraction_service.storage")
@patch("app.services.extraction_service.ocr_service")
@patch("app.services.extraction_service.parse_document", return_value={"prescripteur": "Dr Martin"})
def test_extract_and_classify_ordonnance(mock_parse, mock_ocr, mock_storage, db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    doc = _make_doc(db, tid)

    mock_storage.download_file.return_value = b"bytes"
    mock_ocr.extract_and_classify.return_value = (
        ExtractedDocument(
            raw_text="Ordonnance sphere OD -2.50", page_count=1,
            extraction_method="pdfplumber", confidence=None,
        ),
        DocumentClassification(
            document_type="ordonnance", confidence=0.92,
            keywords_found=["ordonnance", "sphere", "OD"],
        ),
    )

    from app.services.extraction_service import extract_document

    result = extract_document(db, tid, doc.id)

    assert result.document_type == "ordonnance"
    assert result.classification_confidence == 0.92
    assert result.structured_data is not None
    mock_parse.assert_called_once()


# ---------- 3. Extract and classify as devis ----------

@patch("app.services.extraction_service.storage")
@patch("app.services.extraction_service.ocr_service")
@patch("app.services.extraction_service.parse_document", return_value={"montant_ttc": 450.0})
def test_extract_and_classify_devis(mock_parse, mock_ocr, mock_storage, db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    doc = _make_doc(db, tid)

    mock_storage.download_file.return_value = b"bytes"
    mock_ocr.extract_and_classify.return_value = (
        ExtractedDocument(
            raw_text="Devis montant ttc 450 EUR monture verres", page_count=1,
            extraction_method="pdfplumber", confidence=None,
        ),
        DocumentClassification(
            document_type="devis", confidence=0.88,
            keywords_found=["devis", "montant ttc", "monture"],
        ),
    )

    from app.services.extraction_service import extract_document

    result = extract_document(db, tid, doc.id)

    assert result.document_type == "devis"
    assert result.classification_confidence == 0.88


# ---------- 4. Unknown document type -> "autre" ----------

@patch("app.services.extraction_service.storage")
@patch("app.services.extraction_service.ocr_service")
@patch("app.services.extraction_service.parse_document", return_value=None)
def test_extract_unknown_type_returns_autre(mock_parse, mock_ocr, mock_storage, db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    doc = _make_doc(db, tid)

    mock_storage.download_file.return_value = b"bytes"
    mock_ocr.extract_and_classify.return_value = (
        ExtractedDocument(
            raw_text="Random text with no keywords", page_count=1,
            extraction_method="tesseract", confidence=0.6,
        ),
        DocumentClassification(
            document_type="autre", confidence=0.3, keywords_found=[],
        ),
    )

    from app.services.extraction_service import extract_document

    result = extract_document(db, tid, doc.id)

    assert result.document_type == "autre"
    assert result.structured_data is None


# ---------- 5. Extraction stored in database ----------

@patch("app.services.extraction_service.storage")
@patch("app.services.extraction_service.ocr_service")
@patch("app.services.extraction_service.parse_document", return_value=None)
def test_extraction_stored_in_database(mock_parse, mock_ocr, mock_storage, db: Session, default_tenant: Tenant) -> None:
    tid = default_tenant.id
    doc = _make_doc(db, tid)

    mock_storage.download_file.return_value = b"bytes"
    mock_ocr.extract_and_classify.return_value = (
        ExtractedDocument(
            raw_text="Some text", page_count=1,
            extraction_method="pdfplumber", confidence=None,
        ),
        DocumentClassification(
            document_type="facture", confidence=0.85, keywords_found=["facture"],
        ),
    )

    from app.services.extraction_service import extract_document

    result = extract_document(db, tid, doc.id)

    # Verify it was persisted
    stored = db.query(DocumentExtraction).filter_by(
        document_id=doc.id, tenant_id=tid,
    ).first()
    assert stored is not None
    assert stored.id == result.id
    assert stored.raw_text == "Some text"
    assert stored.document_type == "facture"

    # Calling again without force should return existing
    result2 = extract_document(db, tid, doc.id, force=False)
    assert result2.id == result.id
