"""Tests for OCR extraction, document classification, and specialized parsers.

All OCR dependencies (pytesseract, pdfplumber, pdf2image, PIL) are mocked
so tests run without Tesseract or Poppler installed.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.domain.schemas.ocr import DocumentClassification, ExtractedDocument
from app.services.ocr_service import classify_document, extract_and_classify
from app.services.parsers import parse_document
from app.services.parsers.attestation_mutuelle_parser import parse_attestation_mutuelle
from app.services.parsers.devis_parser import parse_devis
from app.services.parsers.facture_parser import parse_facture
from app.services.parsers.ordonnance_parser import parse_ordonnance


# =========================================================================
# Helper: create mock modules for OCR deps (used by lazy imports)
# =========================================================================


class _FakePdfContext:
    """Fake context manager returned by pdfplumber.open()."""

    def __init__(self, pages_text: list[str]) -> None:
        self.pages = []
        for txt in pages_text:
            p = MagicMock()
            p.extract_text.return_value = txt
            self.pages.append(p)

    def __enter__(self) -> "_FakePdfContext":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _make_pdfplumber_mock(pages_text: list[str]) -> MagicMock:
    """Build a mock pdfplumber module whose open() returns pages with given text."""
    mock_mod = MagicMock()
    mock_mod.open.return_value = _FakePdfContext(pages_text)
    return mock_mod


def _make_tesseract_mock(words: list[str], confs: list[str]) -> MagicMock:
    """Build a mock pytesseract module."""
    mock_mod = MagicMock()
    mock_mod.Output = MagicMock()
    mock_mod.Output.DICT = "dict"
    mock_mod.image_to_data.return_value = {"text": words, "conf": confs}
    return mock_mod


# =========================================================================
# PDF text extraction tests
# =========================================================================


class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf with mocked pdfplumber."""

    def test_native_pdf_extraction(self) -> None:
        """pdfplumber extracts enough text -> no OCR fallback."""
        text = "Ordonnance du Dr Martin ophtalmologue\nOD +2.50 (-0.75 a 90) Add +2.00\nOG +3.00 (-1.00 a 180) Add +2.25"
        mock_pdfplumber = _make_pdfplumber_mock([text])

        with patch.dict(sys.modules, {
            "pdfplumber": mock_pdfplumber,
            "pdf2image": MagicMock(),
            "pytesseract": MagicMock(),
        }):
            from app.services.ocr_service import extract_text_from_pdf

            result = extract_text_from_pdf(b"fake-pdf-bytes")

        assert isinstance(result, ExtractedDocument)
        assert result.extraction_method == "pdfplumber"
        assert result.page_count == 1
        assert "Ordonnance" in result.raw_text
        assert result.confidence is None

    def test_scanned_pdf_falls_back_to_ocr(self) -> None:
        """If pdfplumber yields little text, fall back to OCR."""
        mock_pdfplumber = _make_pdfplumber_mock([""])
        mock_tesseract = _make_tesseract_mock(
            ["Ordonnance", "Dr", "Martin", "OD", "+2.50"],
            ["90", "85", "88", "92", "87"],
        )
        mock_pdf2image = MagicMock()
        mock_pdf2image.convert_from_bytes.return_value = [MagicMock()]

        with patch.dict(sys.modules, {
            "pdfplumber": mock_pdfplumber,
            "pytesseract": mock_tesseract,
            "pdf2image": mock_pdf2image,
        }):
            from app.services.ocr_service import extract_text_from_pdf

            result = extract_text_from_pdf(b"fake-scanned-pdf")

        assert result.extraction_method == "pdfplumber+tesseract"
        assert result.page_count == 1
        assert result.confidence is not None
        assert result.confidence > 0

    def test_pdfplumber_exception_handled(self) -> None:
        """If pdfplumber raises an exception, falls back gracefully."""
        mock_pdfplumber = MagicMock()
        mock_pdfplumber.open.side_effect = Exception("corrupted PDF")

        mock_tesseract = _make_tesseract_mock([], [])
        mock_pdf2image = MagicMock()
        mock_pdf2image.convert_from_bytes.return_value = []

        with patch.dict(sys.modules, {
            "pdfplumber": mock_pdfplumber,
            "pytesseract": mock_tesseract,
            "pdf2image": mock_pdf2image,
        }):
            from app.services.ocr_service import extract_text_from_pdf

            result = extract_text_from_pdf(b"bad-pdf")
            assert isinstance(result, ExtractedDocument)


