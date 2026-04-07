"""Tests for PEC preparation workflow — prepare, validate, correct, add_document, precontrol."""

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
    FieldStatus,
)
from app.models import Case, Customer, Tenant
from app.models.pec_preparation import PecPreparation, PecPreparationDocument
from app.services import pec_preparation_service
from app.services.pec_consolidation_service import correct_field
from app.services.pec_precontrol import run_precontrol
from app.services.pec_precontrol_service import add_document, run_precontrol_for_preparation


def _make_customer(db: Session, tenant_id: int) -> Customer:
    c = Customer(tenant_id=tenant_id, first_name="Jean", last_name="Dupont")
    db.add(c)
    db.flush()
    return c


def _make_case(db: Session, tenant_id: int, customer_id: int) -> Case:
    case = Case(tenant_id=tenant_id, customer_id=customer_id, status="draft")
    db.add(case)
    db.flush()
    return case


def _make_profile(
    score: float = 75.0,
    alerts: list[ConsolidationAlert] | None = None,
    nom: str = "Dupont",
    prenom: str = "Jean",
) -> ConsolidatedClientProfile:
    """Build a minimal ConsolidatedClientProfile for testing."""
    return ConsolidatedClientProfile(
        nom=ConsolidatedField(
            value=nom, source="cosium_client", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        prenom=ConsolidatedField(
            value=prenom, source="cosium_client", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        date_naissance=ConsolidatedField(
            value="1985-03-15", source="cosium_client", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        numero_secu=ConsolidatedField(
            value="185031234567890", source="cosium_client", source_label="Cosium",
            confidence=0.9, status=FieldStatus.EXTRACTED,
        ),
        mutuelle_nom=ConsolidatedField(
            value="MGEN", source="document_ocr", source_label="Attestation mutuelle",
            confidence=0.8, status=FieldStatus.EXTRACTED,
        ),
        date_ordonnance=ConsolidatedField(
            value="2026-01-10", source="cosium_prescription", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        montant_ttc=ConsolidatedField(
            value=450.0, source="devis_1", source_label="Devis #1",
            confidence=1.0, status=FieldStatus.EXTRACTED,
        ),
        score_completude=score,
        alertes=alerts or [],
    )


def _make_preparation(
    db: Session,
    tenant_id: int,
    customer_id: int,
    profile: ConsolidatedClientProfile | None = None,
    status: str = "en_preparation",
) -> PecPreparation:
    """Insert a PecPreparation row directly for tests that need it pre-existing."""
    profile = profile or _make_profile()
    prep = PecPreparation(
        tenant_id=tenant_id,
        customer_id=customer_id,
        consolidated_data=profile.model_dump_json(),
        status=status,
        completude_score=profile.score_completude,
        errors_count=0,
        warnings_count=0,
    )
    db.add(prep)
    db.flush()
    return prep


# ---------------------------------------------------------------------------
# prepare_pec
# ---------------------------------------------------------------------------


class TestPreparePec:
    """Tests for pec_preparation_service.prepare_pec."""

    @patch("app.services.pec_preparation_service.consolidation_service")
    @patch("app.services.pec_preparation_service.detect_incoherences")
    def test_prepare_pec_creates_preparation(
        self, mock_detect, mock_consolidation, db, seed_user
    ):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        _make_case(db, tenant.id, customer.id)

        profile = _make_profile(score=80.0, alerts=[])
        mock_consolidation.consolidate_client_for_pec.return_value = profile
        mock_detect.return_value = []

        result = pec_preparation_service.prepare_pec(
            db, tenant.id, customer.id, user_id=seed_user.id
        )

        assert result.id is not None
        assert result.customer_id == customer.id
        assert result.status == "prete"  # no errors => prete
        assert result.completude_score == 80.0

    @patch("app.services.pec_preparation_service.consolidation_service")
    @patch("app.services.pec_preparation_service.detect_incoherences")
    def test_prepare_pec_with_errors_sets_en_preparation(
        self, mock_detect, mock_consolidation, db, seed_user
    ):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)

        alert = ConsolidationAlert(
            severity="error", field="numero_secu",
            message="Numero de secu invalide", sources=["cosium"],
        )
        profile = _make_profile(score=50.0, alerts=[alert])
        mock_consolidation.consolidate_client_for_pec.return_value = profile
        mock_detect.return_value = [alert]

        result = pec_preparation_service.prepare_pec(
            db, tenant.id, customer.id, user_id=seed_user.id
        )

        assert result.status == "en_preparation"
        assert result.errors_count == 1

    def test_prepare_pec_customer_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            pec_preparation_service.prepare_pec(
                db, tenant.id, customer_id=99999, user_id=seed_user.id
            )

    @patch("app.services.pec_preparation_service.consolidation_service")
    @patch("app.services.pec_preparation_service.detect_incoherences")
    def test_prepare_pec_commits_data(
        self, mock_detect, mock_consolidation, db, seed_user
    ):
        """After prepare_pec, data is committed (session.new and session.dirty are empty)."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)

        profile = _make_profile(score=90.0)
        mock_consolidation.consolidate_client_for_pec.return_value = profile
        mock_detect.return_value = []

        pec_preparation_service.prepare_pec(
            db, tenant.id, customer.id, user_id=seed_user.id
        )

        assert len(db.new) == 0, "Session should have no pending new objects after commit"
        assert len(db.dirty) == 0, "Session should have no dirty objects after commit"


# ---------------------------------------------------------------------------
# validate_field
# ---------------------------------------------------------------------------


class TestValidateField:
    """Tests for pec_preparation_service.validate_field."""

    def test_validate_field_marks_field(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _make_preparation(db, tenant.id, customer.id)
        db.commit()

        result = pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "nom", validated_by=seed_user.id
        )

        assert result.user_validations is not None
        assert "nom" in result.user_validations

    def test_validate_field_multiple_fields(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _make_preparation(db, tenant.id, customer.id)
        db.commit()

        pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "nom", validated_by=seed_user.id
        )
        result = pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "prenom", validated_by=seed_user.id
        )

        assert "nom" in result.user_validations
        assert "prenom" in result.user_validations

    def test_validate_field_preparation_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            pec_preparation_service.validate_field(
                db, tenant.id, 99999, "nom", validated_by=seed_user.id
            )

    def test_validate_field_commits(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _make_preparation(db, tenant.id, customer.id)
        db.commit()

        pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "nom", validated_by=seed_user.id
        )

        assert len(db.new) == 0
        assert len(db.dirty) == 0


# ---------------------------------------------------------------------------
# correct_field
# ---------------------------------------------------------------------------


class TestCorrectField:
    """Tests for pec_consolidation_service.correct_field."""

    def test_correct_field_updates_value(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _make_preparation(db, tenant.id, customer.id)
        db.commit()

        result = correct_field(
            db, tenant.id, prep.id,
            field_name="nom",
            new_value="Martin",
            corrected_by=seed_user.id,
            reason="Erreur de saisie Cosium",
        )

        assert result.user_corrections is not None
        assert "nom" in result.user_corrections

    def test_correct_field_recalculates_status(self, db, seed_user):
        """Correcting a field recalculates alerts and may change status."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        profile = _make_profile(score=60.0)
        prep = _make_preparation(
            db, tenant.id, customer.id, profile=profile, status="en_preparation"
        )
        db.commit()

        result = correct_field(
            db, tenant.id, prep.id,
            field_name="numero_secu",
            new_value="285031234567890",
            corrected_by=seed_user.id,
        )

        # Status should be recalculated (prete or en_preparation depending on alerts)
        assert result.status in ("prete", "en_preparation")

    def test_correct_field_preparation_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            correct_field(
                db, tenant.id, 99999,
                field_name="nom", new_value="X", corrected_by=seed_user.id,
            )

    def test_correct_field_no_consolidated_data(self, db, seed_user):
        """Correction without consolidated data should raise BusinessError."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = PecPreparation(
            tenant_id=tenant.id,
            customer_id=customer.id,
            consolidated_data=None,
            status="en_preparation",
            completude_score=0.0,
            errors_count=0,
            warnings_count=0,
        )
        db.add(prep)
        db.commit()

        with pytest.raises(BusinessError):
            correct_field(
                db, tenant.id, prep.id,
                field_name="nom", new_value="Test", corrected_by=seed_user.id,
            )

    def test_correct_field_commits(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _make_preparation(db, tenant.id, customer.id)
        db.commit()

        correct_field(
            db, tenant.id, prep.id,
            field_name="prenom", new_value="Pierre", corrected_by=seed_user.id,
        )

        assert len(db.new) == 0
        assert len(db.dirty) == 0


# ---------------------------------------------------------------------------
# add_document
# ---------------------------------------------------------------------------


class TestAddDocument:
    """Tests for pec_precontrol_service.add_document."""

    def test_add_document_to_preparation(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _make_preparation(db, tenant.id, customer.id)
        db.commit()

        result = add_document(
            db, tenant.id, prep.id,
            document_id=None,
            cosium_document_id=42,
            document_role="ordonnance",
            user_id=seed_user.id,
        )

        assert result.preparation_id == prep.id
        assert result.document_role == "ordonnance"
        assert result.cosium_document_id == 42

    def test_add_document_preparation_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            add_document(
                db, tenant.id, 99999,
                document_role="ordonnance",
                user_id=seed_user.id,
            )

    def test_add_document_creates_audit_entry(self, db, seed_user):
        """Adding a document creates an audit trail entry."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _make_preparation(db, tenant.id, customer.id)
        db.commit()

        add_document(
            db, tenant.id, prep.id,
            cosium_document_id=100,
            document_role="devis",
            user_id=seed_user.id,
        )

        from app.models.pec_audit import PecAuditEntry
        audit_entries = db.query(PecAuditEntry).filter(
            PecAuditEntry.preparation_id == prep.id,
            PecAuditEntry.action == "document_attached",
        ).all()
        assert len(audit_entries) >= 1

    def test_add_document_commits(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _make_preparation(db, tenant.id, customer.id)
        db.commit()

        add_document(
            db, tenant.id, prep.id,
            document_role="attestation_mutuelle",
            user_id=seed_user.id,
        )

        assert len(db.new) == 0
        assert len(db.dirty) == 0


# ---------------------------------------------------------------------------
# run_precontrol
# ---------------------------------------------------------------------------


class TestRunPrecontrol:
    """Tests for the pre-control engine (pec_precontrol.run_precontrol)."""

    def test_precontrol_no_consolidated_data(self, db, seed_user):
        """Without consolidated data, precontrol returns 'incomplet'."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = PecPreparation(
            tenant_id=tenant.id,
            customer_id=customer.id,
            consolidated_data=None,
            status="en_preparation",
            completude_score=0.0,
            errors_count=0,
            warnings_count=0,
        )
        db.add(prep)
        db.flush()

        result = run_precontrol(prep)

        assert result.status == "incomplet"
        assert len(result.erreurs_bloquantes) > 0

    def test_precontrol_complete_profile_with_docs(self, db, seed_user):
        """A complete profile with required docs should return 'pret'."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        profile = _make_profile(score=95.0)
        prep = _make_preparation(db, tenant.id, customer.id, profile=profile)

        # Attach required docs
        for role in ["ordonnance", "devis"]:
            doc = PecPreparationDocument(
                tenant_id=tenant.id,
                preparation_id=prep.id,
                document_role=role,
            )
            db.add(doc)
        db.flush()
        db.refresh(prep)

        result = run_precontrol(prep)

        assert result.status == "pret"
        assert result.completude_score == 95.0

    def test_precontrol_missing_documents(self, db, seed_user):
        """Missing required documents should produce blocking errors."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        profile = _make_profile(score=90.0)
        prep = _make_preparation(db, tenant.id, customer.id, profile=profile)
        db.flush()
        db.refresh(prep)

        result = run_precontrol(prep)

        assert "ordonnance" in result.pieces_manquantes or "devis" in result.pieces_manquantes
        assert len(result.erreurs_bloquantes) > 0

    def test_precontrol_missing_required_fields(self, db, seed_user):
        """Profile missing required fields should have blocking errors."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        # Profile with missing numero_secu and mutuelle_nom
        profile = ConsolidatedClientProfile(
            nom=ConsolidatedField(
                value="Dupont", source="cosium", source_label="Cosium",
                confidence=1.0, status=FieldStatus.CONFIRMED,
            ),
            prenom=ConsolidatedField(
                value="Jean", source="cosium", source_label="Cosium",
                confidence=1.0, status=FieldStatus.CONFIRMED,
            ),
            score_completude=30.0,
        )
        prep = _make_preparation(db, tenant.id, customer.id, profile=profile)
        db.flush()
        db.refresh(prep)

        result = run_precontrol(prep)

        assert result.status in ("incomplet", "conflits")
        assert result.champs_manquants > 0

    def test_precontrol_for_preparation_via_service(self, db, seed_user):
        """run_precontrol_for_preparation returns a dict result."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        profile = _make_profile(score=80.0)
        prep = _make_preparation(db, tenant.id, customer.id, profile=profile)
        db.commit()

        result = run_precontrol_for_preparation(db, tenant.id, prep.id)

        assert isinstance(result, dict)
        assert "status" in result
        assert "completude_score" in result

    def test_precontrol_for_preparation_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            run_precontrol_for_preparation(db, tenant.id, 99999)


# ---------------------------------------------------------------------------
# get_preparation / list
# ---------------------------------------------------------------------------


class TestGetAndListPreparations:
    """Tests for get_preparation and list functions."""

    def test_get_preparation_by_id(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _make_preparation(db, tenant.id, customer.id)
        db.commit()

        result = pec_preparation_service.get_preparation(db, tenant.id, prep.id)

        assert result.id == prep.id
        assert result.customer_id == customer.id

    def test_get_preparation_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            pec_preparation_service.get_preparation(db, tenant.id, 99999)

    def test_list_preparations_for_customer(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        _make_preparation(db, tenant.id, customer.id)
        _make_preparation(db, tenant.id, customer.id)
        db.commit()

        results = pec_preparation_service.list_preparations_for_customer(
            db, tenant.id, customer.id
        )

        assert len(results) == 2

    def test_list_all_preparations(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        _make_preparation(db, tenant.id, customer.id, status="en_preparation")
        _make_preparation(db, tenant.id, customer.id, status="prete")
        db.commit()

        result = pec_preparation_service.list_all_preparations(db, tenant.id)

        assert result["total"] == 2
        assert len(result["items"]) == 2

    def test_list_all_preparations_filter_by_status(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        _make_preparation(db, tenant.id, customer.id, status="en_preparation")
        _make_preparation(db, tenant.id, customer.id, status="prete")
        db.commit()

        result = pec_preparation_service.list_all_preparations(
            db, tenant.id, status="prete"
        )

        assert result["total"] == 1
        assert result["items"][0]["status"] == "prete"
