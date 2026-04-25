"""Tests for the PDF export system.

Covers export_pdf_base helpers (pure functions, no DB) and
the main export orchestrators (DB-dependent, mocked).
"""

import io
import re
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, TableStyle


# ---------------------------------------------------------------------------
# fmt_money
# ---------------------------------------------------------------------------

class TestFmtMoney:
    def _fmt(self, val):
        from app.services.export_pdf_base import fmt_money
        return fmt_money(val)

    def test_positive_integer(self):
        result = self._fmt(1234.56)
        # Should contain narrow-space thousands separator and comma decimal
        assert "1" in result
        assert "234" in result
        assert "56" in result
        assert "EUR" in result

    def test_zero(self):
        result = self._fmt(0.0)
        assert "0,00 EUR" in result

    def test_negative(self):
        result = self._fmt(-500.0)
        assert "-" in result
        assert "500" in result
        assert "EUR" in result

    def test_large_number(self):
        result = self._fmt(1_000_000.0)
        assert "EUR" in result
        # Thousands separator present
        assert len(result) > len("1000000,00 EUR")

    def test_small_decimal(self):
        result = self._fmt(0.01)
        assert "0,01 EUR" in result

    def test_returns_string(self):
        assert isinstance(self._fmt(42.0), str)


# ---------------------------------------------------------------------------
# fmt_diopter
# ---------------------------------------------------------------------------

class TestFmtDiopter:
    def _fmt(self, val):
        from app.services.export_pdf_base import fmt_diopter
        return fmt_diopter(val)

    def test_none_returns_dash(self):
        assert self._fmt(None) == "-"

    def test_positive_value_has_plus_sign(self):
        result = self._fmt(1.25)
        assert result == "+1.25"

    def test_negative_value_has_minus_sign(self):
        result = self._fmt(-0.50)
        assert result == "-0.50"

    def test_zero_has_plus_sign(self):
        # val >= 0 → "+"
        result = self._fmt(0.0)
        assert result == "+0.00"

    def test_two_decimal_places(self):
        result = self._fmt(3.0)
        assert result == "+3.00"

    def test_negative_large(self):
        result = self._fmt(-12.75)
        assert result == "-12.75"


# ---------------------------------------------------------------------------
# create_pdf_doc
# ---------------------------------------------------------------------------

class TestCreatePdfDoc:
    def test_returns_simple_doc_template(self):
        from app.services.export_pdf_base import create_pdf_doc
        output = io.BytesIO()
        doc = create_pdf_doc(output)
        assert isinstance(doc, SimpleDocTemplate)

    def test_default_pagesize_is_a4(self):
        from app.services.export_pdf_base import create_pdf_doc
        output = io.BytesIO()
        doc = create_pdf_doc(output)
        assert doc.pagesize == A4

    def test_custom_pagesize_overrides_default(self):
        from reportlab.lib.pagesizes import LETTER
        from app.services.export_pdf_base import create_pdf_doc
        output = io.BytesIO()
        doc = create_pdf_doc(output, pagesize=LETTER)
        assert doc.pagesize == LETTER

    def test_margins_set(self):
        from reportlab.lib.units import mm
        from app.services.export_pdf_base import create_pdf_doc
        output = io.BytesIO()
        doc = create_pdf_doc(output)
        assert doc.topMargin == pytest.approx(20 * mm, abs=0.1)
        assert doc.bottomMargin == pytest.approx(15 * mm, abs=0.1)
        assert doc.leftMargin == pytest.approx(15 * mm, abs=0.1)
        assert doc.rightMargin == pytest.approx(15 * mm, abs=0.1)

    def test_custom_margin_overrides(self):
        from reportlab.lib.units import mm
        from app.services.export_pdf_base import create_pdf_doc
        output = io.BytesIO()
        doc = create_pdf_doc(output, topMargin=30 * mm)
        assert doc.topMargin == pytest.approx(30 * mm, abs=0.1)


# ---------------------------------------------------------------------------
# section_table_style
# ---------------------------------------------------------------------------

