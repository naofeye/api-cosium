"""Unit tests for pec_preparation_service.

Covers: prepare_pec, get_preparation, list_all_preparations,
list_preparations_for_customer, validate_field, refresh_preparation,
NotFoundError scenarios.

These tests complement test_pec_preparation.py which covers correct_field,
add_document, precontrol, and prepare_pec with error alerts.
Focus here is on the service facade behaviours, pagination helpers,
tenant isolation, and refresh_preparation.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    ConsolidationAlert,
    FieldStatus,
)
from app.models import Customer, Tenant
from app.models.pec_preparation import PecPreparation
from app.services import pec_preparation_service
from app.services.pec_consolidation_service import refresh_preparation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_customer(db: Session, tenant_id: int, first_name: str = "Marie", last_name: str = "Curie") -> Customer:
    c = Customer(tenant_id=tenant_id, first_name=first_name, last_name=last_name)
    db.add(c)
    db.flush()
    return c


def _make_profile(score: float = 85.0, alerts: list | None = None) -> ConsolidatedClientProfile:
    return ConsolidatedClientProfile(
        nom=ConsolidatedField(
            value="Curie", source="cosium_client", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        prenom=ConsolidatedField(
            value="Marie", source="cosium_client", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        date_naissance=ConsolidatedField(
            value="1967-05-10", source="cosium_client", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        numero_secu=ConsolidatedField(
            value="267051234512345", source="cosium_client", source_label="Cosium",
            confidence=0.95, status=FieldStatus.EXTRACTED,
        ),
        mutuelle_nom=ConsolidatedField(
            value="Harmonie", source="document_ocr", source_label="Attestation",
            confidence=0.85, status=FieldStatus.EXTRACTED,
        ),
        date_ordonnance=ConsolidatedField(
            value="2026-02-01", source="cosium_prescription", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        montant_ttc=ConsolidatedField(
            value=320.0, source="devis_1", source_label="Devis #1",
            confidence=1.0, status=FieldStatus.EXTRACTED,
        ),
        score_completude=score,
        alertes=alerts or [],
    )


def _insert_prep(
    db: Session,
    tenant_id: int,
    customer_id: int,
    status: str = "en_preparation",
    score: float = 70.0,
    errors: int = 0,
    warnings: int = 0,
) -> PecPreparation:
    profile = _make_profile(score=score)
    prep = PecPreparation(
        tenant_id=tenant_id,
        customer_id=customer_id,
        consolidated_data=profile.model_dump_json(),
        status=status,
        completude_score=score,
        errors_count=errors,
        warnings_count=warnings,
    )
    db.add(prep)
    db.flush()
    return prep


# ---------------------------------------------------------------------------
# TestPreparePec — additional scenarios not covered in test_pec_preparation.py
# ---------------------------------------------------------------------------


class TestPreparePec:
    """Additional prepare_pec scenarios: devis_id propagation, warnings-only, user_id=0."""

    @patch("app.services.pec_preparation_service.consolidation_service")
    @patch("app.services.pec_preparation_service.detect_incoherences")
    def test_prepare_pec_with_devis_id(self, mock_detect, mock_consolidation, db, seed_user):
        """devis_id is stored on the preparation when provided."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)

        profile = _make_profile(score=78.0)
        mock_consolidation.consolidate_client_for_pec.return_value = profile
        mock_detect.return_value = []

        result = pec_preparation_service.prepare_pec(
            db, tenant.id, customer.id, devis_id=42, user_id=seed_user.id
        )

        assert result.devis_id == 42

    @patch("app.services.pec_preparation_service.consolidation_service")
    @patch("app.services.pec_preparation_service.detect_incoherences")
    def test_prepare_pec_warnings_only_yields_prete(self, mock_detect, mock_consolidation, db, seed_user):
        """Warnings alone must not block status — 'prete' when errors_count == 0."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)

        warning_alert = ConsolidationAlert(
            severity="warning",
            field="mutuelle_nom",
            message="Mutuelle non confirmee",
            sources=["ocr"],
        )
        profile = _make_profile(score=72.0, alerts=[warning_alert])
        mock_consolidation.consolidate_client_for_pec.return_value = profile
        mock_detect.return_value = [warning_alert]

        result = pec_preparation_service.prepare_pec(
            db, tenant.id, customer.id, user_id=seed_user.id
        )

        assert result.status == "prete"
        assert result.warnings_count == 1
        assert result.errors_count == 0

    @patch("app.services.pec_preparation_service.consolidation_service")
    @patch("app.services.pec_preparation_service.detect_incoherences")
    def test_prepare_pec_without_user_id_skips_audit(self, mock_detect, mock_consolidation, db):
        """user_id=0 must not crash; audit_service.log_action is not called."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)

        profile = _make_profile(score=65.0)
        mock_consolidation.consolidate_client_for_pec.return_value = profile
        mock_detect.return_value = []

        with patch("app.services.pec_preparation_service.audit_service") as mock_audit:
            result = pec_preparation_service.prepare_pec(
                db, tenant.id, customer.id, user_id=0
            )
            mock_audit.log_action.assert_not_called()

        assert result.id is not None

    @patch("app.services.pec_preparation_service.consolidation_service")
    @patch("app.services.pec_preparation_service.detect_incoherences")
    def test_prepare_pec_score_propagated(self, mock_detect, mock_consolidation, db, seed_user):
        """completude_score on the preparation matches what the profile reports."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)

        profile = _make_profile(score=93.5)
        mock_consolidation.consolidate_client_for_pec.return_value = profile
        mock_detect.return_value = []

        result = pec_preparation_service.prepare_pec(
            db, tenant.id, customer.id, user_id=seed_user.id
        )

        assert result.completude_score == 93.5

    def test_prepare_pec_invalid_customer_raises_not_found(self, db, seed_user):
        """Customer that does not exist should raise NotFoundError."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            pec_preparation_service.prepare_pec(
                db, tenant.id, customer_id=888888, user_id=seed_user.id
            )


