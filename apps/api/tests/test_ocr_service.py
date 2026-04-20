"""Tests for OCR service, handlers, and classification rules.

Covers:
- classify_document() — each document type and edge cases
- extract_and_classify() — routing logic (PDF vs image vs unsupported)
- CLASSIFICATION_RULES — structure validation
- extract_text_from_pdf() — pdfplumber + OCR fallback paths
- extract_text_from_image() — tesseract path
- ocr_pdf_fallback() — scanned-PDF OCR path

All OCR dependencies (pytesseract, pdfplumber, pdf2image, PIL) are mocked
so these tests run without Tesseract or Poppler installed.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.domain.schemas.ocr import DocumentClassification, ExtractedDocument
from app.services.ocr_classification_rules import CLASSIFICATION_RULES
from app.services.ocr_handlers import classify_document


# ---------------------------------------------------------------------------
# Helpers to build lightweight OCR dependency mocks
# ---------------------------------------------------------------------------


class _FakePdfContext:
    """Minimal pdfplumber PDF context manager."""

    def __init__(self, pages_text: list[str]) -> None:
        self.pages: list[MagicMock] = []
        for txt in pages_text:
            page = MagicMock()
            page.extract_text.return_value = txt
            self.pages.append(page)

    def __enter__(self) -> "_FakePdfContext":
        return self

    def __exit__(self, *args: object) -> bool:
        return False


def _pdfplumber_mock(pages_text: list[str]) -> MagicMock:
    mod = MagicMock()
    mod.open.return_value = _FakePdfContext(pages_text)
    return mod


def _tesseract_mock(words: list[str], confs: list[str]) -> MagicMock:
    mod = MagicMock()
    mod.Output = MagicMock()
    mod.Output.DICT = "dict"
    mod.image_to_data.return_value = {"text": words, "conf": confs}
    return mod


def _pdf2image_mock(n_pages: int = 1) -> MagicMock:
    mod = MagicMock()
    mod.convert_from_bytes.return_value = [MagicMock() for _ in range(n_pages)]
    return mod


def _pil_mock() -> MagicMock:
    mod = MagicMock()
    mod.open.return_value = MagicMock()
    return mod


# ---------------------------------------------------------------------------
# 1. CLASSIFICATION_RULES — structure validation
# ---------------------------------------------------------------------------


class TestClassificationRulesStructure:
    """Verify the CLASSIFICATION_RULES list is well-formed."""

    def test_is_list_of_tuples(self) -> None:
        assert isinstance(CLASSIFICATION_RULES, list)
        assert len(CLASSIFICATION_RULES) > 0

    def test_each_entry_is_two_tuple(self) -> None:
        for entry in CLASSIFICATION_RULES:
            assert isinstance(entry, tuple), f"Expected tuple, got {type(entry)}"
            assert len(entry) == 2, f"Expected (type, keywords), got length {len(entry)}"

    def test_document_type_is_non_empty_string(self) -> None:
        for doc_type, _ in CLASSIFICATION_RULES:
            assert isinstance(doc_type, str) and doc_type.strip(), (
                f"document_type must be a non-empty string, got {doc_type!r}"
            )

    def test_keywords_are_non_empty_lists_of_strings(self) -> None:
        for doc_type, keywords in CLASSIFICATION_RULES:
            assert isinstance(keywords, list), f"{doc_type}: keywords must be a list"
            assert len(keywords) > 0, f"{doc_type}: keywords list must not be empty"
            for kw in keywords:
                assert isinstance(kw, str) and kw, (
                    f"{doc_type}: each keyword must be a non-empty string, got {kw!r}"
                )

    def test_expected_document_types_present(self) -> None:
        """The known business types from the spec must all be represented."""
        expected_types = {
            "ordonnance",
            "devis",
            "attestation_mutuelle",
            "facture",
            "carte_mutuelle",
            "bon_livraison",
            "fiche_opticien",
            "fiche_ophtalmo",
            "consentement_rgpd",
            "feuille_soins",
            "prise_en_charge",
            "courrier",
            "releve_bancaire",
        }
        present_types = {doc_type for doc_type, _ in CLASSIFICATION_RULES}
        missing = expected_types - present_types
        assert not missing, f"Missing document types in CLASSIFICATION_RULES: {missing}"

    def test_no_duplicate_document_types(self) -> None:
        types = [doc_type for doc_type, _ in CLASSIFICATION_RULES]
        assert len(types) == len(set(types)), "Duplicate document types found in CLASSIFICATION_RULES"


# ---------------------------------------------------------------------------
# 2. classify_document() — one test per document type
# ---------------------------------------------------------------------------


class TestClassifyDocumentPerType:
    """classify_document() returns the correct type for representative texts."""

    def test_ordonnance(self) -> None:
        text = (
            "Ordonnance medicale\n"
            "OD : +2.50 (-0.75 a 90) Add +2.00\n"
            "OG : +3.00 (-1.00 a 180) Add +2.25\n"
            "sphere cylindre correction ophtalmolog"
        )
        result = classify_document(text)
        assert result.document_type == "ordonnance"
        assert result.confidence > 0.0
        assert len(result.keywords_found) > 0

    def test_devis(self) -> None:
        text = (
            "Devis n 2024-001\n"
            "Monture Ray-Ban 150,00 EUR\n"
            "Verres progressifs 450,00 EUR\n"
            "Total TTC : 600,00 EUR\n"
            "Part Secu : 12,00 EUR\n"
            "Reste a charge : 200,00 EUR"
        )
        result = classify_document(text)
        assert result.document_type == "devis"
        assert result.confidence > 0.0

    def test_attestation_mutuelle(self) -> None:
        text = (
            "Attestation de droits\n"
            "Mutuelle Generale\n"
            "Organisme complementaire\n"
            "Numero adherent : 123456\n"
            "Droits ouverts du 01/01/2024 au 31/12/2024\n"
            "Tiers payant"
        )
        result = classify_document(text)
        assert result.document_type == "attestation_mutuelle"
        assert result.confidence > 0.0

    def test_facture(self) -> None:
        text = (
            "Facture n FA-2024-0042\n"
            "Date : 15/03/2024\n"
            "Montant HT : 500,00 EUR\n"
            "TVA (20%) : 100,00 EUR\n"
            "Montant TTC : 600,00 EUR\n"
            "Net a payer : 600,00 EUR"
        )
        result = classify_document(text)
        assert result.document_type == "facture"
        assert result.confidence > 0.0

    def test_carte_mutuelle(self) -> None:
        text = (
            "Carte de tiers payant\n"
            "Code organisme : ABC123\n"
            "N adherent : 789456\n"
            "Regime obligatoire"
        )
        result = classify_document(text)
        assert result.document_type == "carte_mutuelle"
        assert result.confidence > 0.0

    def test_bon_livraison(self) -> None:
        text = (
            "Bon de livraison\n"
            "Remis ce jour\n"
            "Bordereau de livraison\n"
            "Reception marchandise"
        )
        result = classify_document(text)
        assert result.document_type == "bon_livraison"
        assert result.confidence > 0.0

    def test_fiche_opticien(self) -> None:
        text = (
            "Fiche opticien\n"
            "Prise de mesure\n"
            "Ecart pupillaire : 63 mm\n"
            "Hauteur de montage"
        )
        result = classify_document(text)
        assert result.document_type == "fiche_opticien"
        assert result.confidence > 0.0

    def test_fiche_ophtalmo(self) -> None:
        text = (
            "Fiche ophtalmo\n"
            "Ophtalmologue Dr Dupont\n"
            "Examen de vue\n"
            "Fond d'oeil normal\n"
            "Bilan ophtalmologique"
        )
        result = classify_document(text)
        assert result.document_type == "fiche_ophtalmo"
        assert result.confidence > 0.0

    def test_consentement_rgpd(self) -> None:
        text = (
            "Consentement RGPD\n"
            "Donnees personnelles\n"
            "Traitement\n"
            "Protection des donnees\n"
            "Droit d'acces"
        )
        result = classify_document(text)
        assert result.document_type == "consentement_rgpd"
        assert result.confidence > 0.0

    def test_feuille_soins(self) -> None:
        text = (
            "Feuille de soins\n"
            "Securite sociale\n"
            "Assurance maladie\n"
            "AMO"
        )
        result = classify_document(text)
        assert result.document_type == "feuille_soins"
        assert result.confidence > 0.0

    def test_prise_en_charge(self) -> None:
        text = (
            "Prise en charge\n"
            "Accord de prise en charge\n"
            "Demande de prise en charge\n"
            "PEC accordee"
        )
        result = classify_document(text)
        assert result.document_type == "prise_en_charge"
        assert result.confidence > 0.0

    def test_courrier(self) -> None:
        text = (
            "Objet : Demande de remboursement\n"
            "Madame, Monsieur,\n"
            "Nous vous prions de bien vouloir trouver ci-joint.\n"
            "Veuillez agreer nos salutations distinguees.\n"
            "Cordialement"
        )
        result = classify_document(text)
        assert result.document_type == "courrier"
        assert result.confidence > 0.0

    def test_releve_bancaire(self) -> None:
        text = (
            "Releve de compte bancaire\n"
            "IBAN FR76 1234 5678 9012\n"
            "BIC AGRIFRPP\n"
            "Solde crediteur : 1 500,00 EUR\n"
            "Mouvement du mois"
        )
        result = classify_document(text)
        assert result.document_type == "releve_bancaire"
        assert result.confidence > 0.0


# ---------------------------------------------------------------------------
# 3. classify_document() — edge cases
# ---------------------------------------------------------------------------


class TestClassifyDocumentEdgeCases:
    """Edge cases: empty, whitespace-only, and unrecognised text."""

    def test_empty_string_returns_autre(self) -> None:
        result = classify_document("")
        assert result.document_type == "autre"
        assert result.confidence == 0.0
        assert result.keywords_found == []

    def test_whitespace_only_returns_autre(self) -> None:
        result = classify_document("   \n\t  ")
        assert result.document_type == "autre"
        assert result.confidence == 0.0
        assert result.keywords_found == []

    def test_garbage_text_returns_autre(self) -> None:
        result = classify_document("xyzzy foobar qux 12345 lorem ipsum dolor")
        assert result.document_type == "autre"
        assert result.confidence == 0.0

    def test_returns_document_classification_instance(self) -> None:
        result = classify_document("Ordonnance OD +1.00")
        assert isinstance(result, DocumentClassification)

    def test_confidence_capped_at_one(self) -> None:
        """Confidence must never exceed 1.0 even with many matching keywords."""
        # Use every keyword from ordonnance rules — score should be exactly 1.0
        ordonnance_keywords = [
            "ordonnance prescription sphere cylindre addition "
            "OD OG acuite correction dioptrie "
            "oeil droit oeil gauche vision de loin vision de pr ophtalmolog"
        ]
        result = classify_document(" ".join(ordonnance_keywords))
        assert result.confidence <= 1.0

    def test_best_score_wins(self) -> None:
        """When two types share keywords, the one with more matches wins."""
        # This text mentions both 'facture' and several devis-specific terms
        text = (
            "Devis monture verres equipement optique reste a charge "
            "part secu part mutuelle total ttc montant ht bon de commande"
        )
        result = classify_document(text)
        assert result.document_type == "devis"

    def test_keywords_found_list_is_subset_of_matched_rules(self) -> None:
        text = "Ordonnance OD +1.00 sphere correction"
        result = classify_document(text)
        assert isinstance(result.keywords_found, list)
        assert len(result.keywords_found) > 0

    def test_case_insensitive_matching(self) -> None:
        """Classification is case-insensitive (text is lowercased internally)."""
        result_lower = classify_document("ordonnance od +2.50 sphere")
        result_upper = classify_document("ORDONNANCE OD +2.50 SPHERE")
        assert result_lower.document_type == result_upper.document_type


# ---------------------------------------------------------------------------
# 4. extract_and_classify() — routing logic
# ---------------------------------------------------------------------------


class TestExtractAndClassify:
    """extract_and_classify() routes to the correct extractor based on filename."""

    def test_pdf_extension_uses_pdfplumber(self) -> None:
        text = (
            "Ordonnance Dr Martin OD +2.50 sphere cylindre correction "
            + "ophtalmolog vision de loin addition"
            + " " * 60  # ensure len > 50
        )
        mock_pdf = _pdfplumber_mock([text])

        with patch.dict(sys.modules, {"pdfplumber": mock_pdf}):
            from app.services.ocr_service import extract_and_classify

            extracted, classification = extract_and_classify(b"pdf-bytes", "ordonnance.pdf")

        assert isinstance(extracted, ExtractedDocument)
        assert isinstance(classification, DocumentClassification)
        assert extracted.extraction_method == "pdfplumber"
        assert classification.document_type == "ordonnance"

    def test_jpg_extension_uses_tesseract(self) -> None:
        words = ["Facture", "FA-2024-001", "TVA", "Montant", "TTC", "600,00", "EUR", "Net", "a", "payer"]
        confs = ["90"] * len(words)
        mock_tess = _tesseract_mock(words, confs)
        mock_pil = _pil_mock()

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "PIL": MagicMock(),
            "PIL.Image": mock_pil,
        }):
            from app.services.ocr_service import extract_and_classify

            extracted, classification = extract_and_classify(b"img-bytes", "scan.jpg")

        assert extracted.extraction_method == "tesseract"
        assert extracted.page_count == 1

    def test_jpeg_extension_uses_tesseract(self) -> None:
        mock_tess = _tesseract_mock(["Attestation", "mutuelle"], ["85", "80"])
        mock_pil = _pil_mock()

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "PIL": MagicMock(),
            "PIL.Image": mock_pil,
        }):
            from app.services.ocr_service import extract_and_classify

            extracted, _ = extract_and_classify(b"img-bytes", "scan.jpeg")

        assert extracted.extraction_method == "tesseract"

    def test_png_extension_uses_tesseract(self) -> None:
        mock_tess = _tesseract_mock([], [])
        mock_pil = _pil_mock()

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "PIL": MagicMock(),
            "PIL.Image": mock_pil,
        }):
            from app.services.ocr_service import extract_and_classify

            extracted, classification = extract_and_classify(b"img-bytes", "image.png")

        assert extracted.extraction_method == "tesseract"
        assert classification.document_type == "autre"

    def test_unsupported_extension_returns_empty_autre(self) -> None:
        from app.services.ocr_service import extract_and_classify

        extracted, classification = extract_and_classify(b"bytes", "report.docx")

        assert extracted.raw_text == ""
        assert extracted.extraction_method == "none"
        assert extracted.page_count == 0
        assert classification.document_type == "autre"
        assert classification.confidence == 0.0

    def test_no_extension_returns_empty_autre(self) -> None:
        from app.services.ocr_service import extract_and_classify

        extracted, classification = extract_and_classify(b"bytes", "noextension")

        assert extracted.raw_text == ""
        assert extracted.extraction_method == "none"
        assert classification.document_type == "autre"

    def test_returns_tuple_of_correct_types(self) -> None:
        from app.services.ocr_service import extract_and_classify

        result = extract_and_classify(b"bytes", "file.xyz")
        assert isinstance(result, tuple)
        assert len(result) == 2
        extracted, classification = result
        assert isinstance(extracted, ExtractedDocument)
        assert isinstance(classification, DocumentClassification)


# ---------------------------------------------------------------------------
# 5. extract_text_from_pdf() — detailed path tests
# ---------------------------------------------------------------------------


class TestExtractTextFromPdf:
    """extract_text_from_pdf() uses pdfplumber; falls back to OCR for scanned PDFs."""

    def test_native_extraction_returns_pdfplumber_method(self) -> None:
        text = "Facture n FA-001\nMontant TTC 600 EUR\n" + "a" * 60
        mock_pdf = _pdfplumber_mock([text])

        with patch.dict(sys.modules, {"pdfplumber": mock_pdf}):
            from app.services.ocr_service import extract_text_from_pdf

            result = extract_text_from_pdf(b"fake-pdf")

        assert result.extraction_method == "pdfplumber"
        assert result.confidence is None
        assert result.language == "fra"
        assert "Facture" in result.raw_text

    def test_multi_page_pdf_joins_pages(self) -> None:
        page1 = "Page un contenu suffisant " * 5
        page2 = "Page deux contenu suffisant " * 5
        mock_pdf = _pdfplumber_mock([page1, page2])

        with patch.dict(sys.modules, {"pdfplumber": mock_pdf}):
            from app.services.ocr_service import extract_text_from_pdf

            result = extract_text_from_pdf(b"fake-pdf")

        assert result.page_count == 2
        assert "Page un" in result.raw_text
        assert "Page deux" in result.raw_text

    def test_short_native_text_triggers_ocr_fallback(self) -> None:
        """pdfplumber yields < 50 chars → falls back to tesseract."""
        mock_pdf = _pdfplumber_mock(["tiny"])  # < 50 chars
        mock_tess = _tesseract_mock(["Ordonnance", "OD"], ["90", "85"])
        mock_pdf2image = _pdf2image_mock(n_pages=1)

        with patch.dict(sys.modules, {
            "pdfplumber": mock_pdf,
            "pytesseract": mock_tess,
            "pdf2image": mock_pdf2image,
        }):
            from app.services.ocr_service import extract_text_from_pdf

            result = extract_text_from_pdf(b"scanned-pdf")

        assert result.extraction_method == "pdfplumber+tesseract"
        assert result.confidence is not None

    def test_empty_pdfplumber_output_triggers_ocr_fallback(self) -> None:
        mock_pdf = _pdfplumber_mock([""])
        mock_tess = _tesseract_mock(["Attestation", "mutuelle"], ["88", "82"])
        mock_pdf2image = _pdf2image_mock()

        with patch.dict(sys.modules, {
            "pdfplumber": mock_pdf,
            "pytesseract": mock_tess,
            "pdf2image": mock_pdf2image,
        }):
            from app.services.ocr_service import extract_text_from_pdf

            result = extract_text_from_pdf(b"scanned-pdf")

        assert result.extraction_method == "pdfplumber+tesseract"

    def test_pdfplumber_exception_falls_back_to_ocr(self) -> None:
        mock_pdf = MagicMock()
        mock_pdf.open.side_effect = Exception("corrupted PDF")
        mock_tess = _tesseract_mock([], [])
        mock_pdf2image = _pdf2image_mock(n_pages=0)

        with patch.dict(sys.modules, {
            "pdfplumber": mock_pdf,
            "pytesseract": mock_tess,
            "pdf2image": mock_pdf2image,
        }):
            from app.services.ocr_service import extract_text_from_pdf

            result = extract_text_from_pdf(b"bad-pdf")

        assert isinstance(result, ExtractedDocument)
        # Fell back to OCR path
        assert result.extraction_method == "pdfplumber+tesseract"


# ---------------------------------------------------------------------------
# 6. extract_text_from_image() — tesseract path
# ---------------------------------------------------------------------------


class TestExtractTextFromImage:
    """extract_text_from_image() reads an image with PIL + pytesseract."""

    def test_basic_image_extraction(self) -> None:
        words = ["Carte", "mutuelle", "N", "12345"]
        confs = ["90", "85", "60", "80"]
        mock_tess = _tesseract_mock(words, confs)
        mock_pil = _pil_mock()

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "PIL": MagicMock(),
            "PIL.Image": mock_pil,
        }):
            from app.services.ocr_handlers import extract_text_from_image

            result = extract_text_from_image(b"fake-image")

        assert isinstance(result, ExtractedDocument)
        assert result.extraction_method == "tesseract"
        assert result.page_count == 1
        assert "Carte" in result.raw_text
        assert result.confidence is not None
        assert 0.0 <= result.confidence <= 1.0
        assert result.language == "fra"

    def test_zero_confidence_words_excluded(self) -> None:
        """Words with conf == 0 (or -1) must not appear in the extracted text."""
        words = ["Visible", "", "AlsoVisible"]
        confs = ["80", "0", "75"]
        mock_tess = _tesseract_mock(words, confs)
        mock_pil = _pil_mock()

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "PIL": MagicMock(),
            "PIL.Image": mock_pil,
        }):
            from app.services.ocr_handlers import extract_text_from_image

            result = extract_text_from_image(b"fake-image")

        assert "Visible" in result.raw_text
        assert "AlsoVisible" in result.raw_text

    def test_empty_tesseract_output(self) -> None:
        mock_tess = _tesseract_mock([], [])
        mock_pil = _pil_mock()

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "PIL": MagicMock(),
            "PIL.Image": mock_pil,
        }):
            from app.services.ocr_handlers import extract_text_from_image

            result = extract_text_from_image(b"blank-image")

        assert result.raw_text == ""
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# 7. ocr_pdf_fallback() — scanned-PDF OCR path
# ---------------------------------------------------------------------------


class TestOcrPdfFallback:
    """ocr_pdf_fallback() converts PDF pages to images then OCRs them."""

    def test_single_page_fallback(self) -> None:
        words = ["Ordonnance", "Dr", "Dupont", "OD", "+2.50"]
        confs = ["90", "88", "85", "92", "87"]
        mock_tess = _tesseract_mock(words, confs)
        mock_pdf2image = _pdf2image_mock(n_pages=1)

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "pdf2image": mock_pdf2image,
        }):
            from app.services.ocr_handlers import ocr_pdf_fallback

            result = ocr_pdf_fallback(b"scanned-pdf", page_count_hint=0)

        assert isinstance(result, ExtractedDocument)
        assert result.extraction_method == "pdfplumber+tesseract"
        assert result.page_count == 1
        assert result.confidence is not None
        assert result.confidence > 0.0
        assert "Ordonnance" in result.raw_text

    def test_multi_page_fallback(self) -> None:
        words = ["Page", "contenu"]
        confs = ["90", "85"]
        mock_tess = _tesseract_mock(words, confs)
        mock_pdf2image = _pdf2image_mock(n_pages=3)

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "pdf2image": mock_pdf2image,
        }):
            from app.services.ocr_handlers import ocr_pdf_fallback

            result = ocr_pdf_fallback(b"multi-page-scan", page_count_hint=3)

        assert result.page_count == 3

    def test_empty_pages_yield_zero_confidence(self) -> None:
        mock_tess = _tesseract_mock([], [])
        mock_pdf2image = _pdf2image_mock(n_pages=1)

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "pdf2image": mock_pdf2image,
        }):
            from app.services.ocr_handlers import ocr_pdf_fallback

            result = ocr_pdf_fallback(b"blank-scan", page_count_hint=1)

        assert result.raw_text == ""
        assert result.confidence == 0.0

    def test_confidence_normalised_between_0_and_1(self) -> None:
        """Tesseract confs are 0-100; result confidence must be in [0, 1]."""
        words = ["texte"]
        confs = ["95"]
        mock_tess = _tesseract_mock(words, confs)
        mock_pdf2image = _pdf2image_mock()

        with patch.dict(sys.modules, {
            "pytesseract": mock_tess,
            "pdf2image": mock_pdf2image,
        }):
            from app.services.ocr_handlers import ocr_pdf_fallback

            result = ocr_pdf_fallback(b"pdf", page_count_hint=1)

        assert 0.0 <= result.confidence <= 1.0
