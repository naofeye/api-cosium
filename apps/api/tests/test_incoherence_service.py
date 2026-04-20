"""Tests for incoherence_checks, incoherence_helpers, and consolidation_identity."""

from datetime import date, datetime, timedelta, UTC
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# incoherence_helpers
# ---------------------------------------------------------------------------
from app.services.incoherence_helpers import (
    ADDITION_MAX,
    ADDITION_MIN,
    AXIS_MAX,
    AXIS_MIN,
    CYLINDER_MAX,
    CYLINDER_MIN,
    PD_MAX,
    PD_MIN,
    SPHERE_MAX,
    SPHERE_MIN,
    _calculate_age,
    _parse_date,
    _safe_float,
    _validate_optical_range,
)
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
    FieldStatus,
)


# ============================================================
# _parse_date
# ============================================================

class TestParseDate:
    def test_already_a_date(self):
        d = date(2024, 3, 15)
        assert _parse_date(d) == d

    def test_datetime_returns_date_part(self):
        dt = datetime(2024, 3, 15, 10, 30, 0)
        assert _parse_date(dt) == date(2024, 3, 15)

    def test_iso_format_string(self):
        assert _parse_date("2024-03-15") == date(2024, 3, 15)

    def test_french_slash_format(self):
        assert _parse_date("15/03/2024") == date(2024, 3, 15)

    def test_dash_format(self):
        assert _parse_date("15-03-2024") == date(2024, 3, 15)

    def test_invalid_string_returns_none(self):
        assert _parse_date("not-a-date") is None

    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_integer_returns_none(self):
        assert _parse_date(20240315) is None

    def test_empty_string_returns_none(self):
        assert _parse_date("") is None

    def test_partial_date_string_returns_none(self):
        assert _parse_date("2024-03") is None


# ============================================================
# _safe_float
# ============================================================

class TestSafeFloat:
    def test_none_returns_none(self):
        assert _safe_float(None) is None

    def test_integer_converted(self):
        assert _safe_float(5) == 5.0

    def test_float_passthrough(self):
        assert _safe_float(-2.75) == -2.75

    def test_valid_string(self):
        assert _safe_float("3.25") == 3.25

    def test_negative_string(self):
        assert _safe_float("-1.50") == -1.5

    def test_invalid_string_returns_none(self):
        assert _safe_float("abc") is None

    def test_empty_string_returns_none(self):
        assert _safe_float("") is None

    def test_list_returns_none(self):
        assert _safe_float([1.0]) is None

    def test_zero_string(self):
        assert _safe_float("0") == 0.0

    def test_bool_true(self):
        # bool is a subclass of int in Python — 1.0 expected
        assert _safe_float(True) == 1.0


# ============================================================
# _validate_optical_range
# ============================================================