# =========================================================================
# Image extraction tests
# =========================================================================


class TestExtractTextFromImage:
    """Tests for extract_text_from_image with mocked PIL and pytesseract."""

    def test_image_ocr(self) -> None:
        mock_tesseract = _make_tesseract_mock(
            ["Carte", "Mutuelle", "N", "12345"],
            ["95", "90", "60", "85"],
        )
        mock_pil = MagicMock()
        mock_pil_image = MagicMock()
        mock_pil.open.return_value = mock_pil_image

        with patch.dict(sys.modules, {
            "pytesseract": mock_tesseract,
            "PIL": MagicMock(),
            "PIL.Image": mock_pil,
        }):
            from app.services.ocr_service import extract_text_from_image

            result = extract_text_from_image(b"fake-image-bytes")

        assert isinstance(result, ExtractedDocument)
        assert result.extraction_method == "tesseract"
        assert result.page_count == 1
        assert "Carte" in result.raw_text
        assert result.confidence is not None


# =========================================================================
# Document classification tests
# =========================================================================


class TestClassifyDocument:
    """Tests for regex-based document classification."""

    def test_classify_ordonnance(self) -> None:
        text = "Ordonnance medicale\nOD +2.50 (-0.75 a 90) Add +2.00\nOG +3.00"
        result = classify_document(text)

        assert isinstance(result, DocumentClassification)
        assert result.document_type == "ordonnance"
        assert result.confidence > 0
        assert len(result.keywords_found) > 0

    def test_classify_devis(self) -> None:
        text = "Devis n 2024-001\nMonture Ray-Ban 150,00 EUR\nVerres progressifs 450,00 EUR\nTotal TTC : 600,00 EUR\nPart Secu : 12,00 EUR\nReste a charge : 200,00 EUR"
        result = classify_document(text)

        assert result.document_type == "devis"
        assert result.confidence > 0

    def test_classify_attestation_mutuelle(self) -> None:
        text = "Attestation de droits\nMutuelle Generale\nNumero adherent: 123456\nDroits ouverts du 01/01/2024 au 31/12/2024\nOrganisme complementaire"
        result = classify_document(text)

        assert result.document_type == "attestation_mutuelle"
        assert result.confidence > 0

    def test_classify_facture(self) -> None:
        text = "Facture n FA-2024-0042\nDate: 15/03/2024\nMontant HT : 500,00 EUR\nTVA (20%) : 100,00 EUR\nMontant TTC : 600,00 EUR"
        result = classify_document(text)

        assert result.document_type == "facture"
        assert result.confidence > 0

    def test_classify_carte_mutuelle(self) -> None:
        text = "Carte de tiers payant\nCode organisme ABC123\nN adherent 789456"
        result = classify_document(text)

        assert result.document_type == "carte_mutuelle"
        assert result.confidence > 0

    def test_classify_empty_text(self) -> None:
        result = classify_document("")
        assert result.document_type == "autre"
        assert result.confidence == 0.0

    def test_classify_garbage_text(self) -> None:
        result = classify_document("xyzzy foobar random gibberish 12345")
        assert result.document_type == "autre"
        assert result.confidence == 0.0


# =========================================================================
# Ordonnance parser tests
# =========================================================================