class TestSectionTableStyle:
    def test_returns_table_style_instance(self):
        from app.services.export_pdf_base import section_table_style
        ts = section_table_style()
        assert isinstance(ts, TableStyle)

    def test_has_commands(self):
        from app.services.export_pdf_base import section_table_style
        ts = section_table_style()
        # TableStyle stores commands in ._cmds
        assert len(ts._cmds) > 0

    def test_header_background_is_blue(self):
        from app.services.export_pdf_base import section_table_style
        ts = section_table_style()
        # Find BACKGROUND command for header row (0,0) -> (-1,0)
        bg_cmds = [
            cmd for cmd in ts._cmds
            if cmd[0] == "BACKGROUND" and cmd[1] == (0, 0) and cmd[2] == (-1, 0)
        ]
        assert len(bg_cmds) == 1
        assert bg_cmds[0][3] == rl_colors.HexColor("#2563EB")


# ---------------------------------------------------------------------------
# make_title_style / make_section_style / make_footer_style
# ---------------------------------------------------------------------------

class TestMakeTitleStyle:
    def test_returns_paragraph_style(self):
        from app.services.export_pdf_base import make_title_style
        s = make_title_style("TestTitle")
        assert isinstance(s, ParagraphStyle)

    def test_name_is_set(self):
        from app.services.export_pdf_base import make_title_style
        s = make_title_style("MyTitle")
        assert s.name == "MyTitle"

    def test_default_font_size(self):
        from app.services.export_pdf_base import make_title_style
        s = make_title_style("T")
        assert s.fontSize == 18

    def test_custom_font_size(self):
        from app.services.export_pdf_base import make_title_style
        s = make_title_style("T", font_size=24)
        assert s.fontSize == 24

    def test_centered_alignment(self):
        from app.services.export_pdf_base import make_title_style
        s = make_title_style("T")
        # alignment=1 means CENTER in reportlab
        assert s.alignment == 1


class TestMakeSectionStyle:
    def test_returns_paragraph_style(self):
        from app.services.export_pdf_base import make_section_style
        s = make_section_style("TestSection")
        assert isinstance(s, ParagraphStyle)

    def test_name_is_set(self):
        from app.services.export_pdf_base import make_section_style
        s = make_section_style("MySec")
        assert s.name == "MySec"

    def test_font_size_13(self):
        from app.services.export_pdf_base import make_section_style
        s = make_section_style("S")
        assert s.fontSize == 13

    def test_color_is_dark_blue(self):
        from app.services.export_pdf_base import make_section_style
        s = make_section_style("S")
        assert s.textColor == rl_colors.HexColor("#1E40AF")


class TestMakeFooterStyle:
    def test_returns_paragraph_style(self):
        from app.services.export_pdf_base import make_footer_style
        s = make_footer_style("TestFooter")
        assert isinstance(s, ParagraphStyle)

    def test_name_is_set(self):
        from app.services.export_pdf_base import make_footer_style
        s = make_footer_style("MyFooter")
        assert s.name == "MyFooter"

    def test_font_size_8(self):
        from app.services.export_pdf_base import make_footer_style
        s = make_footer_style("F")
        assert s.fontSize == 8

    def test_centered_alignment(self):
        from app.services.export_pdf_base import make_footer_style
        s = make_footer_style("F")
        assert s.alignment == 1

    def test_grey_color(self):
        from app.services.export_pdf_base import make_footer_style
        s = make_footer_style("F")
        assert s.textColor == rl_colors.grey


# ---------------------------------------------------------------------------
# generated_timestamp
# ---------------------------------------------------------------------------

class TestGeneratedTimestamp:
    def test_returns_string(self):
        from app.services.export_pdf_base import generated_timestamp
        result = generated_timestamp()
        assert isinstance(result, str)

    def test_matches_dd_mm_yyyy_hh_mm_format(self):
        from app.services.export_pdf_base import generated_timestamp
        result = generated_timestamp()
        # Expected format: DD/MM/YYYY HH:MM
        assert re.match(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$", result), (
            f"Timestamp '{result}' does not match DD/MM/YYYY HH:MM"
        )

    def test_day_and_month_are_zero_padded(self):
        from app.services.export_pdf_base import generated_timestamp
        # Freeze time to a single-digit day and month
        frozen = datetime(2026, 1, 5, 9, 7, tzinfo=UTC)
        with patch("app.services.export_pdf_base.datetime") as mock_dt:
            mock_dt.now.return_value = frozen
            result = generated_timestamp()
        assert result == "05/01/2026 09:07"

    def test_uses_utc(self):
        from app.services.export_pdf_base import generated_timestamp
        # Verify now() is called with UTC
        frozen = datetime(2026, 4, 20, 14, 30, tzinfo=UTC)
        with patch("app.services.export_pdf_base.datetime") as mock_dt:
            mock_dt.now.return_value = frozen
            result = generated_timestamp()
        mock_dt.now.assert_called_once_with(UTC)
        assert result == "20/04/2026 14:30"


