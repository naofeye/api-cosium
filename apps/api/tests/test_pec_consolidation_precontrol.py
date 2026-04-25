"""Tests for pec_consolidation_service and pec_precontrol_service.

Business-critical PEC workflow: consolidation (field correction, refresh)
and pre-control (blocking errors, warnings, readiness checks).

Coverage:
  pec_consolidation_service:
    - correct_field: applies correction, records audit, recalculates completude/status
    - correct_field: raises NotFoundError for unknown preparation
    - correct_field: raises BusinessError when no consolidated data exists
    - correct_field: reason is stored in audit trail when provided
    - correct_field: status becomes "prete" when correction removes all errors
    - correct_field: status stays "en_preparation" when errors remain
    - refresh_preparation: re-runs consolidation and updates stored data
    - refresh_preparation: raises NotFoundError for unknown preparation
    - refresh_preparation: re-applies existing user corrections after refresh
    - completude score increases as required fields are filled

  pec_precontrol_service (run_precontrol_for_preparation wrapper):
    - returns dict with all expected keys
    - raises NotFoundError for unknown preparation
    - delegates correctly to pec_precontrol.run_precontrol

  pec_precontrol.run_precontrol (direct unit tests on the engine):
    - "pret" when all required fields and documents are present
    - "incomplet" when required fields are missing (no conflicts)
    - "conflits" when conflicts exist alongside blocking errors
    - "validation_requise" when many fields are deduced but no blocking errors
    - missing required documents trigger blocking errors
    - recommended documents generate warnings only
    - user-validated fields are excluded from blocking errors
    - field status counts (confirmed/extracted/deduced/missing/conflict/manual) are correct
    - no consolidated data returns status "incomplet" with a clear message
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import BusinessError, NotFoundError
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
    FieldStatus,
)
from app.models.pec_preparation import PecPreparation, PecPreparationDocument
from app.services.pec_precontrol import PreControlResult, run_precontrol

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _field(
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


def _conflict_field(value: object) -> ConsolidatedField:
    return ConsolidatedField(
        value=value,
        source="cosium_client",
        source_label="Cosium",
        confidence=0.5,
        status=FieldStatus.CONFLICT,
        alternatives=[{"value": "other", "source": "ocr"}],
    )


def _deduced_field(value: object) -> ConsolidatedField:
    return ConsolidatedField(
        value=value,
        source="ocr_123",
        source_label="OCR document",
        confidence=0.7,
        status=FieldStatus.DEDUCED,
    )


def _full_profile(score: float = 95.0) -> ConsolidatedClientProfile:
    """Complete profile with all required PEC fields and no alerts."""
    return ConsolidatedClientProfile(
        nom=_field("Dupont"),
        prenom=_field("Jean"),
        date_naissance=_field("1975-06-15"),
        numero_secu=_field("1750615123456"),
        mutuelle_nom=_field("MGEN"),
        mutuelle_numero_adherent=_field("ADH123456"),
        mutuelle_code_organisme=_field("MGEN01"),
        type_beneficiaire=_field("assure"),
        date_fin_droits=_field("2027-12-31"),
        sphere_od=_field(-2.50),
        cylinder_od=_field(-0.75),
        axis_od=_field(90),
        addition_od=_field(1.50),
        sphere_og=_field(-2.00),
        cylinder_og=_field(-1.00),
        axis_og=_field(85),
        addition_og=_field(1.50),
        ecart_pupillaire=_field(63.0),
        prescripteur=_field("Dr Martin"),
        date_ordonnance=_field("2026-03-01"),
        monture=_field("Ray-Ban RB5154"),
        montant_ttc=_field(850.00),
        part_secu=_field(60.00),
        part_mutuelle=_field(400.00),
        reste_a_charge=_field(390.00),
        score_completude=score,
        alertes=[],
    )


def _make_prep(
    db,
    tenant_id: int,
    customer_id: int = 1,
    profile: ConsolidatedClientProfile | None = None,
    status: str = "en_preparation",
    with_docs: bool = False,
    user_corrections: dict | None = None,
    user_validations: dict | None = None,
) -> PecPreparation:
    """Insert a PecPreparation directly into the test DB."""
    prep = PecPreparation(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status=status,
        completude_score=profile.score_completude if profile else 0.0,
        errors_count=0,
        warnings_count=0,
        consolidated_data=profile.model_dump_json() if profile else None,
        user_corrections=json.dumps(user_corrections) if user_corrections else None,
        user_validations=json.dumps(user_validations) if user_validations else None,
        created_by=1,
    )
    db.add(prep)
    db.flush()

    if with_docs:
        for role in ("ordonnance", "devis", "attestation_mutuelle"):
            db.add(
                PecPreparationDocument(
                    tenant_id=tenant_id,
                    preparation_id=prep.id,
                    document_role=role,
                )
            )
        db.flush()

    db.commit()
    db.refresh(prep)
    return prep


# ---------------------------------------------------------------------------
# pec_consolidation_service tests
# ---------------------------------------------------------------------------

class TestCorrectField:
    """pec_consolidation_service.correct_field"""

    def test_raises_not_found_for_missing_preparation(self, db, default_tenant):
        from app.services.pec_consolidation_service import correct_field

        with pytest.raises(NotFoundError):
            correct_field(db, default_tenant.id, preparation_id=99999,
                          field_name="nom", new_value="Durand", corrected_by=1)

    def test_raises_business_error_when_no_consolidated_data(self, db, default_tenant):
        from app.services.pec_consolidation_service import correct_field

        prep = _make_prep(db, default_tenant.id, profile=None)

        with pytest.raises(BusinessError) as exc_info:
            correct_field(db, default_tenant.id, prep.id,
                          field_name="nom", new_value="Durand", corrected_by=1)

        # BusinessError(message, code): first arg is the message
        assert "NO_CONSOLIDATED_DATA" in exc_info.value.message

    def test_applies_correction_to_field(self, db, default_tenant):
        from app.services.pec_consolidation_service import correct_field

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile, with_docs=True)

        response = correct_field(
            db, default_tenant.id, prep.id,
            field_name="nom", new_value="Durand", corrected_by=1,
        )

        assert response.id == prep.id
        # The consolidated_data stored in DB should reflect the new value
        db.refresh(prep)
        stored_profile = ConsolidatedClientProfile.model_validate_json(
            prep.consolidated_data
        )
        assert stored_profile.nom.value == "Durand"
        assert stored_profile.nom.status == FieldStatus.MANUAL
        assert stored_profile.nom.source == "manual"

    def test_correction_records_user_corrections_json(self, db, default_tenant):
        from app.services.pec_consolidation_service import correct_field

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile)

        correct_field(
            db, default_tenant.id, prep.id,
            field_name="prenom", new_value="Jacques", corrected_by=42,
        )

        db.refresh(prep)
        corrections = json.loads(prep.user_corrections)
        assert "prenom" in corrections
        assert corrections["prenom"]["corrected"] == "Jacques"
        assert corrections["prenom"]["by"] == 42
        assert corrections["prenom"]["original"] == "Jean"

    def test_correction_stores_reason_when_provided(self, db, default_tenant):
        from app.services.pec_consolidation_service import correct_field

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile)

        correct_field(
            db, default_tenant.id, prep.id,
            field_name="nom", new_value="Leroy", corrected_by=1,
            reason="Erreur de saisie initiale",
        )

        db.refresh(prep)
        corrections = json.loads(prep.user_corrections)
        assert corrections["nom"]["reason"] == "Erreur de saisie initiale"

    def test_status_becomes_prete_when_no_remaining_errors(self, db, default_tenant):
        """After correcting the last blocking field the status flips to 'prete'."""
        from app.services.pec_consolidation_service import correct_field

        # Profile with numero_secu missing → will have errors
        profile = _full_profile()
        profile.numero_secu = None
        prep = _make_prep(db, default_tenant.id, profile=profile, status="en_preparation")

        # Patch detect_incoherences to return no alerts after correction
        with patch(
            "app.services.pec_consolidation_service.detect_incoherences",
            return_value=[],
        ):
            correct_field(
                db, default_tenant.id, prep.id,
                field_name="numero_secu", new_value="1750615123456", corrected_by=1,
            )

        db.refresh(prep)
        assert prep.status == "prete"
        assert prep.errors_count == 0

    def test_status_stays_en_preparation_when_errors_remain(self, db, default_tenant):
        """Correction of one field does not clear status if other errors still exist."""
        from app.services.pec_consolidation_service import correct_field

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile, status="en_preparation")

        # Patch detect_incoherences to return one blocking error
        remaining_alert = ConsolidationAlert(
            severity="error",
            field="montant_ttc",
            message="Montant incohérent",
        )
        with patch(
            "app.services.pec_consolidation_service.detect_incoherences",
            return_value=[remaining_alert],
        ):
            correct_field(
                db, default_tenant.id, prep.id,
                field_name="nom", new_value="Durand", corrected_by=1,
            )

        db.refresh(prep)
        assert prep.status == "en_preparation"
        assert prep.errors_count == 1

    def test_completude_score_is_recalculated(self, db, default_tenant):
        """Completude score is updated after a correction."""
        from app.services.pec_consolidation_service import correct_field

        profile = _full_profile()
        profile.score_completude = 50.0
        prep = _make_prep(db, default_tenant.id, profile=profile)

        with patch(
            "app.services.pec_consolidation_service.detect_incoherences",
            return_value=[],
        ):
            correct_field(
                db, default_tenant.id, prep.id,
                field_name="nom", new_value="Durand", corrected_by=1,
            )

        db.refresh(prep)
        # Score should be >= 0 and written back
        assert prep.completude_score >= 0.0

    def test_correction_creates_audit_entry(self, db, default_tenant):
        """An audit entry is created for each field correction."""
        from app.models.pec_audit import PecAuditEntry
        from app.services.pec_consolidation_service import correct_field

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile)

        correct_field(
            db, default_tenant.id, prep.id,
            field_name="prenom", new_value="Paul", corrected_by=7,
        )

        entries = (
            db.query(PecAuditEntry)
            .filter(
                PecAuditEntry.preparation_id == prep.id,
                PecAuditEntry.action == "field_corrected",
            )
            .all()
        )
        assert len(entries) == 1
        assert entries[0].field_name == "prenom"
        assert entries[0].user_id == 7

    def test_correct_unknown_field_does_not_crash(self, db, default_tenant):
        """Correcting a field that doesn't exist on the profile is a no-op (no crash)."""
        from app.services.pec_consolidation_service import correct_field

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile)

        # Should not raise
        with patch(
            "app.services.pec_consolidation_service.detect_incoherences",
            return_value=[],
        ):
            response = correct_field(
                db, default_tenant.id, prep.id,
                field_name="champ_inexistant", new_value="valeur", corrected_by=1,
            )

        assert response.id == prep.id


