"""Tests for PEC pre-control, audit trail, document validation, and enhanced business rules.

8 tests covering:
1. Pre-control "pret" with full data
2. Pre-control "incomplet" with missing fields
3. Pre-control "conflits" with conflicting sources
4. Pre-control "validation_requise" with many deduced fields
5. Audit trail records all actions
6. Audit trail endpoint returns entries
7. Required document check blocks submit without ordonnance
8. Business rule: reste_a_charge > TTC -> error
"""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
    FieldStatus,
)
from app.models.pec_audit import PecAuditEntry
from app.models.pec_preparation import PecPreparation, PecPreparationDocument
from app.models.tenant import Organization, Tenant
from app.repositories import pec_audit_repo
from app.services.incoherence_detector import (
    detect_financial_incoherences,
    detect_incoherences,
)
from app.services.pec_precontrol import PreControlResult, run_precontrol


def _make_field(
    value: object,
    source: str = "cosium_client",
    status: FieldStatus = FieldStatus.EXTRACTED,
    confidence: float = 1.0,
) -> ConsolidatedField:
    return ConsolidatedField(
        value=value,
        source=source,
        source_label=source,
        confidence=confidence,
        status=status,
    )


def _make_conflict_field(value: object) -> ConsolidatedField:
    return ConsolidatedField(
        value=value,
        source="cosium_client",
        source_label="Cosium",
        confidence=0.5,
        status=FieldStatus.CONFLICT,
        alternatives=[{"value": "other", "source": "ocr"}],
    )


def _make_deduced_field(value: object) -> ConsolidatedField:
    return ConsolidatedField(
        value=value,
        source="ocr_123",
        source_label="OCR document",
        confidence=0.7,
        status=FieldStatus.DEDUCED,
    )


def _full_profile() -> ConsolidatedClientProfile:
    """Create a fully complete profile with no issues."""
    return ConsolidatedClientProfile(
        nom=_make_field("Dupont"),
        prenom=_make_field("Jean"),
        date_naissance=_make_field("1975-06-15"),
        numero_secu=_make_field("1750615123456"),
        mutuelle_nom=_make_field("MGEN"),
        mutuelle_numero_adherent=_make_field("ADH123456"),
        mutuelle_code_organisme=_make_field("MGEN01"),
        type_beneficiaire=_make_field("assure"),
        date_fin_droits=_make_field("2027-12-31"),
        sphere_od=_make_field(-2.50),
        cylinder_od=_make_field(-0.75),
        axis_od=_make_field(90),
        addition_od=_make_field(1.50),
        sphere_og=_make_field(-2.00),
        cylinder_og=_make_field(-1.00),
        axis_og=_make_field(85),
        addition_og=_make_field(1.50),
        ecart_pupillaire=_make_field(63.0),
        prescripteur=_make_field("Dr Martin"),
        date_ordonnance=_make_field("2026-03-01"),
        monture=_make_field("Ray-Ban RB5154"),
        montant_ttc=_make_field(850.00),
        part_secu=_make_field(60.00),
        part_mutuelle=_make_field(400.00),
        reste_a_charge=_make_field(390.00),
        score_completude=95.0,
        alertes=[],
    )