class TestValidateOpticalRange:
    def test_value_in_range_returns_none(self):
        assert _validate_optical_range(-2.0, "sphere_od", "Sphere OD", -25.0, 25.0, "src") is None

    def test_value_at_min_boundary_ok(self):
        assert _validate_optical_range(SPHERE_MIN, "sphere_od", "Sphere OD", SPHERE_MIN, SPHERE_MAX, "src") is None

    def test_value_at_max_boundary_ok(self):
        assert _validate_optical_range(SPHERE_MAX, "sphere_od", "Sphere OD", SPHERE_MIN, SPHERE_MAX, "src") is None

    def test_value_below_min_returns_alert(self):
        alert = _validate_optical_range(-30.0, "sphere_od", "Sphere OD", SPHERE_MIN, SPHERE_MAX, "src1")
        assert alert is not None
        assert alert.severity == "error"
        assert alert.field == "sphere_od"
        assert "-30.0" in alert.message
        assert "src1" in alert.sources

    def test_value_above_max_returns_alert(self):
        alert = _validate_optical_range(30.0, "sphere_og", "Sphere OG", SPHERE_MIN, SPHERE_MAX, "src2")
        assert alert is not None
        assert alert.severity == "error"
        assert alert.field == "sphere_og"
        assert "30.0" in alert.message

    def test_none_value_returns_none(self):
        assert _validate_optical_range(None, "sphere_od", "Sphere OD", SPHERE_MIN, SPHERE_MAX, "src") is None

    def test_empty_source_gives_empty_sources_list(self):
        alert = _validate_optical_range(-99.0, "sphere_od", "Sphere OD", SPHERE_MIN, SPHERE_MAX, "")
        assert alert is not None
        assert alert.sources == []

    def test_axis_out_of_range(self):
        alert = _validate_optical_range(200, "axis_od", "Axe OD", AXIS_MIN, AXIS_MAX, "rx_src")
        assert alert is not None
        assert alert.severity == "error"
        assert "200" in alert.message

    def test_axis_in_range(self):
        assert _validate_optical_range(90, "axis_od", "Axe OD", AXIS_MIN, AXIS_MAX, "src") is None

    def test_addition_below_min(self):
        alert = _validate_optical_range(0.25, "addition_od", "Addition OD", ADDITION_MIN, ADDITION_MAX, "src")
        assert alert is not None

    def test_addition_above_max(self):
        alert = _validate_optical_range(5.0, "addition_od", "Addition OD", ADDITION_MIN, ADDITION_MAX, "src")
        assert alert is not None

    def test_pd_too_small(self):
        alert = _validate_optical_range(40.0, "ecart_pupillaire", "Ecart pupillaire", PD_MIN, PD_MAX, "src")
        assert alert is not None

    def test_pd_too_large(self):
        alert = _validate_optical_range(90.0, "ecart_pupillaire", "Ecart pupillaire", PD_MIN, PD_MAX, "src")
        assert alert is not None


# ============================================================
# _calculate_age
# ============================================================