class TestOrdonnanceParser:
    """Tests for optical prescription parsing."""

    def test_parse_od_og_inline(self) -> None:
        text = "OD : +2.50 (-0.75 a 90) Add +2.00\nOG : +3.00 (-1.00 a 180) Add +2.25"
        result = parse_ordonnance(text)

        assert result is not None
        assert result["od"] is not None
        assert result["od"]["sphere"] == 2.50
        assert result["od"]["cylinder"] == -0.75
        assert result["od"]["axis"] == 90
        assert result["od"]["addition"] == 2.00
        assert result["og"] is not None
        assert result["og"]["sphere"] == 3.00
        assert result["og"]["cylinder"] == -1.00
        assert result["og"]["axis"] == 180
        assert result["og"]["addition"] == 2.25

    def test_parse_comma_format(self) -> None:
        text = "OD +2,50 (-0,75) 90 Add 2,00"
        result = parse_ordonnance(text)

        assert result is not None
        assert result["od"]["sphere"] == 2.50
        assert result["od"]["cylinder"] == -0.75

    def test_parse_labeled_format(self) -> None:
        text = "OD Sph +1.25 Cyl -0.50 Axe 45 Add +1.50"
        result = parse_ordonnance(text)

        assert result is not None
        assert result["od"]["sphere"] == 1.25
        assert result["od"]["cylinder"] == -0.50
        assert result["od"]["axis"] == 45

    def test_parse_prescriber(self) -> None:
        text = "Dr Martin Dupont\nOD +2.50 (-0.75 a 90)"
        result = parse_ordonnance(text)

        assert result is not None
        assert result["prescriber"] is not None
        assert "Martin" in result["prescriber"]

    def test_parse_date(self) -> None:
        text = "Date: 15/03/2024\nOD +2.50 (-0.75 a 90)"
        result = parse_ordonnance(text)

        assert result is not None
        assert result["date"] == "15/03/2024"

    def test_parse_pupillary_distance(self) -> None:
        text = "OD +2.50 (-0.75 a 90)\nEcart pupillaire: 63 mm"
        result = parse_ordonnance(text)

        assert result is not None
        assert result["pupillary_distance"] == 63.0

    def test_parse_empty_text(self) -> None:
        assert parse_ordonnance("") is None
        assert parse_ordonnance("random text without any corrections") is None


# =========================================================================
# Devis parser tests
# =========================================================================


class TestDevisParser:
    """Tests for quote document parsing."""

    def test_parse_devis_full(self) -> None:
        text = (
            "Devis : DEV-2024-001\n"
            "Date: 15/03/2024\n"
            "Monture Ray-Ban 150,00 EUR\n"
            "Verres progressifs 450,00 EUR\n"
            "Total HT : 500,00 EUR\n"
            "Total TTC : 600,00 EUR\n"
            "Part Secu : 12,00 EUR\n"
            "Part Mutuelle : 388,00 EUR\n"
            "Reste a charge : 200,00 EUR"
        )
        result = parse_devis(text)

        assert result is not None
        assert result["numero_devis"] == "DEV-2024-001"
        assert result["date"] == "15/03/2024"
        assert result["montant_ht"] == 500.00
        assert result["montant_ttc"] == 600.00
        assert result["part_secu"] == 12.00
        assert result["part_mutuelle"] == 388.00
        assert result["reste_a_charge"] == 200.00
        assert len(result["line_items"]) >= 2

    def test_parse_devis_partial(self) -> None:
        text = "Devis : Q-42\nTotal TTC : 852,00 EUR"
        result = parse_devis(text)

        assert result is not None
        assert result["numero_devis"] == "Q-42"
        assert result["montant_ttc"] == 852.00

    def test_parse_devis_empty(self) -> None:
        assert parse_devis("") is None
        assert parse_devis("just some random text") is None


# =========================================================================
# Attestation mutuelle parser tests
# =========================================================================


