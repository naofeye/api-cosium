"""Tests for PEC field-level status tracking, conflict detection, and optical validation.

10 tests covering:
1. Devis field has status=EXTRACTED, confidence=1.0
2. OCR-only field has status=DEDUCED
3. Missing field has status=MISSING
4. Conflicting sources produce status=CONFLICT with alternatives
5. Sphere tolerance 0.25 D doesn't trigger conflict
6. Sphere difference > 0.25 D triggers conflict
7. Amount tolerance 1 EUR works
8. Manual correction sets status=MANUAL
9. Optical validation: sphere out of range -> error
10. Optical validation: valid values -> no error
"""

import pytest

from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
    FieldStatus,
)
from app.services.consolidation_service import (
    _make_field,
    _make_missing_field,
    _resolve_field,
    TOLERANCE_AMOUNT,
    TOLERANCE_SPHERE,
)
from app.services.incoherence_detector import (
    detect_incoherences,
    detect_optical_incoherences,
)


class TestFieldStatus:
    """Tests for FieldStatus on ConsolidatedField."""

    def test_devis_field_extracted_confidence_1(self) -> None:
        """1. A field from devis should have status=EXTRACTED and confidence=1.0."""
        field = _make_field(
            value=450.00,
            source="devis_42",
            source_label="Devis D-2026-042",
            confidence=1.0,
            status=FieldStatus.EXTRACTED,
        )
        assert field.status == FieldStatus.EXTRACTED
        assert field.confidence == 1.0
        assert field.value == 450.00
        assert field.source == "devis_42"

    def test_ocr_only_field_deduced(self) -> None:
        """2. A field from OCR only (no primary source) should have status=DEDUCED."""
        field = _resolve_field(
            primary_value=None,
            primary_source="cosium_prescription_1",
            primary_label="Ordonnance Cosium",
            primary_confidence=0.95,
            secondary_value=2.50,
            secondary_source="document_ocr_123",
            secondary_label="Document OCR (ordonnance)",
            secondary_confidence=0.7,
        )
        assert field.status == FieldStatus.DEDUCED
        assert field.value == 2.50
        assert field.source == "document_ocr_123"

    def test_missing_field_status(self) -> None:
        """3. A field with no data from any source should have status=MISSING."""
        field = _resolve_field(
            primary_value=None,
            primary_source="cosium_client",
            primary_label="Cosium",
            primary_confidence=1.0,
            secondary_value=None,
            secondary_source="document_ocr_1",
            secondary_label="Document OCR",
            secondary_confidence=0.7,
        )
        assert field.status == FieldStatus.MISSING
        assert field.value is None
        assert field.confidence == 0.0

    def test_missing_field_helper(self) -> None:
        """3b. _make_missing_field helper produces correct status."""
        field = _make_missing_field()
        assert field.status == FieldStatus.MISSING
        assert field.value is None
        assert field.confidence == 0.0

    def test_conflicting_sources_produce_conflict_with_alternatives(self) -> None:
        """4. Two sources with different values should produce CONFLICT with alternatives."""
        field = _resolve_field(
            primary_value=450.00,
            primary_source="devis_42",
            primary_label="Devis D-2026-042",
            primary_confidence=1.0,
            secondary_value=500.00,
            secondary_source="document_ocr_789",
            secondary_label="Document OCR (devis)",
            secondary_confidence=0.7,
            tolerance=TOLERANCE_AMOUNT,
        )
        assert field.status == FieldStatus.CONFLICT
        assert field.value == 450.00  # Primary value retained
        assert field.alternatives is not None
        assert len(field.alternatives) == 1
        assert field.alternatives[0]["value"] == 500.00
        assert field.alternatives[0]["source"] == "document_ocr_789"

    def test_sphere_tolerance_no_conflict(self) -> None:
        """5. Sphere difference within 0.25 D should NOT trigger conflict."""
        field = _resolve_field(
            primary_value=2.50,
            primary_source="cosium_prescription_1",
            primary_label="Ordonnance Cosium",
            primary_confidence=0.95,
            secondary_value=2.25,
            secondary_source="document_ocr_123",
            secondary_label="Document OCR (ordonnance)",
            secondary_confidence=0.7,
            tolerance=TOLERANCE_SPHERE,
        )
        assert field.status == FieldStatus.EXTRACTED
        assert field.alternatives is None

    def test_sphere_difference_above_tolerance_triggers_conflict(self) -> None:
        """6. Sphere difference > 0.25 D should trigger CONFLICT."""
        field = _resolve_field(
            primary_value=2.50,
            primary_source="cosium_prescription_1",
            primary_label="Ordonnance Cosium",
            primary_confidence=0.95,
            secondary_value=2.00,
            secondary_source="document_ocr_123",
            secondary_label="Document OCR (ordonnance)",
            secondary_confidence=0.7,
            tolerance=TOLERANCE_SPHERE,
        )
        assert field.status == FieldStatus.CONFLICT
        assert field.alternatives is not None
        assert field.alternatives[0]["value"] == 2.00

    def test_amount_tolerance_within_1_eur(self) -> None:
        """7. Amount difference within 1 EUR should NOT trigger conflict."""
        field = _resolve_field(
            primary_value=450.00,
            primary_source="devis_42",
            primary_label="Devis D-2026-042",
            primary_confidence=1.0,
            secondary_value=450.80,
            secondary_source="document_ocr_789",
            secondary_label="Document OCR (devis)",
            secondary_confidence=0.7,
            tolerance=TOLERANCE_AMOUNT,
        )
        assert field.status == FieldStatus.EXTRACTED
        assert field.alternatives is None

    def test_manual_correction_sets_manual_status(self) -> None:
        """8. A manually corrected field should have status=MANUAL."""
        field = _make_field(
            value="Dupont-Martin",
            source="manual",
            source_label="Correction manuelle",
            confidence=1.0,
            status=FieldStatus.MANUAL,
        )
        assert field.status == FieldStatus.MANUAL
        assert field.value == "Dupont-Martin"
        assert field.source == "manual"