class TestCalculateAge:
    def test_age_today_birthday(self):
        today = date.today()
        dob = date(today.year - 30, today.month, today.day)
        assert _calculate_age(dob) == 30

    def test_age_birthday_not_yet_this_year(self):
        today = date.today()
        # Birthday is tomorrow → hasn't turned yet
        tomorrow = today + timedelta(days=1)
        dob = date(today.year - 25, tomorrow.month, tomorrow.day)
        assert _calculate_age(dob) == 24

    def test_age_birthday_already_this_year(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        dob = date(today.year - 25, yesterday.month, yesterday.day)
        assert _calculate_age(dob) == 25

    def test_newborn_age_zero(self):
        assert _calculate_age(date.today()) == 0

    def test_age_very_old(self):
        dob = date(1924, 1, 1)
        age = _calculate_age(dob)
        assert age >= 100


# ============================================================
# Helpers: build test profile
# ============================================================

def _make_field(
    value,
    source: str = "test_src",
    source_label: str = "Test",
    confidence: float = 1.0,
    status: FieldStatus = FieldStatus.EXTRACTED,
    alternatives=None,
    last_updated=None,
) -> ConsolidatedField:
    return ConsolidatedField(
        value=value,
        source=source,
        source_label=source_label,
        confidence=confidence,
        status=status,
        alternatives=alternatives,
        last_updated=last_updated,
    )


def _empty_profile() -> ConsolidatedClientProfile:
    return ConsolidatedClientProfile()


# ============================================================
# detect_field_status_alerts
# ============================================================

from app.services.incoherence_checks import (
    detect_field_status_alerts,
    detect_temporal_incoherences,
    detect_equipment_incoherences,
    detect_optical_incoherences,
)


class TestDetectFieldStatusAlerts:
    def test_no_alerts_when_all_extracted(self):
        profile = _empty_profile()
        profile.nom = _make_field("Dupont", status=FieldStatus.EXTRACTED)
        profile.prenom = _make_field("Jean", status=FieldStatus.EXTRACTED)
        alerts = detect_field_status_alerts(profile)
        assert alerts == []

    def test_conflict_field_generates_warning(self):
        profile = _empty_profile()
        profile.nom = _make_field(
            "Dupont",
            status=FieldStatus.CONFLICT,
            alternatives=[{"value": "DUPONT", "source": "ocr_src"}],
        )
        alerts = detect_field_status_alerts(profile)
        assert len(alerts) == 1
        assert alerts[0].severity == "warning"
        assert alerts[0].field == "nom"
        assert "Conflit" in alerts[0].message
        assert "DUPONT" in alerts[0].message

    def test_deduced_field_generates_info(self):
        profile = _empty_profile()
        profile.sphere_od = _make_field(-2.5, status=FieldStatus.DEDUCED, source_label="Ordonnance OCR")
        alerts = detect_field_status_alerts(profile)
        assert len(alerts) == 1
        assert alerts[0].severity == "info"
        assert alerts[0].field == "sphere_od"
        assert "deduit" in alerts[0].message.lower()

    def test_missing_field_not_in_list_skipped(self):
        # profile.nom is None → skipped entirely
        profile = _empty_profile()
        alerts = detect_field_status_alerts(profile)
        assert alerts == []

    def test_multiple_conflicts(self):
        profile = _empty_profile()
        profile.nom = _make_field("Dupont", status=FieldStatus.CONFLICT, alternatives=[])
        profile.prenom = _make_field("Jean", status=FieldStatus.CONFLICT, alternatives=[])
        alerts = detect_field_status_alerts(profile)
        assert len(alerts) == 2

    def test_conflict_includes_alternative_values_in_message(self):
        profile = _empty_profile()
        profile.numero_secu = _make_field(
            "123456789",
            status=FieldStatus.CONFLICT,
            alternatives=[{"value": "987654321", "source": "ocr"}],
        )
        alerts = detect_field_status_alerts(profile)
        assert "987654321" in alerts[0].message

    def test_sources_list_includes_field_source_and_alternatives(self):
        profile = _empty_profile()
        profile.mutuelle_nom = _make_field(
            "MGEN",
            source="ocr_src",
            status=FieldStatus.CONFLICT,
            alternatives=[{"value": "Harmonie", "source": "cosium_src"}],
        )
        alerts = detect_field_status_alerts(profile)
        assert "ocr_src" in alerts[0].sources
        assert "cosium_src" in alerts[0].sources

    def test_confirmed_field_no_alert(self):
        profile = _empty_profile()
        profile.nom = _make_field("Dupont", status=FieldStatus.CONFIRMED)
        alerts = detect_field_status_alerts(profile)
        assert alerts == []

    def test_manual_field_no_alert(self):
        profile = _empty_profile()
        profile.prenom = _make_field("Jean", status=FieldStatus.MANUAL)
        alerts = detect_field_status_alerts(profile)
        assert alerts == []


# ============================================================
# detect_temporal_incoherences
# ============================================================

class TestDetectTemporalIncoherences:
    def test_no_alerts_for_empty_profile(self):
        profile = _empty_profile()
        alerts = detect_temporal_incoherences(profile)
        assert alerts == []

    def test_addition_for_minor_raises_warning(self):
        today = date.today()
        dob = date(today.year - 10, today.month, today.day)  # 10-year-old
        profile = _empty_profile()
        profile.date_naissance = _make_field(str(dob))
        profile.addition_od = _make_field(2.0)
        alerts = detect_temporal_incoherences(profile)
        fields = [a.field for a in alerts]
        assert "addition" in fields
        minor_alert = next(a for a in alerts if a.field == "addition" and "mineur" in a.message)
        assert minor_alert.severity == "warning"

    def test_no_addition_for_over_50_raises_info(self):
        today = date.today()
        dob = date(today.year - 60, today.month, today.day)
        profile = _empty_profile()
        profile.date_naissance = _make_field(str(dob))
        # No addition fields set
        alerts = detect_temporal_incoherences(profile)
        fields = [a.field for a in alerts]
        assert "addition" in fields
        alert = next(a for a in alerts if a.field == "addition")
        assert alert.severity == "info"
        assert "presbyte" in alert.message

    def test_no_alert_when_over_50_has_addition(self):
        today = date.today()
        dob = date(today.year - 55, today.month, today.day)
        profile = _empty_profile()
        profile.date_naissance = _make_field(str(dob))
        profile.addition_od = _make_field(2.0)
        alerts = detect_temporal_incoherences(profile)
        addition_alerts = [a for a in alerts if a.field == "addition"]
        assert addition_alerts == []

    def test_no_alert_for_under_16_without_addition(self):
        today = date.today()
        dob = date(today.year - 12, today.month, today.day)
        profile = _empty_profile()
        profile.date_naissance = _make_field(str(dob))
        # No addition fields
        alerts = detect_temporal_incoherences(profile)
        addition_alerts = [a for a in alerts if a.field == "addition"]
        assert addition_alerts == []

    def test_devis_before_ordonnance_raises_warning(self):
        ordo_date = date(2025, 6, 1)
        devis_date = datetime(2025, 4, 1, tzinfo=UTC)  # 2 months before ordonnance
        profile = _empty_profile()
        profile.date_ordonnance = _make_field(str(ordo_date))
        profile.montant_ttc = _make_field(450.0, last_updated=devis_date)
        alerts = detect_temporal_incoherences(profile)
        fields = [a.field for a in alerts]
        assert "montant_ttc" in fields
        alert = next(a for a in alerts if a.field == "montant_ttc")
        assert alert.severity == "warning"
        assert "30 jours" in alert.message

    def test_devis_slightly_before_ordonnance_no_alert(self):
        # Within 30-day window → no alert
        ordo_date = date(2025, 6, 1)
        devis_date = datetime(2025, 5, 15, tzinfo=UTC)  # 17 days before
        profile = _empty_profile()
        profile.date_ordonnance = _make_field(str(ordo_date))
        profile.montant_ttc = _make_field(450.0, last_updated=devis_date)
        alerts = detect_temporal_incoherences(profile)
        assert not any(a.field == "montant_ttc" for a in alerts)

    def test_invalid_dob_skips_age_checks(self):
        profile = _empty_profile()
        profile.date_naissance = _make_field("not-a-date")
        profile.addition_od = _make_field(2.0)
        # Should not crash; no age-based alerts
        alerts = detect_temporal_incoherences(profile)
        assert not any(a.field == "addition" for a in alerts)


# ============================================================
# detect_equipment_incoherences
# ============================================================

class TestDetectEquipmentIncoherences:
    def test_no_alerts_when_complete(self):
        profile = _empty_profile()
        profile.montant_ttc = _make_field(450.0)
        profile.monture = _make_field("Ray-Ban RB3025")
        profile.verres = [_make_field("Verre progressif OD"), _make_field("Verre progressif OG")]
        alerts = detect_equipment_incoherences(profile)
        assert alerts == []

    def test_missing_monture_with_montant_raises_warning(self):
        profile = _empty_profile()
        profile.montant_ttc = _make_field(450.0)
        profile.verres = [_make_field("Verre progressif")]
        alerts = detect_equipment_incoherences(profile)
        assert any(a.field == "monture" for a in alerts)
        monture_alert = next(a for a in alerts if a.field == "monture")
        assert monture_alert.severity == "warning"

    def test_missing_verres_with_montant_raises_warning(self):
        profile = _empty_profile()
        profile.montant_ttc = _make_field(450.0)
        profile.monture = _make_field("Ray-Ban")
        alerts = detect_equipment_incoherences(profile)
        assert any(a.field == "verres" for a in alerts)

    def test_no_alerts_when_no_montant(self):
        # Without montant_ttc, no equipment alerts expected
        profile = _empty_profile()
        alerts = detect_equipment_incoherences(profile)
        assert not any(a.field == "monture" for a in alerts)
        assert not any(a.field == "verres" for a in alerts)

    def test_addition_with_unifocal_verre_raises_warning(self):
        profile = _empty_profile()
        profile.addition_od = _make_field(2.0)
        profile.verres = [_make_field("Verre unifocal OD")]
        alerts = detect_equipment_incoherences(profile)
        verre_alerts = [a for a in alerts if a.field == "verres" and "unifocal" in a.message]
        assert len(verre_alerts) >= 1
        assert verre_alerts[0].severity == "warning"

    def test_addition_with_progressive_verre_no_incoherence(self):
        profile = _empty_profile()
        profile.addition_od = _make_field(2.0)
        profile.verres = [_make_field("Verre progressif OD")]
        alerts = detect_equipment_incoherences(profile)
        unifocal_alerts = [a for a in alerts if "unifocal" in a.message]
        assert unifocal_alerts == []

    def test_addition_zero_with_unifocal_no_incoherence(self):
        # addition = 0 means no addition
        profile = _empty_profile()
        profile.addition_od = _make_field(0.0)
        profile.verres = [_make_field("Verre unifocal")]
        alerts = detect_equipment_incoherences(profile)
        unifocal_alerts = [a for a in alerts if "unifocal" in a.message]
        assert unifocal_alerts == []

    def test_og_addition_with_unifocal_also_triggers(self):
        profile = _empty_profile()
        profile.addition_og = _make_field(1.5)
        profile.verres = [_make_field("verre unifocal OG")]
        alerts = detect_equipment_incoherences(profile)
        assert any("unifocal" in a.message for a in alerts)


# ============================================================
# detect_optical_incoherences
# ============================================================

class TestDetectOpticalIncoherences:
    def test_no_alerts_for_empty_profile(self):
        profile = _empty_profile()
        alerts = detect_optical_incoherences(profile)
        assert alerts == []

    def test_ordonnance_older_than_3_years_is_error(self):
        old_date = date.today() - timedelta(days=3 * 365 + 10)
        profile = _empty_profile()
        profile.date_ordonnance = _make_field(str(old_date), source="rx_src")
        alerts = detect_optical_incoherences(profile)
        ordo_alerts = [a for a in alerts if a.field == "date_ordonnance"]
        assert len(ordo_alerts) == 1
        assert ordo_alerts[0].severity == "error"
        assert "perimee" in ordo_alerts[0].message
        assert "rx_src" in ordo_alerts[0].sources

    def test_ordonnance_between_1_and_3_years_is_warning(self):
        old_date = date.today() - timedelta(days=400)
        profile = _empty_profile()
        profile.date_ordonnance = _make_field(str(old_date), source="rx_src")
        alerts = detect_optical_incoherences(profile)
        ordo_alerts = [a for a in alerts if a.field == "date_ordonnance"]
        assert len(ordo_alerts) == 1
        assert ordo_alerts[0].severity == "warning"
        assert "expiree" in ordo_alerts[0].message

    def test_recent_ordonnance_no_alert(self):
        recent = date.today() - timedelta(days=180)
        profile = _empty_profile()
        profile.date_ordonnance = _make_field(str(recent))
        alerts = detect_optical_incoherences(profile)
        ordo_alerts = [a for a in alerts if a.field == "date_ordonnance"]
        assert ordo_alerts == []

    def test_addition_gap_greater_than_0_50_raises_warning(self):
        profile = _empty_profile()
        profile.addition_od = _make_field(2.0, source="src_od")
        profile.addition_og = _make_field(1.0, source="src_og")  # gap = 1.0
        alerts = detect_optical_incoherences(profile)
        add_alerts = [a for a in alerts if a.field == "addition"]
        assert len(add_alerts) == 1
        assert add_alerts[0].severity == "warning"
        assert "OD=+2.00" in add_alerts[0].message
        assert "OG=+1.00" in add_alerts[0].message

    def test_addition_gap_exactly_0_50_no_alert(self):
        profile = _empty_profile()
        profile.addition_od = _make_field(2.0)
        profile.addition_og = _make_field(1.5)  # gap = 0.5 → not > 0.50
        alerts = detect_optical_incoherences(profile)
        add_alerts = [a for a in alerts if a.field == "addition"]
        assert add_alerts == []

    def test_addition_gap_slightly_over_0_50_raises_warning(self):
        profile = _empty_profile()
        profile.addition_od = _make_field(2.0)
        profile.addition_og = _make_field(1.49)  # gap = 0.51
        alerts = detect_optical_incoherences(profile)
        add_alerts = [a for a in alerts if a.field == "addition"]
        assert len(add_alerts) == 1

    def test_sphere_out_of_range_raises_error(self):
        profile = _empty_profile()
        profile.sphere_od = _make_field(-30.0, source="rx_src")
        alerts = detect_optical_incoherences(profile)
        sphere_alerts = [a for a in alerts if a.field == "sphere_od"]
        assert len(sphere_alerts) == 1
        assert sphere_alerts[0].severity == "error"

    def test_sphere_in_range_no_alert(self):
        profile = _empty_profile()
        profile.sphere_od = _make_field(-2.5)
        alerts = detect_optical_incoherences(profile)
        assert not any(a.field == "sphere_od" for a in alerts)

    def test_cylinder_out_of_range_raises_error(self):
        profile = _empty_profile()
        profile.cylinder_og = _make_field(-15.0)
        alerts = detect_optical_incoherences(profile)
        assert any(a.field == "cylinder_og" for a in alerts)

    def test_axis_out_of_range_raises_error(self):
        profile = _empty_profile()
        profile.axis_od = _make_field(200)
        alerts = detect_optical_incoherences(profile)
        assert any(a.field == "axis_od" for a in alerts)

    def test_axis_at_boundary_0_ok(self):
        profile = _empty_profile()
        profile.axis_od = _make_field(0)
        alerts = detect_optical_incoherences(profile)
        assert not any(a.field == "axis_od" for a in alerts)

    def test_axis_at_boundary_180_ok(self):
        profile = _empty_profile()
        profile.axis_od = _make_field(180)
        alerts = detect_optical_incoherences(profile)
        assert not any(a.field == "axis_od" for a in alerts)

    def test_pd_out_of_range_raises_error(self):
        profile = _empty_profile()
        profile.ecart_pupillaire = _make_field(45.0)
        alerts = detect_optical_incoherences(profile)
        assert any(a.field == "ecart_pupillaire" for a in alerts)

    def test_pd_in_range_no_alert(self):
        profile = _empty_profile()
        profile.ecart_pupillaire = _make_field(64.0)
        alerts = detect_optical_incoherences(profile)
        assert not any(a.field == "ecart_pupillaire" for a in alerts)

    def test_non_parseable_field_value_skipped(self):
        profile = _empty_profile()
        profile.sphere_od = _make_field("non-numeric")
        # _safe_float → None → _validate_optical_range(None) → None → no alert
        alerts = detect_optical_incoherences(profile)
        assert not any(a.field == "sphere_od" for a in alerts)

    def test_invalid_ordonnance_date_no_alert(self):
        profile = _empty_profile()
        profile.date_ordonnance = _make_field("not-a-date")
        alerts = detect_optical_incoherences(profile)
        ordo_alerts = [a for a in alerts if a.field == "date_ordonnance"]
        assert ordo_alerts == []

    def test_multiple_range_errors_all_reported(self):
        profile = _empty_profile()
        profile.sphere_od = _make_field(-30.0)
        profile.cylinder_od = _make_field(-20.0)
        profile.axis_od = _make_field(200)
        alerts = detect_optical_incoherences(profile)
        fields_in_alerts = {a.field for a in alerts}
        assert "sphere_od" in fields_in_alerts
        assert "cylinder_od" in fields_in_alerts
        assert "axis_od" in fields_in_alerts


# ============================================================
# consolidation_identity
# ============================================================

from app.services.consolidation_identity import consolidate_identity, consolidate_mutuelle
from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle


def _make_customer(**kwargs) -> Customer:
    """Build a Customer ORM object without a real DB session."""
    defaults = dict(
        id=1,
        tenant_id=1,
        first_name="Jean",
        last_name="Dupont",
        birth_date=date(1985, 7, 20),
        social_security_number="1850775012345",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=None,
    )
    defaults.update(kwargs)
    c = Customer.__new__(Customer)
    for k, v in defaults.items():
        setattr(c, k, v)
    return c


def _make_mutuelle(**kwargs) -> ClientMutuelle:
    defaults = dict(
        id=1,
        tenant_id=1,
        customer_id=1,
        mutuelle_name="MGEN",
        numero_adherent="12345A",
        type_beneficiaire="assure",
        date_fin=date(2026, 12, 31),
        source="cosium_tpp",
        confidence=0.9,
    )
    defaults.update(kwargs)
    m = ClientMutuelle.__new__(ClientMutuelle)
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


class TestConsolidateIdentity:
    def test_customer_data_populates_nom_and_prenom(self):
        profile = _empty_profile()
        customer = _make_customer()
        consolidate_identity(profile, customer, {})
        assert profile.nom is not None
        assert profile.nom.value == "Dupont"
        assert profile.prenom is not None
        assert profile.prenom.value == "Jean"

    def test_customer_source_is_cosium_client(self):
        profile = _empty_profile()
        customer = _make_customer()
        consolidate_identity(profile, customer, {})
        assert profile.nom.source == "cosium_client"
        assert profile.prenom.source == "cosium_client"

    def test_numero_secu_populated_from_customer(self):
        profile = _empty_profile()
        customer = _make_customer(social_security_number="1850775012345")
        consolidate_identity(profile, customer, {})
        assert profile.numero_secu is not None
        assert profile.numero_secu.value == "1850775012345"

    def test_date_naissance_set_from_customer(self):
        profile = _empty_profile()
        customer = _make_customer(birth_date=date(1985, 7, 20))
        consolidate_identity(profile, customer, {})
        assert profile.date_naissance is not None
        assert profile.date_naissance.value == "1985-07-20"
        assert profile.date_naissance.source == "cosium_client"

    def test_no_birth_date_leaves_date_naissance_none(self):
        profile = _empty_profile()
        customer = _make_customer(birth_date=None)
        consolidate_identity(profile, customer, {})
        assert profile.date_naissance is None

    def test_none_customer_leaves_identity_fields_none(self):
        profile = _empty_profile()
        consolidate_identity(profile, None, {})
        assert profile.nom is None
        assert profile.prenom is None
        assert profile.numero_secu is None
        assert profile.date_naissance is None

    def test_no_secu_leaves_numero_secu_none(self):
        profile = _empty_profile()
        customer = _make_customer(social_security_number=None)
        consolidate_identity(profile, customer, {})
        assert profile.numero_secu is None

    def test_ocr_nom_conflict_detected(self):
        """When OCR provides a different nom, CONFLICT status should be set."""
        profile = _empty_profile()
        customer = _make_customer(last_name="Dupont")
        ocr_map = {
            "attestation_mutuelle": (
                {"nom": "DUPON"},  # Different spelling
                "doc_ocr_42",
                "Document OCR (attestation_mutuelle)",
                0.85,
            )
        }
        consolidate_identity(profile, customer, ocr_map)
        assert profile.nom is not None
        # Primary = Cosium → retained; secondary differs → CONFLICT
        assert profile.nom.status == FieldStatus.CONFLICT

    def test_ocr_nom_same_as_cosium_no_conflict(self):
        """When OCR matches Cosium, no conflict."""
        profile = _empty_profile()
        customer = _make_customer(last_name="Dupont")
        ocr_map = {
            "attestation_mutuelle": (
                {"nom": "Dupont"},
                "doc_ocr_42",
                "Document OCR",
                0.9,
            )
        }
        consolidate_identity(profile, customer, ocr_map)
        assert profile.nom is not None
        assert profile.nom.status == FieldStatus.EXTRACTED

    def test_no_cosium_data_uses_ocr_as_deduced(self):
        """When no customer, OCR becomes the deduced source."""
        profile = _empty_profile()
        ocr_map = {
            "attestation_mutuelle": (
                {"nom": "Martin"},
                "doc_ocr_99",
                "Document OCR",
                0.75,
            )
        }
        consolidate_identity(profile, None, ocr_map)
        assert profile.nom is not None
        assert profile.nom.value == "Martin"
        assert profile.nom.status == FieldStatus.DEDUCED


class TestConsolidateMutuelle:
    def test_mutuelle_from_single_source(self):
        profile = _empty_profile()
        mut = _make_mutuelle()
        consolidate_mutuelle(profile, [mut], {})
        assert profile.mutuelle_nom is not None
        # No OCR → secondary becomes DEDUCED
        assert profile.mutuelle_nom.value == "MGEN"

    def test_no_mutuelles_and_no_ocr_leaves_nom_none(self):
        profile = _empty_profile()
        consolidate_mutuelle(profile, [], {})
        assert profile.mutuelle_nom is None

    def test_date_fin_droits_from_mutuelle(self):
        profile = _empty_profile()
        mut = _make_mutuelle(date_fin=date(2026, 12, 31))
        consolidate_mutuelle(profile, [mut], {})
        assert profile.date_fin_droits is not None

    def test_type_beneficiaire_set_from_mutuelle(self):
        profile = _empty_profile()
        mut = _make_mutuelle(type_beneficiaire="conjoint")
        consolidate_mutuelle(profile, [mut], {})
        assert profile.type_beneficiaire is not None
        assert profile.type_beneficiaire.value == "conjoint"

    def test_ocr_provides_primary_mutuelle_nom(self):
        """OCR attestation is PRIMARY for mutuelle fields."""
        profile = _empty_profile()
        mut = _make_mutuelle(mutuelle_name="MGEN")
        ocr_map = {
            "attestation_mutuelle": (
                {"mutuelle_nom": "Harmonie Mutuelle", "numero_adherent": "99887A"},
                "doc_ocr_10",
                "Document OCR (attestation_mutuelle)",
                0.95,
            )
        }
        consolidate_mutuelle(profile, [mut], ocr_map)
        assert profile.mutuelle_nom is not None
        # OCR is primary → OCR value should be retained
        assert profile.mutuelle_nom.value == "Harmonie Mutuelle"

    def test_ocr_code_organisme_sets_field(self):
        profile = _empty_profile()
        ocr_map = {
            "attestation_mutuelle": (
                {"code_organisme": "750012345"},
                "doc_ocr_20",
                "Document OCR",
                0.9,
            )
        }
        consolidate_mutuelle(profile, [], ocr_map)
        assert profile.mutuelle_code_organisme is not None
        assert profile.mutuelle_code_organisme.value == "750012345"

    def test_no_ocr_code_organisme_field_none_when_no_source(self):
        profile = _empty_profile()
        mut = _make_mutuelle()
        # No code_organisme on mutuelle model → attribute might not exist
        if hasattr(mut, "code_organisme"):
            mut.code_organisme = None
        consolidate_mutuelle(profile, [mut], {})
        # Should not crash; field may remain None if no source provides it
        # (test just asserts no exception is raised)

    def test_ocr_conflict_with_mutuelle_nom(self):
        """When OCR and mutuelle disagree on nom, CONFLICT is set."""
        profile = _empty_profile()
        mut = _make_mutuelle(mutuelle_name="MGEN")
        ocr_map = {
            "attestation_mutuelle": (
                {"mutuelle_nom": "Harmonie"},
                "doc_ocr_30",
                "Document OCR",
                0.9,
            )
        }
        consolidate_mutuelle(profile, [mut], ocr_map)
        # OCR primary = "Harmonie", secondary = "MGEN" → CONFLICT
        assert profile.mutuelle_nom.status == FieldStatus.CONFLICT
