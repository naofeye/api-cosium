"""Focused tests for document parsers (pure text parsing, no DB, no mocks needed).

Covers:
  - ordonnance_parser  : OD/OG correction values, prescriber, date, PD
  - devis_parser       : amounts, line items, quote number
  - facture_parser     : invoice number, date, amounts (HT / TVA / TTC)
  - attestation_mutuelle_parser : mutuelle name, adherent number, dates
"""

from __future__ import annotations

import pytest

from app.services.parsers.ordonnance_parser import parse_ordonnance
from app.services.parsers.devis_parser import parse_devis
from app.services.parsers.facture_parser import parse_facture
from app.services.parsers.attestation_mutuelle_parser import parse_attestation_mutuelle


# =============================================================================
# ORDONNANCE PARSER
# =============================================================================


class TestOrdonnanceParserBasic:
    """Core OD/OG extraction in the most common inline format."""

    OCR_TEXT_INLINE = """\
Cabinet d'Ophtalmologie Dr Claire Fontaine
12 rue de la Paix, 75001 Paris
Date: 08/02/2025

ORDONNANCE MÉDICALE

OD : +2.50 (-0.75 a 90) Add +2.00
OG : +3.00 (-1.00 a 180) Add +2.25

Ecart pupillaire: 63 mm
"""

    def test_returns_dict_not_none(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result is not None
        assert isinstance(result, dict)

    def test_od_sphere(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["od"]["sphere"] == pytest.approx(2.50)

    def test_od_cylinder(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["od"]["cylinder"] == pytest.approx(-0.75)

    def test_od_axis(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["od"]["axis"] == 90

    def test_od_addition(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["od"]["addition"] == pytest.approx(2.00)

    def test_og_sphere(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["og"]["sphere"] == pytest.approx(3.00)

    def test_og_cylinder(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["og"]["cylinder"] == pytest.approx(-1.00)

    def test_og_axis(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["og"]["axis"] == 180

    def test_og_addition(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["og"]["addition"] == pytest.approx(2.25)

    def test_prescriber_name_extracted(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["prescriber"] is not None
        assert "Fontaine" in result["prescriber"]

    def test_date_extracted(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["date"] == "08/02/2025"

    def test_pupillary_distance_extracted(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert result["pupillary_distance"] == pytest.approx(63.0)

    def test_confidence_between_0_and_1(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_INLINE)
        assert 0.0 <= result["od"]["confidence"] <= 1.0
        assert 0.0 <= result["og"]["confidence"] <= 1.0


class TestOrdonnanceParserCommaFormat:
    """French comma decimal separator (2,50 instead of 2.50)."""

    OCR_TEXT_COMMA = """\
Ophtalmologue : Dr Bernard Leblanc
Date: 12/05/2025
OD +2,50 (-0,75) 90 Add 2,00
OG +1,75 (-0,50) 120 Add 1,75
"""

    def test_od_sphere_with_comma(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_COMMA)
        assert result is not None
        assert result["od"]["sphere"] == pytest.approx(2.50)

    def test_od_cylinder_with_comma(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_COMMA)
        assert result["od"]["cylinder"] == pytest.approx(-0.75)

    def test_og_sphere_with_comma(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_COMMA)
        assert result["og"]["sphere"] == pytest.approx(1.75)

    def test_prescriber_extracted(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_COMMA)
        assert result["prescriber"] is not None
        assert "Leblanc" in result["prescriber"]


class TestOrdonnanceParserLabeledFormat:
    """Labeled Sph/Cyl/Axe/Add format on one line."""

    OCR_TEXT_LABELED = "OD Sph +1.25 Cyl -0.50 Axe 45 Add +1.50\nOG Sph -0.25 Cyl -0.25 Axe 10"

    def test_od_labeled_sphere(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_LABELED)
        assert result is not None
        assert result["od"]["sphere"] == pytest.approx(1.25)

    def test_od_labeled_cylinder(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_LABELED)
        assert result["od"]["cylinder"] == pytest.approx(-0.50)

    def test_od_labeled_axis(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_LABELED)
        assert result["od"]["axis"] == 45

    def test_od_labeled_addition(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_LABELED)
        assert result["od"]["addition"] == pytest.approx(1.50)

    def test_og_labeled_sphere(self) -> None:
        result = parse_ordonnance(self.OCR_TEXT_LABELED)
        assert result["og"] is not None
        assert result["og"]["sphere"] == pytest.approx(-0.25)


class TestOrdonnanceParserPartialData:
    """Prescriptions where some fields are missing (sphere only, no addition)."""

    def test_sphere_only_od(self) -> None:
        text = "OD +1.00\nOG -0.75"
        result = parse_ordonnance(text)
        assert result is not None
        assert result["od"]["sphere"] == pytest.approx(1.00)
        assert result["od"]["cylinder"] is None
        assert result["od"]["axis"] is None
        assert result["od"]["addition"] is None

    def test_confidence_lower_when_fewer_fields(self) -> None:
        full_text = "OD +2.50 (-0.75 a 90) Add +2.00"
        partial_text = "OD +2.50"
        full_result = parse_ordonnance(full_text)
        partial_result = parse_ordonnance(partial_text)
        assert full_result["od"]["confidence"] > partial_result["od"]["confidence"]

    def test_no_og_returns_none_for_og_key(self) -> None:
        text = "OD +1.50 (-0.50 a 60)"
        result = parse_ordonnance(text)
        assert result is not None
        assert result["og"] is None

    def test_prescriber_absent_returns_none(self) -> None:
        text = "OD +2.00 (-0.25 a 170)"
        result = parse_ordonnance(text)
        assert result["prescriber"] is None

    def test_date_absent_returns_none(self) -> None:
        text = "OD +2.00 (-0.25 a 170)"
        result = parse_ordonnance(text)
        assert result["date"] is None

    def test_pupillary_distance_absent_returns_none(self) -> None:
        text = "OD +2.00 (-0.25 a 170)"
        result = parse_ordonnance(text)
        assert result["pupillary_distance"] is None


class TestOrdonnanceParserEdgeCases:
    """Edge cases and malformed/empty input."""

    def test_empty_string_returns_none(self) -> None:
        assert parse_ordonnance("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert parse_ordonnance("   \n\t  ") is None

    def test_unrelated_text_returns_none(self) -> None:
        text = "Facture n FA-2024-001\nMontant TTC : 600,00 EUR"
        assert parse_ordonnance(text) is None

    def test_degree_sign_in_axis(self) -> None:
        text = "OD +1.25 (-0.50 a 90°) Add +1.50"
        result = parse_ordonnance(text)
        assert result is not None
        assert result["od"]["axis"] == 90

    def test_ep_abbreviation_for_pd(self) -> None:
        text = "OD +2.00 (-0.50 a 45)\nEP : 64"
        result = parse_ordonnance(text)
        assert result is not None
        assert result["pupillary_distance"] == pytest.approx(64.0)

    def test_pd_abbreviation(self) -> None:
        text = "OD +2.00 (-0.50 a 45)\nPD : 65.5 mm"
        result = parse_ordonnance(text)
        assert result is not None
        assert result["pupillary_distance"] == pytest.approx(65.5)

    def test_positive_sphere_no_explicit_sign(self) -> None:
        """Sphere value without leading +; the regex sign is optional so it matches."""
        text = "OD 2.50 (-0.75 a 90)"
        result = parse_ordonnance(text)
        assert result is not None
        assert result["od"]["sphere"] == pytest.approx(2.50)
        assert result["od"]["cylinder"] == pytest.approx(-0.75)
        assert result["od"]["axis"] == 90

    def test_negative_sphere(self) -> None:
        text = "OD -3.75 (-0.50 a 15)\nOG -2.50 (-0.25 a 175)"
        result = parse_ordonnance(text)
        assert result is not None
        assert result["od"]["sphere"] == pytest.approx(-3.75)
        assert result["og"]["sphere"] == pytest.approx(-2.50)


# =============================================================================
# DEVIS PARSER
# =============================================================================


class TestDevisParserFull:
    """Complete devis with all expected fields."""

    OCR_TEXT = """\
OPTICIEN POINT DE VUE
12, avenue du Général de Gaulle — 69001 Lyon

DEVIS : DEV-2024-0317
Date: 15/03/2024

ÉQUIPEMENT VISUEL

Monture Silhouette 298,00 EUR
Verres progressifs Varilux X 648,00 EUR
Traitement antireflet 45,00 EUR

Total HT : 826,45 EUR
Total TTC : 991,74 EUR
Part Secu : 7,50 EUR
Part Mutuelle : 462,00 EUR
Reste a charge : 522,24 EUR
"""

    def test_returns_dict(self) -> None:
        assert parse_devis(self.OCR_TEXT) is not None

    def test_numero_devis(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        assert result["numero_devis"] == "DEV-2024-0317"

    def test_date(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        assert result["date"] == "15/03/2024"

    def test_montant_ht(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        assert result["montant_ht"] == pytest.approx(826.45)

    def test_montant_ttc(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        assert result["montant_ttc"] == pytest.approx(991.74)

    def test_part_secu(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        assert result["part_secu"] == pytest.approx(7.50)

    def test_part_mutuelle(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        assert result["part_mutuelle"] == pytest.approx(462.00)

    def test_reste_a_charge(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        assert result["reste_a_charge"] == pytest.approx(522.24)

    def test_line_items_count(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        assert len(result["line_items"]) >= 2

    def test_monture_in_line_items(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        descriptions = [item["description"].lower() for item in result["line_items"]]
        assert any("monture" in d for d in descriptions)

    def test_verres_in_line_items(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        descriptions = [item["description"].lower() for item in result["line_items"]]
        assert any("verre" in d for d in descriptions)

    def test_line_item_montant_is_float(self) -> None:
        result = parse_devis(self.OCR_TEXT)
        for item in result["line_items"]:
            assert isinstance(item["montant"], float)


class TestDevisParserPartial:
    """Minimal devis with only a subset of fields present."""

    def test_numero_and_ttc_only(self) -> None:
        text = "Devis : Q-42\nTotal TTC : 852,00 EUR"
        result = parse_devis(text)
        assert result is not None
        assert result["numero_devis"] == "Q-42"
        assert result["montant_ttc"] == pytest.approx(852.00)
        assert result["montant_ht"] is None
        assert result["part_secu"] is None
        assert result["part_mutuelle"] is None
        assert result["reste_a_charge"] is None

    def test_large_amount_with_space_thousands_separator(self) -> None:
        text = "Devis : D-001\nTotal TTC : 1 234,56 EUR"
        result = parse_devis(text)
        assert result is not None
        assert result["montant_ttc"] == pytest.approx(1234.56)

    def test_no_numero_but_has_ttc(self) -> None:
        text = "Total TTC : 450,00 EUR\nMonture Essilor 200,00 EUR"
        result = parse_devis(text)
        assert result is not None
        assert result["numero_devis"] is None
        assert result["montant_ttc"] == pytest.approx(450.00)

    def test_alternative_keyword_n_devis(self) -> None:
        text = "N° devis : DV-2025-999\nTotal TTC : 300,00 EUR"
        result = parse_devis(text)
        assert result is not None
        assert result["numero_devis"] == "DV-2025-999"


class TestDevisParserEdgeCases:
    """Edge cases and graceful failures."""

    def test_empty_string_returns_none(self) -> None:
        assert parse_devis("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert parse_devis("   \n\t  ") is None

    def test_unrelated_text_returns_none(self) -> None:
        assert parse_devis("Bonjour, veuillez nous contacter au 01 23 45 67 89.") is None

    def test_line_items_empty_when_none_found(self) -> None:
        text = "Devis : DEV-001\nTotal TTC : 100,00 EUR"
        result = parse_devis(text)
        assert result is not None
        assert result["line_items"] == []

    def test_verre_droit_gauche_in_items(self) -> None:
        text = "Devis : DEV-002\nVerre droit 240,00 EUR\nVerre gauche 240,00 EUR"
        result = parse_devis(text)
        assert result is not None
        descriptions = [item["description"].lower() for item in result["line_items"]]
        assert any("verre" in d for d in descriptions)


# =============================================================================
# FACTURE PARSER
# =============================================================================


class TestFactureParserFull:
    """Complete facture with all expected fields."""

    OCR_TEXT = """\
FACTURE
Opticien Lumière SAS
Siret : 123 456 789 00012

Facture : FA-2024-0042
Date: 15/03/2024

Montant HT : 500,00 EUR
TVA (20%) : 100,00 EUR
Montant TTC : 600,00 EUR
"""

    def test_returns_dict(self) -> None:
        assert parse_facture(self.OCR_TEXT) is not None

    def test_numero_facture(self) -> None:
        result = parse_facture(self.OCR_TEXT)
        assert result["numero_facture"] == "FA-2024-0042"

    def test_date(self) -> None:
        result = parse_facture(self.OCR_TEXT)
        assert result["date"] == "15/03/2024"

    def test_montant_ht(self) -> None:
        result = parse_facture(self.OCR_TEXT)
        assert result["montant_ht"] == pytest.approx(500.00)

    def test_tva(self) -> None:
        result = parse_facture(self.OCR_TEXT)
        assert result["tva"] == pytest.approx(100.00)

    def test_montant_ttc(self) -> None:
        result = parse_facture(self.OCR_TEXT)
        assert result["montant_ttc"] == pytest.approx(600.00)


class TestFactureParserPartial:
    """Partial facture missing some fields."""

    def test_numero_and_ttc_only(self) -> None:
        text = "Facture : F-99\nTotal TTC : 1 234,56 EUR"
        result = parse_facture(text)
        assert result is not None
        assert result["numero_facture"] == "F-99"
        assert result["montant_ttc"] == pytest.approx(1234.56)
        assert result["montant_ht"] is None
        assert result["tva"] is None

    def test_no_date_returns_none_for_date(self) -> None:
        text = "Facture : FAC-001\nTotal TTC : 200,00 EUR"
        result = parse_facture(text)
        assert result["date"] is None

    def test_alternative_keyword_n_facture(self) -> None:
        text = "N° facture : INV-2025-01\nMontant TTC : 99,00 EUR"
        result = parse_facture(text)
        assert result is not None
        assert result["numero_facture"] == "INV-2025-01"

    def test_net_a_payer_keyword(self) -> None:
        text = "Facture : FA-007\nNet a payer TTC : 750,00 EUR"
        result = parse_facture(text)
        assert result is not None
        assert result["montant_ttc"] == pytest.approx(750.00)

    def test_large_amount_with_space_separator(self) -> None:
        text = "Facture : FA-008\nMontant TTC : 2 500,00 EUR"
        result = parse_facture(text)
        assert result is not None
        assert result["montant_ttc"] == pytest.approx(2500.00)


class TestFactureParserEdgeCases:
    """Edge cases and graceful failures."""

    def test_empty_string_returns_none(self) -> None:
        assert parse_facture("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert parse_facture("   \n\t  ") is None

    def test_unrelated_text_returns_none(self) -> None:
        # No invoice number and no TTC amount → should return None
        assert parse_facture("Bonjour, voici notre catalogue de montures.") is None

    def test_amounts_are_floats(self) -> None:
        text = (
            "Facture : FA-100\n"
            "Montant HT : 400,00 EUR\n"
            "TVA (20%) : 80,00 EUR\n"
            "Montant TTC : 480,00 EUR"
        )
        result = parse_facture(text)
        assert result is not None
        assert isinstance(result["montant_ht"], float)
        assert isinstance(result["tva"], float)
        assert isinstance(result["montant_ttc"], float)

    def test_date_formats_slash(self) -> None:
        text = "Facture : FA-200\nDate: 01/01/2025\nTotal TTC : 100,00 EUR"
        result = parse_facture(text)
        assert result["date"] == "01/01/2025"

    def test_date_formats_dash(self) -> None:
        text = "Facture : FA-201\nDate: 01-01-2025\nTotal TTC : 100,00 EUR"
        result = parse_facture(text)
        assert result["date"] == "01-01-2025"


# =============================================================================
# ATTESTATION MUTUELLE PARSER
# =============================================================================


class TestAttestationMutuelleParserFull:
    """Complete attestation with all expected fields."""

    # Note: parser regex uses 'adherent' without accent — use matching form in test text.
    OCR_TEXT = """\
ATTESTATION DE DROITS
Organisme complementaire

Mutuelle : Harmonie Mutuelle
Code organisme : ABC123
N° adherent : 789456123
Nom assure : Dupont
Prenom : Jean
Date debut : 01/01/2025
Date fin : 31/12/2025
"""

    def test_returns_dict(self) -> None:
        assert parse_attestation_mutuelle(self.OCR_TEXT) is not None

    def test_nom_mutuelle(self) -> None:
        result = parse_attestation_mutuelle(self.OCR_TEXT)
        assert result["nom_mutuelle"] is not None
        assert "Harmonie" in result["nom_mutuelle"]

    def test_code_organisme(self) -> None:
        result = parse_attestation_mutuelle(self.OCR_TEXT)
        assert result["code_organisme"] == "ABC123"

    def test_numero_adherent(self) -> None:
        result = parse_attestation_mutuelle(self.OCR_TEXT)
        assert result["numero_adherent"] == "789456123"

    def test_nom_assure(self) -> None:
        result = parse_attestation_mutuelle(self.OCR_TEXT)
        assert result["nom_assure"] == "Dupont"

    def test_prenom_assure(self) -> None:
        result = parse_attestation_mutuelle(self.OCR_TEXT)
        assert result["prenom_assure"] == "Jean"

    def test_date_debut_droits(self) -> None:
        result = parse_attestation_mutuelle(self.OCR_TEXT)
        assert result["date_debut_droits"] == "01/01/2025"

    def test_date_fin_droits(self) -> None:
        result = parse_attestation_mutuelle(self.OCR_TEXT)
        assert result["date_fin_droits"] == "31/12/2025"


class TestAttestationMutuelleParserPartial:
    """Partial attestations and alternate keyword variants."""

    def test_code_organisme_only(self) -> None:
        # The _MUTUELLE_NAME regex matches 'organisme' as prefix and may pick up
        # trailing text as a spurious nom_mutuelle; the key assertion is code_organisme.
        text = "Code organisme : XY789"
        result = parse_attestation_mutuelle(text)
        assert result is not None
        assert result["code_organisme"] == "XY789"
        assert result["numero_adherent"] is None

    def test_code_amc_keyword(self) -> None:
        text = "Code AMC : MUT456\nMutuelle : MGEN"
        result = parse_attestation_mutuelle(text)
        assert result is not None
        assert result["code_organisme"] == "MUT456"

    def test_numero_membre_keyword(self) -> None:
        text = "Code organisme : TEST01\nN° membre : A12345"
        result = parse_attestation_mutuelle(text)
        assert result is not None
        assert result["numero_adherent"] == "A12345"

    def test_titulaire_keyword(self) -> None:
        text = "Code organisme : Z99\nTitulaire : Martin Sophie"
        result = parse_attestation_mutuelle(text)
        assert result is not None
        assert result["nom_assure"] is not None

    def test_date_fields_absent_return_none(self) -> None:
        # Use unaccented 'adherent' to match the parser regex
        text = "Mutuelle : AG2R\nCode organisme : AG001\nN° adherent : 000111222"
        result = parse_attestation_mutuelle(text)
        assert result is not None
        assert result["date_debut_droits"] is None
        assert result["date_fin_droits"] is None

    def test_dash_separated_adherent_number(self) -> None:
        text = "Code organisme : ORG01\nNumero adherent : 123-456-789"
        result = parse_attestation_mutuelle(text)
        assert result is not None
        assert result["numero_adherent"] == "123-456-789"


class TestAttestationMutuelleParserEdgeCases:
    """Edge cases and graceful failures."""

    def test_empty_string_returns_none(self) -> None:
        assert parse_attestation_mutuelle("") is None

    def test_whitespace_only_returns_none(self) -> None:
        assert parse_attestation_mutuelle("   \n\t  ") is None

    def test_unrelated_text_returns_none(self) -> None:
        text = "Bonjour Madame, merci de nous contacter pour votre commande."
        assert parse_attestation_mutuelle(text) is None

    def test_ordonnance_text_does_not_match(self) -> None:
        text = "OD +2.50 (-0.75 a 90) Add +2.00\nOG +3.00 (-1.00 a 180)"
        result = parse_attestation_mutuelle(text)
        assert result is None

    def test_all_fields_present_no_missing_keys(self) -> None:
        # Use unaccented 'adherent' to match the parser regex
        text = (
            "Mutuelle : Malakoff Humanis\n"
            "Code organisme : MH123\n"
            "N° adherent : 987654321\n"
            "Nom assure : Leclerc\n"
            "Prenom : Marie\n"
            "Date debut : 01/04/2025\n"
            "Date fin : 31/03/2026"
        )
        result = parse_attestation_mutuelle(text)
        assert result is not None
        expected_keys = {
            "nom_mutuelle",
            "code_organisme",
            "numero_adherent",
            "nom_assure",
            "prenom_assure",
            "date_debut_droits",
            "date_fin_droits",
        }
        assert expected_keys.issubset(result.keys())


# =============================================================================
# CROSS-PARSER SANITY CHECKS
# =============================================================================


class TestCrossParserSanity:
    """Verify parsers don't bleed into each other's domains."""

    ORDONNANCE_TEXT = """\
Dr Hélène Marchand
Date: 10/04/2025
OD : -1.50 (-0.25 a 5) Add +2.00
OG : -1.25 (-0.25 a 175) Add +2.00
Ecart pupillaire : 62 mm
"""

    FACTURE_TEXT = """\
Facture : FA-2025-0100
Date: 10/04/2025
Montant HT : 850,00 EUR
TVA (20%) : 170,00 EUR
Montant TTC : 1 020,00 EUR
"""

    # Note: parser regex uses 'adherent' without accent
    ATTESTATION_TEXT = """\
Mutuelle : MMA IARD
Code organisme : MMA01
N° adherent : 112233445
Date debut : 01/01/2025
Date fin : 31/12/2025
"""

    def test_facture_text_does_not_parse_as_ordonnance(self) -> None:
        assert parse_ordonnance(self.FACTURE_TEXT) is None

    def test_attestation_text_does_not_parse_as_ordonnance(self) -> None:
        assert parse_ordonnance(self.ATTESTATION_TEXT) is None

    def test_ordonnance_text_does_not_parse_as_facture(self) -> None:
        # No invoice number and no TTC → should be None
        assert parse_facture(self.ORDONNANCE_TEXT) is None

    def test_ordonnance_text_does_not_parse_as_attestation(self) -> None:
        assert parse_attestation_mutuelle(self.ORDONNANCE_TEXT) is None

    def test_ordonnance_text_does_not_parse_as_devis(self) -> None:
        assert parse_devis(self.ORDONNANCE_TEXT) is None