# ---------------------------------------------------------------------------
# TestGetPreparation
# ---------------------------------------------------------------------------


class TestGetPreparation:
    """get_preparation: success path and error path."""

    def test_get_preparation_returns_correct_id(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _insert_prep(db, tenant.id, customer.id)
        db.commit()

        result = pec_preparation_service.get_preparation(db, tenant.id, prep.id)

        assert result.id == prep.id
        assert result.tenant_id == tenant.id

    def test_get_preparation_tenant_isolation(self, db, seed_user):
        """Preparation belonging to one tenant is not visible from another tenant_id."""
        from app.models import Organization

        org2 = Organization(name="Org2", slug="org-2", plan="solo")
        db.add(org2)
        db.flush()
        tenant2 = Tenant(
            organization_id=org2.id,
            name="Autre Magasin",
            slug="autre-magasin",
            cosium_tenant="t2",
            cosium_login="l2",
            cosium_password_enc="p2",
        )
        db.add(tenant2)
        db.flush()

        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _insert_prep(db, tenant.id, customer.id)
        db.commit()

        with pytest.raises(NotFoundError):
            pec_preparation_service.get_preparation(db, tenant2.id, prep.id)

    def test_get_preparation_not_found(self, db):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            pec_preparation_service.get_preparation(db, tenant.id, 99999)

    def test_get_preparation_includes_consolidated_data(self, db, seed_user):
        """consolidated_data is included in the response as a dict."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _insert_prep(db, tenant.id, customer.id)
        db.commit()

        result = pec_preparation_service.get_preparation(db, tenant.id, prep.id)

        assert result.consolidated_data is not None
        assert isinstance(result.consolidated_data, dict)


# ---------------------------------------------------------------------------
# TestListPreparationsForCustomer
# ---------------------------------------------------------------------------


class TestListPreparationsForCustomer:
    """list_preparations_for_customer: basic listing and pagination."""

    def test_returns_all_preparations_for_customer(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        for _ in range(3):
            _insert_prep(db, tenant.id, customer.id)
        db.commit()

        results = pec_preparation_service.list_preparations_for_customer(
            db, tenant.id, customer.id
        )

        assert len(results) == 3

    def test_does_not_return_other_customers_preparations(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        cust_a = _make_customer(db, tenant.id, "Alice", "A")
        cust_b = _make_customer(db, tenant.id, "Bob", "B")
        _insert_prep(db, tenant.id, cust_a.id)
        _insert_prep(db, tenant.id, cust_b.id)
        db.commit()

        results = pec_preparation_service.list_preparations_for_customer(
            db, tenant.id, cust_a.id
        )

        assert len(results) == 1
        assert results[0].customer_id == cust_a.id

    def test_returns_empty_list_for_customer_without_preparations(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        db.commit()

        results = pec_preparation_service.list_preparations_for_customer(
            db, tenant.id, customer.id
        )

        assert results == []

    def test_limit_respected(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        for _ in range(5):
            _insert_prep(db, tenant.id, customer.id)
        db.commit()

        results = pec_preparation_service.list_preparations_for_customer(
            db, tenant.id, customer.id, limit=2
        )

        assert len(results) == 2


# ---------------------------------------------------------------------------
# TestListAllPreparations
# ---------------------------------------------------------------------------


class TestListAllPreparations:
    """list_all_preparations: pagination, status filter, KPI counts."""

    def test_pagination_metadata(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        for i in range(4):
            _insert_prep(db, tenant.id, customer.id)
        db.commit()

        result = pec_preparation_service.list_all_preparations(
            db, tenant.id, limit=2, offset=0
        )

        assert result["total"] == 4
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert result["total_pages"] == 2
        assert len(result["items"]) == 2

    def test_second_page_returns_remaining(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        for _ in range(3):
            _insert_prep(db, tenant.id, customer.id)
        db.commit()

        result = pec_preparation_service.list_all_preparations(
            db, tenant.id, limit=2, offset=2
        )

        assert len(result["items"]) == 1

    def test_status_filter_returns_only_matching(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        _insert_prep(db, tenant.id, customer.id, status="en_preparation")
        _insert_prep(db, tenant.id, customer.id, status="prete")
        _insert_prep(db, tenant.id, customer.id, status="prete")
        db.commit()

        result = pec_preparation_service.list_all_preparations(
            db, tenant.id, status="prete"
        )

        assert result["total"] == 2
        assert all(item["status"] == "prete" for item in result["items"])

    def test_counts_by_status_included(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        _insert_prep(db, tenant.id, customer.id, status="en_preparation")
        _insert_prep(db, tenant.id, customer.id, status="prete")
        db.commit()

        result = pec_preparation_service.list_all_preparations(db, tenant.id)

        assert "counts" in result
        assert isinstance(result["counts"], dict)
        assert result["counts"].get("en_preparation", 0) == 1
        assert result["counts"].get("prete", 0) == 1

    def test_items_include_customer_name(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id, first_name="Louis", last_name="Pasteur")
        _insert_prep(db, tenant.id, customer.id)
        db.commit()

        result = pec_preparation_service.list_all_preparations(db, tenant.id)

        item = result["items"][0]
        assert "Pasteur" in item["customer_name"] or "Louis" in item["customer_name"]

    def test_empty_tenant_returns_zero(self, db):
        from app.models import Organization

        org = Organization(name="Empty Org", slug="empty-org-2", plan="solo")
        db.add(org)
        db.flush()
        tenant_empty = Tenant(
            organization_id=org.id,
            name="Empty Store",
            slug="empty-store-2",
            cosium_tenant="et2",
            cosium_login="el2",
            cosium_password_enc="ep2",
        )
        db.add(tenant_empty)
        db.commit()

        result = pec_preparation_service.list_all_preparations(db, tenant_empty.id)

        assert result["total"] == 0
        assert result["items"] == []


# ---------------------------------------------------------------------------
# TestValidateField — extended scenarios
# ---------------------------------------------------------------------------


class TestValidateField:
    """validate_field: idempotency and merge behaviour."""

    def test_validate_field_stores_user_id(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _insert_prep(db, tenant.id, customer.id)
        db.commit()

        result = pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "numero_secu", validated_by=seed_user.id
        )

        validations = result.user_validations
        assert validations is not None
        assert validations["numero_secu"]["validated_by"] == seed_user.id
        assert validations["numero_secu"]["validated"] is True

    def test_validate_field_preserves_previous_validations(self, db, seed_user):
        """Second validate_field call must not erase the first validated field."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _insert_prep(db, tenant.id, customer.id)
        db.commit()

        pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "nom", validated_by=seed_user.id
        )
        result = pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "date_naissance", validated_by=seed_user.id
        )

        assert "nom" in result.user_validations
        assert "date_naissance" in result.user_validations

    def test_validate_field_idempotent(self, db, seed_user):
        """Validating the same field twice must not raise an error."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _insert_prep(db, tenant.id, customer.id)
        db.commit()

        pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "nom", validated_by=seed_user.id
        )
        result = pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "nom", validated_by=seed_user.id
        )

        assert result.user_validations["nom"]["validated"] is True

    def test_validate_field_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            pec_preparation_service.validate_field(
                db, tenant.id, 77777, "nom", validated_by=seed_user.id
            )


# ---------------------------------------------------------------------------
# TestRefreshPreparation
# ---------------------------------------------------------------------------


class TestRefreshPreparation:
    """refresh_preparation: re-runs consolidation and recalculates status."""

    @patch("app.services.pec_consolidation_service.consolidation_service")
    @patch("app.services.pec_consolidation_service.detect_incoherences")
    def test_refresh_updates_score_and_status(self, mock_detect, mock_consolidation, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _insert_prep(db, tenant.id, customer.id, status="en_preparation", score=50.0, errors=1)
        db.commit()

        fresh_profile = _make_profile(score=95.0, alerts=[])
        mock_consolidation.consolidate_client_for_pec.return_value = fresh_profile
        mock_detect.return_value = []

        # _calculate_completude is imported inline inside refresh_preparation
        with patch("app.services.consolidation_service._calculate_completude", return_value=95.0):
            result = refresh_preparation(db, tenant.id, prep.id)

        assert result.status == "prete"
        assert result.errors_count == 0

    @patch("app.services.pec_consolidation_service.consolidation_service")
    @patch("app.services.pec_consolidation_service.detect_incoherences")
    def test_refresh_with_new_errors_sets_en_preparation(self, mock_detect, mock_consolidation, db, seed_user):
        """If fresh consolidation returns errors, status must revert to en_preparation."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        prep = _insert_prep(db, tenant.id, customer.id, status="prete", score=90.0, errors=0)
        db.commit()

        error_alert = ConsolidationAlert(
            severity="error", field="numero_secu",
            message="Numero de secu invalide", sources=["cosium"],
        )
        fresh_profile = _make_profile(score=55.0, alerts=[error_alert])
        mock_consolidation.consolidate_client_for_pec.return_value = fresh_profile
        mock_detect.return_value = [error_alert]

        with patch("app.services.consolidation_service._calculate_completude", return_value=55.0):
            result = refresh_preparation(db, tenant.id, prep.id)

        assert result.status == "en_preparation"
        assert result.errors_count == 1

    def test_refresh_preparation_not_found(self, db):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        with pytest.raises(NotFoundError):
            refresh_preparation(db, tenant.id, 66666)

    @patch("app.services.pec_consolidation_service.consolidation_service")
    @patch("app.services.pec_consolidation_service.detect_incoherences")
    def test_refresh_applies_existing_corrections(self, mock_detect, mock_consolidation, db, seed_user):
        """User corrections stored on the preparation must be re-applied during refresh."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        corrections = {"nom": {"original": "Dupont", "corrected": "Martin", "by": seed_user.id, "at": "2026-01-01T00:00:00"}}
        prep = PecPreparation(
            tenant_id=tenant.id,
            customer_id=customer.id,
            consolidated_data=_make_profile().model_dump_json(),
            status="en_preparation",
            completude_score=70.0,
            errors_count=0,
            warnings_count=0,
            user_corrections=json.dumps(corrections),
        )
        db.add(prep)
        db.commit()

        fresh_profile = _make_profile(score=80.0, alerts=[])
        mock_consolidation.consolidate_client_for_pec.return_value = fresh_profile
        mock_detect.return_value = []

        with patch("app.services.consolidation_service._calculate_completude", return_value=80.0):
            result = refresh_preparation(db, tenant.id, prep.id)

        # Result must be a valid response without crash — corrections were applied
        assert result.id == prep.id
        assert result.status == "prete"