# ---------------------------------------------------------------------------
# severity_color
# ---------------------------------------------------------------------------

class TestSeverityColor:
    def _color(self, sev):
        from app.services.export_pdf_base import severity_color
        return severity_color(sev)

    def test_error_returns_red(self):
        c = self._color("error")
        assert c == rl_colors.HexColor("#DC2626")

    def test_warning_returns_amber(self):
        c = self._color("warning")
        assert c == rl_colors.HexColor("#D97706")

    def test_info_returns_blue(self):
        c = self._color("info")
        assert c == rl_colors.HexColor("#2563EB")

    def test_unknown_severity_returns_blue(self):
        c = self._color("something_else")
        assert c == rl_colors.HexColor("#2563EB")

    def test_empty_string_returns_blue(self):
        c = self._color("")
        assert c == rl_colors.HexColor("#2563EB")

    def test_returns_reportlab_color(self):
        from app.services.export_pdf_base import severity_color
        assert isinstance(severity_color("error"), rl_colors.Color)


# ---------------------------------------------------------------------------
# fin_field
# ---------------------------------------------------------------------------

class TestFinField:
    def _fin(self, field):
        from app.services.export_pdf_base import fin_field
        return fin_field(field)

    def test_none_field_returns_dashes(self):
        val, source, conf = self._fin(None)
        assert val == "-"
        assert source == "-"
        assert conf == "-"

    def test_empty_dict_returns_dashes(self):
        val, source, conf = self._fin({})
        assert val == "-"
        assert source == "-"
        assert conf == "-"

    def test_value_formatted_as_eur(self):
        val, _, _ = self._fin({"value": 1234.56, "source_label": "OCR", "confidence": 0.95})
        assert "EUR" in val
        assert "1" in val and "234" in val

    def test_source_label_extracted(self):
        _, source, _ = self._fin({"value": 100.0, "source_label": "Facture Cosium", "confidence": 0.8})
        assert source == "Facture Cosium"

    def test_confidence_formatted_as_percent(self):
        _, _, conf = self._fin({"value": 50.0, "source_label": "X", "confidence": 0.75})
        assert conf == "75 %"

    def test_confidence_zero_percent(self):
        _, _, conf = self._fin({"value": 0.0, "source_label": "X", "confidence": 0.0})
        assert conf == "0 %"

    def test_confidence_100_percent(self):
        _, _, conf = self._fin({"value": 0.0, "source_label": "X", "confidence": 1.0})
        assert conf == "100 %"

    def test_missing_confidence_returns_dash(self):
        _, _, conf = self._fin({"value": 10.0, "source_label": "X"})
        assert conf == "-"

    def test_missing_source_label_returns_dash(self):
        _, source, _ = self._fin({"value": 10.0, "confidence": 0.9})
        assert source == "-"

    def test_none_value_returns_dash_for_value(self):
        val, _, _ = self._fin({"value": None, "source_label": "X", "confidence": 0.5})
        assert val == "-"

    def test_returns_tuple_of_three(self):
        result = self._fin({"value": 1.0, "source_label": "A", "confidence": 0.5})
        assert isinstance(result, tuple)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# export_client_pdf — produces bytes output (mocked DB)
# ---------------------------------------------------------------------------