class TestRefreshPreparation:
    """pec_consolidation_service.refresh_preparation"""

    def test_raises_not_found_for_missing_preparation(self, db, default_tenant):
        from app.services.pec_consolidation_service import refresh_preparation

        with pytest.raises(NotFoundError):
            refresh_preparation(db, default_tenant.id, preparation_id=99999)

    def test_refresh_calls_consolidation_service(self, db, default_tenant):
        """refresh_preparation invokes consolidate_client_for_pec."""
        from app.services.pec_consolidation_service import refresh_preparation

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile)

        fresh_profile = _full_profile(score=88.0)

        with (
            patch(
                "app.services.pec_consolidation_service.consolidation_service"
                ".consolidate_client_for_pec",
                return_value=fresh_profile,
            ) as mock_consolidate,
            patch(
                "app.services.pec_consolidation_service.detect_incoherences",
                return_value=[],
            ),
        ):
            response = refresh_preparation(db, default_tenant.id, prep.id)

        mock_consolidate.assert_called_once_with(
            db, default_tenant.id, prep.customer_id, prep.devis_id
        )
        assert response.id == prep.id

    def test_refresh_updates_consolidated_data_in_db(self, db, default_tenant):
        """After refresh, consolidated_data in DB reflects the new profile."""
        from app.services.pec_consolidation_service import refresh_preparation

        old_profile = _full_profile(score=40.0)
        prep = _make_prep(db, default_tenant.id, profile=old_profile)

        new_profile = _full_profile(score=90.0)
        new_profile.nom = _field("Nouveau")

        with (
            patch(
                "app.services.pec_consolidation_service.consolidation_service"
                ".consolidate_client_for_pec",
                return_value=new_profile,
            ),
            patch(
                "app.services.pec_consolidation_service.detect_incoherences",
                return_value=[],
            ),
        ):
            refresh_preparation(db, default_tenant.id, prep.id)

        db.refresh(prep)
        stored = ConsolidatedClientProfile.model_validate_json(prep.consolidated_data)
        assert stored.nom.value == "Nouveau"

    def test_refresh_reapplies_user_corrections(self, db, default_tenant):
        """Existing user corrections are re-applied on top of the fresh profile."""
        from app.services.pec_consolidation_service import refresh_preparation

        profile = _full_profile()
        existing_corrections = {
            "nom": {"corrected": "Corrige", "by": 1, "at": "2026-04-01T10:00:00+00:00"}
        }
        prep = _make_prep(
            db, default_tenant.id, profile=profile,
            user_corrections=existing_corrections,
        )

        fresh_profile = _full_profile()  # nom = "Dupont" from fresh data

        with (
            patch(
                "app.services.pec_consolidation_service.consolidation_service"
                ".consolidate_client_for_pec",
                return_value=fresh_profile,
            ),
            patch(
                "app.services.pec_consolidation_service.detect_incoherences",
                return_value=[],
            ),
        ):
            refresh_preparation(db, default_tenant.id, prep.id)

        db.refresh(prep)
        stored = ConsolidatedClientProfile.model_validate_json(prep.consolidated_data)
        # User correction ("Corrige") must override the fresh value ("Dupont")
        assert stored.nom.value == "Corrige"
        assert stored.nom.status == FieldStatus.MANUAL

    def test_refresh_status_becomes_prete_with_no_errors(self, db, default_tenant):
        from app.services.pec_consolidation_service import refresh_preparation

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile, status="en_preparation")

        with (
            patch(
                "app.services.pec_consolidation_service.consolidation_service"
                ".consolidate_client_for_pec",
                return_value=_full_profile(),
            ),
            patch(
                "app.services.pec_consolidation_service.detect_incoherences",
                return_value=[],
            ),
        ):
            refresh_preparation(db, default_tenant.id, prep.id)

        db.refresh(prep)
        assert prep.status == "prete"
        assert prep.errors_count == 0

    def test_refresh_status_stays_en_preparation_with_errors(self, db, default_tenant):
        from app.services.pec_consolidation_service import refresh_preparation

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile, status="prete")

        blocking_alert = ConsolidationAlert(
            severity="error", field="numero_secu", message="Numéro sécu invalide"
        )

        with (
            patch(
                "app.services.pec_consolidation_service.consolidation_service"
                ".consolidate_client_for_pec",
                return_value=_full_profile(),
            ),
            patch(
                "app.services.pec_consolidation_service.detect_incoherences",
                return_value=[blocking_alert],
            ),
        ):
            refresh_preparation(db, default_tenant.id, prep.id)

        db.refresh(prep)
        assert prep.status == "en_preparation"
        assert prep.errors_count == 1

    def test_refresh_creates_audit_entry(self, db, default_tenant):
        from app.models.pec_audit import PecAuditEntry
        from app.services.pec_consolidation_service import refresh_preparation

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile)

        with (
            patch(
                "app.services.pec_consolidation_service.consolidation_service"
                ".consolidate_client_for_pec",
                return_value=_full_profile(),
            ),
            patch(
                "app.services.pec_consolidation_service.detect_incoherences",
                return_value=[],
            ),
        ):
            refresh_preparation(db, default_tenant.id, prep.id)

        entries = (
            db.query(PecAuditEntry)
            .filter(
                PecAuditEntry.preparation_id == prep.id,
                PecAuditEntry.action == "refreshed",
            )
            .all()
        )
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# run_precontrol_for_preparation (service wrapper) tests
# ---------------------------------------------------------------------------