@pytest.fixture
def db_session():
    """Create an in-memory database session for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    # Seed org + tenant
    org = Organization(name="Test Org", slug="test-org", plan="solo")
    session.add(org)
    session.flush()
    tenant = Tenant(organization_id=org.id, name="Test", slug="test")
    session.add(tenant)
    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _create_prep(
    db_session,
    profile: ConsolidatedClientProfile | None = None,
    status: str = "prete",
    with_docs: bool = True,
) -> PecPreparation:
    """Helper to create a PecPreparation in the test DB."""
    tenant = db_session.query(Tenant).first()
    prep = PecPreparation(
        tenant_id=tenant.id,
        customer_id=1,
        status=status,
        completude_score=95.0 if profile else 0.0,
        errors_count=0,
        warnings_count=0,
        consolidated_data=profile.model_dump_json() if profile else None,
        created_by=1,
    )
    db_session.add(prep)
    db_session.flush()

    if with_docs:
        for role in ("ordonnance", "devis", "attestation_mutuelle"):
            doc = PecPreparationDocument(
                preparation_id=prep.id,
                document_role=role,
            )
            db_session.add(doc)
        db_session.flush()

    db_session.commit()
    db_session.refresh(prep)
    return prep


class TestPreControl:
    """Tests 1-4: Pre-control status determination."""

    def test_precontrol_pret_full_data(self, db_session) -> None:
        """1. Pre-control returns 'pret' when all data is complete and no issues."""
        profile = _full_profile()
        prep = _create_prep(db_session, profile=profile, with_docs=True)

        result = run_precontrol(prep)

        assert result.status == "pret"
        assert result.status_label == "Dossier pret"
        assert result.completude_score == 95.0
        assert len(result.erreurs_bloquantes) == 0
        assert "ordonnance" in result.pieces_presentes
        assert "devis" in result.pieces_presentes
        assert len(result.pieces_manquantes) == 0

    def test_precontrol_incomplet_missing_fields(self, db_session) -> None:
        """2. Pre-control returns 'incomplet' when required fields are missing."""
        profile = ConsolidatedClientProfile(
            nom=_make_field("Dupont"),
            prenom=_make_field("Jean"),
            # Missing: date_naissance, numero_secu, mutuelle_nom, date_ordonnance, montant_ttc
            score_completude=20.0,
        )
        prep = _create_prep(db_session, profile=profile, with_docs=True)

        result = run_precontrol(prep)

        assert result.status == "incomplet"
        assert result.status_label == "Dossier incomplet"
        assert len(result.erreurs_bloquantes) > 0
        # Check specific missing fields
        blocking_text = " ".join(result.erreurs_bloquantes)
        assert "Date de naissance" in blocking_text
        assert "securite sociale" in blocking_text
        assert "Mutuelle" in blocking_text

    def test_precontrol_conflits_with_conflicts(self, db_session) -> None:
        """3. Pre-control returns 'conflits' when there are conflicting sources and blocking errors."""
        profile = _full_profile()
        # Add conflict fields -- need to also introduce a blocking error
        profile.numero_secu = None  # Missing required field = blocking error
        profile.nom = _make_conflict_field("Dupont")
        profile.prenom = _make_conflict_field("Jean")
        # Re-run incoherence detection to populate alerts
        alerts = detect_incoherences(profile)
        profile.alertes = alerts

        prep = _create_prep(db_session, profile=profile, with_docs=True)

        result = run_precontrol(prep)

        assert result.status == "conflits"
        assert result.champs_en_conflit >= 2

    def test_precontrol_validation_requise_many_deduced(self, db_session) -> None:
        """4. Pre-control returns 'validation_requise' when many fields are deduced."""
        profile = _full_profile()
        # Make 4+ fields deduced
        profile.nom = _make_deduced_field("Dupont")
        profile.prenom = _make_deduced_field("Jean")
        profile.date_naissance = _make_deduced_field("1975-06-15")
        profile.numero_secu = _make_deduced_field("1750615123456")
        profile.mutuelle_nom = _make_deduced_field("MGEN")
        profile.score_completude = 80.0

        prep = _create_prep(db_session, profile=profile, with_docs=True)

        result = run_precontrol(prep)

        assert result.status == "validation_requise"
        assert result.status_label == "Validation requise"
        assert result.champs_deduits >= 4


class TestAuditTrail:
    """Tests 5-6: Audit trail recording and retrieval."""

    def test_audit_trail_records_actions(self, db_session) -> None:
        """5. Audit trail records all types of actions."""
        tenant = db_session.query(Tenant).first()
        profile = _full_profile()
        prep = _create_prep(db_session, profile=profile, with_docs=True)

        # Create various audit entries
        pec_audit_repo.create(
            db_session, tenant.id, prep.id, "created", user_id=1,
            new_value={"customer_id": 1},
        )
        pec_audit_repo.create(
            db_session, tenant.id, prep.id, "field_validated", user_id=1,
            field_name="nom",
        )
        pec_audit_repo.create(
            db_session, tenant.id, prep.id, "field_corrected", user_id=1,
            field_name="prenom", old_value="Jan", new_value="Jean",
        )
        pec_audit_repo.create(
            db_session, tenant.id, prep.id, "refreshed", user_id=1,
        )
        pec_audit_repo.create(
            db_session, tenant.id, prep.id, "document_attached", user_id=1,
            field_name="ordonnance",
        )
        pec_audit_repo.create(
            db_session, tenant.id, prep.id, "submitted", user_id=1,
        )
        db_session.commit()

        entries = pec_audit_repo.list_by_preparation(
            db_session, prep.id, tenant.id,
        )

        assert len(entries) == 6
        actions = {e.action for e in entries}
        assert actions == {
            "created", "field_validated", "field_corrected",
            "refreshed", "document_attached", "submitted",
        }

    def test_audit_trail_entries_have_correct_data(self, db_session) -> None:
        """6. Audit trail entries contain the expected field data."""
        tenant = db_session.query(Tenant).first()
        profile = _full_profile()
        prep = _create_prep(db_session, profile=profile, with_docs=True)

        pec_audit_repo.create(
            db_session, tenant.id, prep.id, "field_corrected", user_id=42,
            field_name="nom", old_value="Dupon", new_value="Dupont", source="manual",
        )
        db_session.commit()

        entries = pec_audit_repo.list_by_preparation(
            db_session, prep.id, tenant.id,
        )

        assert len(entries) == 1
        entry = entries[0]
        assert entry.action == "field_corrected"
        assert entry.field_name == "nom"
        assert entry.user_id == 42
        assert entry.source == "manual"
        assert json.loads(entry.old_value) == "Dupon"
        assert json.loads(entry.new_value) == "Dupont"
        assert entry.created_at is not None


class TestDocumentValidation:
    """Test 7: Required document check."""

    def test_submit_blocked_without_ordonnance(self, db_session) -> None:
        """7. Pre-control flags missing ordonnance as blocking error."""
        profile = _full_profile()
        prep = _create_prep(db_session, profile=profile, with_docs=False)

        # Only attach devis (no ordonnance)
        doc = PecPreparationDocument(
            preparation_id=prep.id,
            document_role="devis",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(prep)

        result = run_precontrol(prep)

        assert "ordonnance" in result.pieces_manquantes
        blocking_text = " ".join(result.erreurs_bloquantes)
        assert "Ordonnance" in blocking_text
        assert result.status in ("incomplet", "conflits")


class TestBusinessRules:
    """Test 8: Enhanced financial business rules."""

    def test_reste_a_charge_exceeds_ttc_is_error(self) -> None:
        """8. reste_a_charge > montant_ttc produces an error alert."""
        profile = ConsolidatedClientProfile(
            montant_ttc=_make_field(500.00),
            reste_a_charge=_make_field(600.00),
        )

        alerts = detect_financial_incoherences(profile)

        error_alerts = [a for a in alerts if a.severity == "error"]
        assert len(error_alerts) >= 1
        assert any(
            "reste a charge" in a.message.lower() and "depasse" in a.message.lower()
            for a in error_alerts
        )

    def test_low_amount_warning(self) -> None:
        """Montant < 50 EUR generates a warning."""
        profile = ConsolidatedClientProfile(
            montant_ttc=_make_field(30.00),
        )

        alerts = detect_financial_incoherences(profile)

        warnings = [a for a in alerts if a.severity == "warning"]
        assert any("inhabituellement bas" in a.message for a in warnings)

    def test_high_amount_warning(self) -> None:
        """Montant > 5000 EUR generates a warning."""
        profile = ConsolidatedClientProfile(
            montant_ttc=_make_field(6000.00),
        )

        alerts = detect_financial_incoherences(profile)

        warnings = [a for a in alerts if a.severity == "warning"]
        assert any("inhabituellement eleve" in a.message for a in warnings)

    def test_part_secu_exceeds_60_percent(self) -> None:
        """Part secu > 60% of TTC generates a warning."""
        profile = ConsolidatedClientProfile(
            montant_ttc=_make_field(500.00),
            part_secu=_make_field(350.00),  # 70%
        )

        alerts = detect_financial_incoherences(profile)

        warnings = [a for a in alerts if a.severity == "warning"]
        assert any("60%" in a.message for a in warnings)