class TestExportClientPdf:
    def test_produces_bytes(self, db, default_tenant):
        """export_client_pdf returns non-empty bytes (PDF header present)."""
        from app.services.export_pdf_client import export_client_pdf

        # Build a minimal client_360 mock that covers all branches
        correction_mock = MagicMock()
        correction_mock.prescription_date = "01/01/2025"
        correction_mock.prescriber_name = "Dr. Martin"
        correction_mock.sphere_right = -1.25
        correction_mock.cylinder_right = None
        correction_mock.axis_right = 90
        correction_mock.addition_right = None
        correction_mock.sphere_left = -1.0
        correction_mock.cylinder_left = None
        correction_mock.axis_left = 85
        correction_mock.addition_left = None

        cosium_data_mock = MagicMock()
        cosium_data_mock.correction_actuelle = correction_mock
        cosium_data_mock.total_ca_cosium = 1500.0
        cosium_data_mock.cosium_payments = []
        cosium_data_mock.calendar_events = []
        cosium_data_mock.equipments = []

        resume_mock = MagicMock()
        resume_mock.total_facture = 2000.0
        resume_mock.total_paye = 1800.0
        resume_mock.reste_du = 200.0
        resume_mock.taux_recouvrement = 90.0

        client_360_mock = MagicMock()
        client_360_mock.first_name = "Jean"
        client_360_mock.last_name = "Dupont"
        client_360_mock.birth_date = "15/06/1975"
        client_360_mock.email = "jean.dupont@example.com"
        client_360_mock.phone = "0612345678"
        client_360_mock.address = "12 rue de la Paix"
        client_360_mock.postal_code = "75001"
        client_360_mock.city = "Paris"
        client_360_mock.social_security_number = "175061512345678"
        client_360_mock.cosium_id = "COS-001"
        client_360_mock.cosium_data = cosium_data_mock
        client_360_mock.cosium_invoices = []
        client_360_mock.resume_financier = resume_mock

        with patch(
            "app.services.client_360_service.get_client_360",
            return_value=client_360_mock,
        ):
            result = export_client_pdf(db, client_id=1, tenant_id=default_tenant.id)

        assert isinstance(result, bytes)
        assert len(result) > 100
        # PDF magic bytes
        assert result[:4] == b"%PDF"

    def test_produces_bytes_minimal_data(self, db, default_tenant):
        """export_client_pdf handles None optional fields without raising."""
        from app.services.export_pdf_client import export_client_pdf

        resume_mock = MagicMock()
        resume_mock.total_facture = 0.0
        resume_mock.total_paye = 0.0
        resume_mock.reste_du = 0.0
        resume_mock.taux_recouvrement = 0.0

        client_360_mock = MagicMock()
        client_360_mock.first_name = "Marie"
        client_360_mock.last_name = "Curie"
        client_360_mock.birth_date = None
        client_360_mock.email = None
        client_360_mock.phone = None
        client_360_mock.address = None
        client_360_mock.postal_code = None
        client_360_mock.city = None
        client_360_mock.social_security_number = None
        client_360_mock.cosium_id = None
        client_360_mock.cosium_data = None
        client_360_mock.cosium_invoices = []
        client_360_mock.resume_financier = resume_mock

        with patch(
            "app.services.client_360_service.get_client_360",
            return_value=client_360_mock,
        ):
            result = export_client_pdf(db, client_id=99, tenant_id=default_tenant.id)

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# export_balance_clients_pdf — produces bytes (empty data set)
# ---------------------------------------------------------------------------

class TestExportBalanceClientsPdf:
    def test_produces_bytes_no_rows(self, db, default_tenant):
        """Balance PDF works with an empty result set (no outstanding invoices)."""
        from app.services.export_pdf_balance import export_balance_clients_pdf

        result = export_balance_clients_pdf(db, tenant_id=default_tenant.id)

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_produces_bytes_with_date_filter(self, db, default_tenant):
        from datetime import date
        from app.services.export_pdf_balance import export_balance_clients_pdf

        result = export_balance_clients_pdf(
            db,
            tenant_id=default_tenant.id,
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
        )

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# export_monthly_report_pdf — produces bytes (mocked DB with empty tables)
# ---------------------------------------------------------------------------

class TestExportMonthlyReportPdf:
    def test_produces_bytes(self, db, default_tenant):
        """Monthly report PDF builds successfully with no data in tables."""
        from app.services.export_pdf_report import export_monthly_report_pdf

        result = export_monthly_report_pdf(
            db, tenant_id=default_tenant.id, year=2026, month=4,
        )

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_month_names_fr_mapping(self):
        from app.services.export_pdf_report import MONTH_NAMES_FR

        assert MONTH_NAMES_FR[1] == "Janvier"
        assert MONTH_NAMES_FR[12] == "Decembre"
        assert MONTH_NAMES_FR[6] == "Juin"
        assert len(MONTH_NAMES_FR) == 12


# ---------------------------------------------------------------------------
# export_dashboard_pdf — produces bytes (mocked analytics_service)
# ---------------------------------------------------------------------------