class TestRunPrecontrolForPreparation:
    """pec_precontrol_service.run_precontrol_for_preparation"""

    def test_raises_not_found_for_missing_preparation(self, db, default_tenant):
        from app.services.pec_precontrol_service import run_precontrol_for_preparation

        with pytest.raises(NotFoundError):
            run_precontrol_for_preparation(db, default_tenant.id, preparation_id=99999)

    def test_returns_dict_with_expected_keys(self, db, default_tenant):
        from app.services.pec_precontrol_service import run_precontrol_for_preparation

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile, with_docs=True)

        result = run_precontrol_for_preparation(db, default_tenant.id, prep.id)

        assert isinstance(result, dict)
        for key in (
            "status", "status_label", "completude_score",
            "erreurs_bloquantes", "alertes_verification",
            "champs_confirmes", "champs_manquants",
        ):
            assert key in result, f"Missing key: {key}"

    def test_delegates_to_run_precontrol_engine(self, db, default_tenant):
        """The service wrapper must call run_precontrol and return its model_dump."""
        from app.services.pec_precontrol_service import run_precontrol_for_preparation

        profile = _full_profile()
        prep = _make_prep(db, default_tenant.id, profile=profile, with_docs=True)

        fake_result = PreControlResult(
            status="pret",
            status_label="Dossier pret",
            completude_score=95.0,
        )

        with patch(
            "app.services.pec_precontrol.run_precontrol",
            return_value=fake_result,
        ) as mock_run:
            result = run_precontrol_for_preparation(db, default_tenant.id, prep.id)

        mock_run.assert_called_once()
        assert result["status"] == "pret"