class TestOpticalValidation:
    """Tests for optical value range validation in incoherence detector."""

    def test_sphere_out_of_range_produces_error(self) -> None:
        """9. Sphere value outside -25/+25 should produce an error alert."""
        profile = ConsolidatedClientProfile()
        profile.sphere_od = _make_field(
            value=30.0,
            source="cosium_prescription_1",
            source_label="Ordonnance Cosium",
            confidence=0.95,
            status=FieldStatus.EXTRACTED,
        )
        alerts = detect_optical_incoherences(profile)
        sphere_alerts = [a for a in alerts if a.field == "sphere_od"]
        assert len(sphere_alerts) == 1
        assert sphere_alerts[0].severity == "error"
        assert "hors plage" in sphere_alerts[0].message

    def test_valid_optical_values_no_error(self) -> None:
        """10. Valid optical values within range should produce no range errors."""
        profile = ConsolidatedClientProfile()
        profile.sphere_od = _make_field(-2.50, "cosium_prescription_1", "Ordonnance Cosium", 0.95, FieldStatus.EXTRACTED)
        profile.sphere_og = _make_field(-3.00, "cosium_prescription_1", "Ordonnance Cosium", 0.95, FieldStatus.EXTRACTED)
        profile.cylinder_od = _make_field(-1.25, "cosium_prescription_1", "Ordonnance Cosium", 0.95, FieldStatus.EXTRACTED)
        profile.cylinder_og = _make_field(-0.75, "cosium_prescription_1", "Ordonnance Cosium", 0.95, FieldStatus.EXTRACTED)
        profile.axis_od = _make_field(90, "cosium_prescription_1", "Ordonnance Cosium", 0.95, FieldStatus.EXTRACTED)
        profile.axis_og = _make_field(85, "cosium_prescription_1", "Ordonnance Cosium", 0.95, FieldStatus.EXTRACTED)
        profile.addition_od = _make_field(2.00, "cosium_prescription_1", "Ordonnance Cosium", 0.95, FieldStatus.EXTRACTED)
        profile.addition_og = _make_field(2.00, "cosium_prescription_1", "Ordonnance Cosium", 0.95, FieldStatus.EXTRACTED)
        profile.ecart_pupillaire = _make_field(63.0, "document_ocr_1", "Document OCR", 0.7, FieldStatus.DEDUCED)

        alerts = detect_optical_incoherences(profile)
        # No range errors expected — only check for hors plage alerts
        range_alerts = [a for a in alerts if "hors plage" in a.message]
        assert len(range_alerts) == 0


class TestFieldStatusAlerts:
    """Test that detect_incoherences uses field status for alerts."""

    def test_conflict_field_generates_warning(self) -> None:
        """CONFLICT field should generate a warning alert."""
        profile = ConsolidatedClientProfile()
        profile.montant_ttc = ConsolidatedField(
            value=450.00,
            source="devis_42",
            source_label="Devis D-2026-042",
            confidence=1.0,
            status=FieldStatus.CONFLICT,
            alternatives=[{"value": 500.00, "source": "document_ocr_789", "confidence": 0.7}],
        )
        alerts = detect_incoherences(profile)
        conflict_alerts = [a for a in alerts if a.field == "montant_ttc" and "Conflit" in a.message]
        assert len(conflict_alerts) >= 1
        assert conflict_alerts[0].severity == "warning"

    def test_deduced_field_generates_info(self) -> None:
        """DEDUCED field should generate an info alert."""
        profile = ConsolidatedClientProfile()
        profile.sphere_od = ConsolidatedField(
            value=-2.50,
            source="document_ocr_123",
            source_label="Document OCR (ordonnance)",
            confidence=0.7,
            status=FieldStatus.DEDUCED,
        )
        alerts = detect_incoherences(profile)
        deduced_alerts = [a for a in alerts if a.field == "sphere_od" and "deduit" in a.message]
        assert len(deduced_alerts) >= 1
        assert deduced_alerts[0].severity == "info"