class TestExportDashboardPdf:
    def test_produces_bytes(self, db, default_tenant):
        """Dashboard PDF builds successfully when analytics service is mocked."""
        from app.services.export_pdf_dashboard import export_dashboard_pdf

        ca_par_mois_mock = MagicMock()
        ca_par_mois_mock.mois = "Janvier 2026"
        ca_par_mois_mock.ca = 5000.0

        commercial_mock = MagicMock()
        commercial_mock.devis_en_cours = 3
        commercial_mock.devis_signes = 10
        commercial_mock.taux_conversion = 77.0
        commercial_mock.panier_moyen = 450.0
        commercial_mock.ca_par_mois = [ca_par_mois_mock]

        financial_mock = MagicMock()
        financial_mock.ca_total = 50000.0
        financial_mock.montant_facture = 48000.0
        financial_mock.montant_encaisse = 45000.0
        financial_mock.reste_a_encaisser = 3000.0
        financial_mock.taux_recouvrement = 93.75

        cosium_mock = MagicMock()
        cosium_mock.total_facture_cosium = 50000.0
        cosium_mock.total_outstanding = 3000.0
        cosium_mock.total_paid = 47000.0
        cosium_mock.invoice_count = 120
        cosium_mock.quote_count = 15
        cosium_mock.credit_note_count = 2

        operational_mock = MagicMock()
        operational_mock.dossiers_en_cours = 8
        operational_mock.dossiers_complets = 112
        operational_mock.taux_completude = 93.3
        operational_mock.pieces_manquantes = 4

        dashboard_mock = MagicMock()
        dashboard_mock.financial = financial_mock
        dashboard_mock.cosium = cosium_mock
        dashboard_mock.operational = operational_mock
        dashboard_mock.commercial = commercial_mock

        with patch(
            "app.services.analytics_comparison_service.get_dashboard_full",
            return_value=dashboard_mock,
        ):
            result = export_dashboard_pdf(
                db, tenant_id=default_tenant.id,
            )

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"

    def test_produces_bytes_no_cosium(self, db, default_tenant):
        """Dashboard PDF handles missing cosium block gracefully."""
        from app.services.export_pdf_dashboard import export_dashboard_pdf

        financial_mock = MagicMock()
        financial_mock.ca_total = 0.0
        financial_mock.montant_facture = 0.0
        financial_mock.montant_encaisse = 0.0
        financial_mock.reste_a_encaisser = 0.0
        financial_mock.taux_recouvrement = 0.0

        commercial_mock = MagicMock()
        commercial_mock.devis_en_cours = 0
        commercial_mock.devis_signes = 0
        commercial_mock.taux_conversion = 0.0
        commercial_mock.panier_moyen = 0.0
        commercial_mock.ca_par_mois = []

        operational_mock = MagicMock()
        operational_mock.dossiers_en_cours = 0
        operational_mock.dossiers_complets = 0
        operational_mock.taux_completude = 0.0
        operational_mock.pieces_manquantes = 0

        dashboard_mock = MagicMock()
        dashboard_mock.financial = financial_mock
        dashboard_mock.cosium = None
        dashboard_mock.operational = operational_mock
        dashboard_mock.commercial = commercial_mock

        with patch(
            "app.services.analytics_comparison_service.get_dashboard_full",
            return_value=dashboard_mock,
        ):
            result = export_dashboard_pdf(db, tenant_id=default_tenant.id)

        assert isinstance(result, bytes)
        assert result[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Facade re-exports (export_pdf.py)
# ---------------------------------------------------------------------------

class TestExportPdfFacade:
    """Verify that export_pdf.py correctly re-exports all public symbols."""

    def test_export_client_pdf_importable(self):
        from app.services.export_pdf import export_client_pdf  # noqa: F401

    def test_export_dashboard_pdf_importable(self):
        from app.services.export_pdf import export_dashboard_pdf  # noqa: F401

    def test_export_balance_clients_pdf_importable(self):
        from app.services.export_pdf import export_balance_clients_pdf  # noqa: F401

    def test_export_pec_preparation_pdf_importable(self):
        from app.services.export_pdf import export_pec_preparation_pdf  # noqa: F401

    def test_export_monthly_report_pdf_importable(self):
        from app.services.export_pdf import export_monthly_report_pdf  # noqa: F401

    def test_month_names_fr_importable(self):
        from app.services.export_pdf import MONTH_NAMES_FR  # noqa: F401
        assert isinstance(MONTH_NAMES_FR, dict)

    def test_get_balance_rows_importable(self):
        from app.services.export_pdf import _get_balance_rows  # noqa: F401