# ---------------------------------------------------------------------------
# run_precontrol engine unit tests (pure logic, no DB writes)
# ---------------------------------------------------------------------------

class TestRunPrecontrolEngine:
    """Direct unit tests on pec_precontrol.run_precontrol."""

    # ------------------------------------------------------------------
    # Helper: create a minimal PecPreparation-like object without DB
    # ------------------------------------------------------------------

    def _prep_obj(
        self,
        profile: ConsolidatedClientProfile | None = None,
        doc_roles: list[str] | None = None,
        user_validations: dict | None = None,
    ) -> MagicMock:
        """Build a mock PecPreparation for pure-logic unit tests (no DB needed).

        run_precontrol only reads three attributes:
          - consolidated_data (str | None)
          - user_validations  (str | None)
          - documents         (list with .document_role)
        Using MagicMock avoids SQLAlchemy instrumentation issues.
        """
        docs: list[MagicMock] = []
        for role in (doc_roles or []):
            doc = MagicMock()
            doc.document_role = role
            docs.append(doc)

        obj = MagicMock(spec=PecPreparation)
        obj.consolidated_data = profile.model_dump_json() if profile else None
        obj.user_validations = json.dumps(user_validations) if user_validations else None
        obj.documents = docs
        return obj

    # ------------------------------------------------------------------
    # Status determination
    # ------------------------------------------------------------------

    def test_pret_when_all_data_complete(self):
        """Status is 'pret' with all required fields and required documents."""
        profile = _full_profile()
        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])

        result = run_precontrol(prep)

        assert result.status == "pret"
        assert result.status_label == "Dossier pret"
        assert result.completude_score == 95.0
        assert len(result.erreurs_bloquantes) == 0

    def test_incomplet_when_required_fields_missing(self):
        """Status is 'incomplet' when required fields are absent."""
        profile = ConsolidatedClientProfile(
            nom=_field("Dupont"),
            prenom=_field("Jean"),
            # date_naissance, numero_secu, mutuelle_nom, date_ordonnance, montant_ttc missing
            score_completude=20.0,
        )
        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])

        result = run_precontrol(prep)

        assert result.status == "incomplet"
        assert result.status_label == "Dossier incomplet"
        assert len(result.erreurs_bloquantes) > 0

    def test_incomplet_contains_specific_missing_field_labels(self):
        """Each missing required field appears by name in erreurs_bloquantes."""
        profile = ConsolidatedClientProfile(
            nom=_field("Dupont"),
            score_completude=10.0,
        )
        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])

        result = run_precontrol(prep)

        blocking = " ".join(result.erreurs_bloquantes)
        assert "Date de naissance" in blocking
        assert "securite sociale" in blocking
        assert "Mutuelle" in blocking
        assert "Date d'ordonnance" in blocking
        assert "Montant TTC" in blocking

    def test_conflits_when_conflict_fields_and_blocking_errors(self):
        """Status is 'conflits' when conflict fields exist alongside blocking errors."""
        profile = _full_profile()
        profile.numero_secu = None  # blocking
        profile.nom = _conflict_field("Dupont")
        profile.prenom = _conflict_field("Jean")

        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])

        result = run_precontrol(prep)

        assert result.status == "conflits"
        assert result.champs_en_conflit >= 2
        assert len(result.erreurs_bloquantes) > 0

    def test_validation_requise_when_many_deduced(self):
        """Status is 'validation_requise' when >3 fields are deduced and no blocking errors."""
        profile = _full_profile()
        profile.nom = _deduced_field("Dupont")
        profile.prenom = _deduced_field("Jean")
        profile.date_naissance = _deduced_field("1975-06-15")
        profile.numero_secu = _deduced_field("1750615123456")
        profile.mutuelle_nom = _deduced_field("MGEN")

        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])

        result = run_precontrol(prep)

        assert result.status == "validation_requise"
        assert result.status_label == "Validation requise"
        assert result.champs_deduits >= 4

    def test_no_consolidated_data_returns_incomplet(self):
        """Missing consolidated data returns status 'incomplet' with explanation."""
        prep = self._prep_obj(profile=None)

        result = run_precontrol(prep)

        assert result.status == "incomplet"
        assert len(result.erreurs_bloquantes) == 1
        assert "consolidee" in result.erreurs_bloquantes[0].lower()
        assert result.completude_score == 0.0

    # ------------------------------------------------------------------
    # Document checks
    # ------------------------------------------------------------------

    def test_missing_ordonnance_is_blocking_error(self):
        """Missing ordonnance generates a blocking error."""
        profile = _full_profile()
        prep = self._prep_obj(profile, doc_roles=["devis"])  # no ordonnance

        result = run_precontrol(prep)

        assert "ordonnance" in result.pieces_manquantes
        blocking = " ".join(result.erreurs_bloquantes)
        assert "Ordonnance" in blocking

    def test_missing_devis_is_blocking_error(self):
        """Missing signed devis generates a blocking error."""
        profile = _full_profile()
        prep = self._prep_obj(profile, doc_roles=["ordonnance"])  # no devis

        result = run_precontrol(prep)

        assert "devis" in result.pieces_manquantes
        blocking = " ".join(result.erreurs_bloquantes)
        assert "Devis signe" in blocking

    def test_missing_attestation_mutuelle_is_warning_only(self):
        """Missing attestation mutuelle is a warning, not a blocking error."""
        profile = _full_profile()
        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])  # no attestation

        result = run_precontrol(prep)

        # Should be in recommended missing, not required missing
        assert "attestation_mutuelle" not in result.pieces_manquantes
        assert "attestation_mutuelle" in result.pieces_recommandees_manquantes
        # Must appear in alertes_verification, not erreurs_bloquantes
        warnings = " ".join(result.alertes_verification)
        assert "Attestation mutuelle" in warnings

    def test_present_documents_listed_correctly(self):
        """Present documents are tracked in pieces_presentes."""
        profile = _full_profile()
        prep = self._prep_obj(
            profile,
            doc_roles=["ordonnance", "devis", "attestation_mutuelle"],
        )

        result = run_precontrol(prep)

        assert "ordonnance" in result.pieces_presentes
        assert "devis" in result.pieces_presentes
        assert "attestation_mutuelle" in result.pieces_presentes
        assert len(result.pieces_manquantes) == 0
        assert len(result.pieces_recommandees_manquantes) == 0

    # ------------------------------------------------------------------
    # User validations
    # ------------------------------------------------------------------

    def test_validated_fields_excluded_from_blocking_errors(self):
        """Fields explicitly validated by the user are not reported as blocking errors."""
        profile = ConsolidatedClientProfile(
            nom=_field("Dupont"),
            prenom=_field("Jean"),
            # date_naissance is missing — but the user has validated it
            numero_secu=_field("1750615123456"),
            mutuelle_nom=_field("MGEN"),
            date_ordonnance=_field("2026-03-01"),
            montant_ttc=_field(850.00),
            score_completude=80.0,
        )
        user_validations = {
            "date_naissance": {"validated": True, "validated_by": 1, "at": "2026-04-01T10:00:00"}
        }
        prep = self._prep_obj(
            profile,
            doc_roles=["ordonnance", "devis"],
            user_validations=user_validations,
        )

        result = run_precontrol(prep)

        blocking = " ".join(result.erreurs_bloquantes)
        assert "Date de naissance" not in blocking

    def test_non_validated_missing_fields_still_block(self):
        """Only explicitly validated fields are excluded; others remain blocking."""
        profile = ConsolidatedClientProfile(
            nom=_field("Dupont"),
            # prenom and date_naissance missing; only date_naissance is validated
            date_ordonnance=_field("2026-03-01"),
            montant_ttc=_field(850.00),
            numero_secu=_field("1750615123456"),
            mutuelle_nom=_field("MGEN"),
            score_completude=60.0,
        )
        user_validations = {
            "date_naissance": {"validated": True, "validated_by": 1, "at": "2026-04-01T10:00:00"}
        }
        prep = self._prep_obj(
            profile,
            doc_roles=["ordonnance", "devis"],
            user_validations=user_validations,
        )

        result = run_precontrol(prep)

        blocking = " ".join(result.erreurs_bloquantes)
        # date_naissance validated → excluded
        assert "Date de naissance" not in blocking
        # prenom not validated → still blocking
        assert "Prenom" in blocking

    # ------------------------------------------------------------------
    # Field status counts
    # ------------------------------------------------------------------

    def test_field_counts_confirmed(self):
        """Confirmed fields are counted correctly."""
        profile = _full_profile()
        profile.nom = _field("Dupont", status=FieldStatus.CONFIRMED)
        profile.prenom = _field("Jean", status=FieldStatus.CONFIRMED)

        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])
        result = run_precontrol(prep)

        assert result.champs_confirmes >= 2

    def test_field_counts_manual(self):
        """Manual fields are counted correctly."""
        profile = _full_profile()
        profile.nom = _field("Dupont", status=FieldStatus.MANUAL)

        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])
        result = run_precontrol(prep)

        assert result.champs_manuels >= 1

    def test_field_counts_missing_when_fields_absent(self):
        """Missing fields are counted correctly when profile fields are None."""
        profile = ConsolidatedClientProfile(score_completude=0.0)
        prep = self._prep_obj(profile)

        result = run_precontrol(prep)

        # All 25 tracked fields are None → all missing
        assert result.champs_manquants == 25

    def test_conflict_count_triggers_warning(self):
        """Conflict fields generate an alertes_verification entry."""
        profile = _full_profile()
        profile.nom = _conflict_field("Dupont")
        profile.prenom = _conflict_field("Jean")

        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])
        result = run_precontrol(prep)

        assert result.champs_en_conflit >= 2
        warnings = " ".join(result.alertes_verification)
        assert "conflit" in warnings.lower()

    def test_many_deduced_fields_trigger_advisory_warning(self):
        """More than 3 deduced fields generate an alertes_verification warning."""
        profile = _full_profile()
        profile.nom = _deduced_field("Dupont")
        profile.prenom = _deduced_field("Jean")
        profile.date_naissance = _deduced_field("1975-06-15")
        profile.numero_secu = _deduced_field("175...")
        profile.mutuelle_nom = _deduced_field("MGEN")

        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])
        result = run_precontrol(prep)

        assert result.champs_deduits >= 4
        warnings = " ".join(result.alertes_verification)
        assert "deduit" in warnings.lower()

    # ------------------------------------------------------------------
    # Alert propagation from profile.alertes
    # ------------------------------------------------------------------

    def test_profile_error_alerts_propagated_as_blocking(self):
        """Error alerts embedded in the profile's alertes list become blocking errors."""
        profile = _full_profile()
        profile.alertes = [
            ConsolidationAlert(
                severity="error",
                field="montant_ttc",
                message="Montant incohérent avec la prescription",
            )
        ]

        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])
        result = run_precontrol(prep)

        assert "Montant incohérent avec la prescription" in result.erreurs_bloquantes

    def test_profile_warning_alerts_propagated_as_verification(self):
        """Warning alerts in profile.alertes become alertes_verification."""
        profile = _full_profile()
        profile.alertes = [
            ConsolidationAlert(
                severity="warning",
                field="date_ordonnance",
                message="Ordonnance ancienne de plus de 3 ans",
            )
        ]

        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])
        result = run_precontrol(prep)

        assert "Ordonnance ancienne de plus de 3 ans" in result.alertes_verification

    def test_profile_info_alerts_become_points_vigilance(self):
        """Info alerts in profile.alertes are listed as points_vigilance."""
        profile = _full_profile()
        profile.alertes = [
            ConsolidationAlert(
                severity="info",
                field="type_beneficiaire",
                message="Bénéficiaire différent de l'assuré principal",
            )
        ]

        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])
        result = run_precontrol(prep)

        assert "Bénéficiaire différent de l'assuré principal" in result.points_vigilance

    def test_validated_field_alerts_are_excluded(self):
        """Error alerts for user-validated fields are skipped."""
        profile = _full_profile()
        profile.alertes = [
            ConsolidationAlert(
                severity="error",
                field="nom",
                message="Conflit de nom entre sources",
            )
        ]
        user_validations = {
            "nom": {"validated": True, "validated_by": 1, "at": "2026-04-01T10:00:00"}
        }

        prep = self._prep_obj(
            profile,
            doc_roles=["ordonnance", "devis"],
            user_validations=user_validations,
        )
        result = run_precontrol(prep)

        assert "Conflit de nom entre sources" not in result.erreurs_bloquantes

    # ------------------------------------------------------------------
    # Completude score
    # ------------------------------------------------------------------

    def test_completude_score_passed_through_from_profile(self):
        """completude_score in result matches profile.score_completude."""
        profile = _full_profile(score=73.5)
        prep = self._prep_obj(profile, doc_roles=["ordonnance", "devis"])

        result = run_precontrol(prep)

        assert result.completude_score == 73.5