class TestAttestationMutuelleParser:
    """Tests for mutual insurance attestation parsing."""

    def test_parse_attestation_full(self) -> None:
        text = (
            "Attestation de droits\n"
            "Mutuelle : Harmonie Mutuelle\n"
            "Code organisme : ABC123\n"
            "Numero adherent : 789456123\n"
            "Nom assure : Dupont\n"
            "Prenom : Jean\n"
            "Date debut : 01/01/2024\n"
            "Date fin : 31/12/2024"
        )
        result = parse_attestation_mutuelle(text)

        assert result is not None
        assert result["nom_mutuelle"] is not None
        assert "Harmonie" in result["nom_mutuelle"]
        assert result["code_organisme"] == "ABC123"
        assert result["numero_adherent"] == "789456123"
        assert result["nom_assure"] == "Dupont"
        assert result["prenom_assure"] == "Jean"
        assert result["date_debut_droits"] == "01/01/2024"
        assert result["date_fin_droits"] == "31/12/2024"

    def test_parse_attestation_partial(self) -> None:
        text = "Mutuelle Generale\nCode organisme : XY789"
        result = parse_attestation_mutuelle(text)

        assert result is not None
        assert result["code_organisme"] == "XY789"

    def test_parse_attestation_empty(self) -> None:
        assert parse_attestation_mutuelle("") is None
        assert parse_attestation_mutuelle("random stuff no relevant info here") is None


# =========================================================================
# Facture parser tests
# =========================================================================


class TestFactureParser:
    """Tests for invoice parsing."""

    def test_parse_facture_full(self) -> None:
        text = (
            "Facture : FA-2024-0042\n"
            "Date: 15/03/2024\n"
            "Montant HT : 500,00 EUR\n"
            "TVA (20%) : 100,00 EUR\n"
            "Montant TTC : 600,00 EUR"
        )
        result = parse_facture(text)

        assert result is not None
        assert result["numero_facture"] == "FA-2024-0042"
        assert result["date"] == "15/03/2024"
        assert result["montant_ht"] == 500.00
        assert result["tva"] == 100.00
        assert result["montant_ttc"] == 600.00

    def test_parse_facture_partial(self) -> None:
        text = "Facture : F-99\nTotal TTC : 1 234,56 EUR"
        result = parse_facture(text)

        assert result is not None
        assert result["numero_facture"] == "F-99"
        assert result["montant_ttc"] == 1234.56

    def test_parse_facture_empty(self) -> None:
        assert parse_facture("") is None


# =========================================================================
# Dispatcher tests
# =========================================================================


class TestParseDocumentDispatcher:
    """Tests for the parse_document dispatcher function."""

    def test_dispatch_ordonnance(self) -> None:
        text = "OD +2.50 (-0.75 a 90)"
        result = parse_document(text, "ordonnance")
        assert result is not None
        assert "od" in result

    def test_dispatch_unknown_type(self) -> None:
        result = parse_document("some text", "unknown_type")
        assert result is None

    def test_dispatch_autre_type(self) -> None:
        result = parse_document("some text", "autre")
        assert result is None


# =========================================================================
# extract_and_classify integration test
# =========================================================================


class TestExtractAndClassify:
    """Test the convenience function that combines extraction + classification."""

    def test_extract_and_classify_pdf(self) -> None:
        text = "Ordonnance du Dr Martin OD +2.50 OG +3.00 sphere cylindre addition" + " " * 50
        mock_pdfplumber = _make_pdfplumber_mock([text])

        with patch.dict(sys.modules, {"pdfplumber": mock_pdfplumber}):
            from app.services.ocr_service import extract_and_classify

            extracted, classification = extract_and_classify(b"fake-pdf", "prescription.pdf")

        assert isinstance(extracted, ExtractedDocument)
        assert isinstance(classification, DocumentClassification)
        assert classification.document_type == "ordonnance"

    def test_extract_and_classify_unsupported(self) -> None:
        extracted, classification = extract_and_classify(b"data", "file.docx")

        assert extracted.raw_text == ""
        assert extracted.extraction_method == "none"
        assert classification.document_type == "autre"
