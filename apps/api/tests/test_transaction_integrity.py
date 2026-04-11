"""Tests that verify services properly commit after write operations.

These tests catch the exact class of bug where a service performs writes
(inserts, updates, deletes) but forgets to call db.commit(), leaving
data in session.new or session.dirty and never persisting it.

After each write service call, we assert:
  - len(db.new) == 0  (no pending inserts)
  - len(db.dirty) == 0  (no pending updates)
"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.schemas.cases import CaseCreate
from app.domain.schemas.client_mutuelle import ClientMutuelleCreate
from app.domain.schemas.consolidation import (
    ConsolidatedClientProfile,
    ConsolidatedField,
    FieldStatus,
)
from app.domain.schemas.interactions import InteractionCreate
from app.domain.schemas.pec import (
    PayerOrgCreate,
    PecCreate,
    PecStatusUpdate,
    RelanceCreate,
)
from app.models import Case, Customer, Tenant
from app.models.pec_preparation import PecPreparation
from app.services import (
    case_service,
    client_mutuelle_service,
    interaction_service,
    pec_preparation_service,
    pec_service,
)
from app.services.pec_consolidation_service import correct_field
from app.services.pec_precontrol_service import add_document


def _get_tenant(db: Session) -> Tenant:
    return db.query(Tenant).filter(Tenant.slug == "test-magasin").first()


def _make_customer(db: Session, tenant_id: int) -> Customer:
    c = Customer(tenant_id=tenant_id, first_name="Integrity", last_name="Test")
    db.add(c)
    db.flush()
    return c


def _make_case(db: Session, tenant_id: int, customer_id: int) -> Case:
    case = Case(tenant_id=tenant_id, customer_id=customer_id, status="draft")
    db.add(case)
    db.flush()
    return case


def _assert_committed(db: Session) -> None:
    """Assert session has no pending new or dirty objects."""
    assert len(db.new) == 0, (
        f"Session has {len(db.new)} pending new object(s) — db.commit() was missed"
    )
    assert len(db.dirty) == 0, (
        f"Session has {len(db.dirty)} dirty object(s) — db.commit() was missed"
    )


def _make_profile() -> ConsolidatedClientProfile:
    """Build a minimal profile for PEC preparation tests."""
    return ConsolidatedClientProfile(
        nom=ConsolidatedField(
            value="Test", source="cosium", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        prenom=ConsolidatedField(
            value="Integrity", source="cosium", source_label="Cosium",
            confidence=1.0, status=FieldStatus.CONFIRMED,
        ),
        score_completude=70.0,
    )


# ---------------------------------------------------------------------------
# case_service
# ---------------------------------------------------------------------------


class TestCaseServiceCommits:
    """Verify case_service.create_case commits properly."""

    def test_create_case_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        payload = CaseCreate(
            first_name="Alice", last_name="Dupont",
            phone="0612345678", source="manual",
        )
        case_service.create_case(db, tenant.id, payload, seed_user.id)
        _assert_committed(db)


# ---------------------------------------------------------------------------
# interaction_service
# ---------------------------------------------------------------------------


class TestInteractionServiceCommits:
    """Verify interaction_service write operations commit properly."""

    def test_add_interaction_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)
        db.commit()

        payload = InteractionCreate(
            client_id=customer.id,
            case_id=case.id,
            type="appel",
            direction="entrant",
            subject="Appel de suivi",
            content="Le client a confirme sa venue.",
        )
        interaction_service.add_interaction(db, tenant.id, payload, seed_user.id)
        _assert_committed(db)

    def test_delete_interaction_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)
        db.commit()

        payload = InteractionCreate(
            client_id=customer.id,
            case_id=case.id,
            type="note",
            direction="interne",
            subject="Note interne",
        )
        result = interaction_service.add_interaction(db, tenant.id, payload, seed_user.id)

        interaction_service.delete_interaction(db, tenant.id, result.id, seed_user.id)
        _assert_committed(db)


# ---------------------------------------------------------------------------
# client_mutuelle_service
# ---------------------------------------------------------------------------


class TestClientMutuelleServiceCommits:
    """Verify client_mutuelle_service write operations commit properly."""

    def test_add_client_mutuelle_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        customer = _make_customer(db, tenant.id)
        db.commit()

        payload = ClientMutuelleCreate(
            mutuelle_name="MGEN Test",
            source="manual",
            confidence=1.0,
        )
        client_mutuelle_service.add_client_mutuelle(
            db, tenant.id, customer.id, payload
        )
        _assert_committed(db)

    def test_delete_client_mutuelle_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        customer = _make_customer(db, tenant.id)
        db.commit()

        payload = ClientMutuelleCreate(
            mutuelle_name="Harmonie Test",
            source="manual",
        )
        result = client_mutuelle_service.add_client_mutuelle(
            db, tenant.id, customer.id, payload
        )

        client_mutuelle_service.delete_client_mutuelle(
            db, tenant.id, customer.id, result.id
        )
        _assert_committed(db)


# ---------------------------------------------------------------------------
# pec_service
# ---------------------------------------------------------------------------


class TestPecServiceCommits:
    """Verify pec_service write operations commit properly."""

    def _setup_org_and_case(self, db, tenant_id, user_id):
        org = pec_service.create_organization(
            db, tenant_id,
            PayerOrgCreate(name="MGEN Commit", type="mutuelle", code="MGEN_C"),
            user_id,
        )
        customer = _make_customer(db, tenant_id)
        case = _make_case(db, tenant_id, customer.id)
        return org.id, case.id

    def test_create_organization_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        pec_service.create_organization(
            db, tenant.id,
            PayerOrgCreate(name="Org Commit", type="mutuelle", code="OC1"),
            seed_user.id,
        )
        _assert_committed(db)

    def test_create_pec_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        org_id, case_id = self._setup_org_and_case(db, tenant.id, seed_user.id)

        payload = PecCreate(
            case_id=case_id, organization_id=org_id, montant_demande=300.0
        )
        pec_service.create_pec(db, tenant.id, payload, seed_user.id)
        _assert_committed(db)

    def test_change_status_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        org_id, case_id = self._setup_org_and_case(db, tenant.id, seed_user.id)

        pec = pec_service.create_pec(
            db, tenant.id,
            PecCreate(case_id=case_id, organization_id=org_id, montant_demande=200.0),
            seed_user.id,
        )
        pec_service.change_status(
            db, tenant.id, pec.id,
            PecStatusUpdate(status="en_attente", comment="En cours"),
            seed_user.id,
        )
        _assert_committed(db)

    def test_create_relance_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        org_id, case_id = self._setup_org_and_case(db, tenant.id, seed_user.id)

        pec = pec_service.create_pec(
            db, tenant.id,
            PecCreate(case_id=case_id, organization_id=org_id, montant_demande=100.0),
            seed_user.id,
        )
        payload = RelanceCreate(type="email", contenu="Relance urgente")
        pec_service.create_relance(db, tenant.id, pec.id, payload, seed_user.id)
        _assert_committed(db)


# ---------------------------------------------------------------------------
# pec_preparation_service
# ---------------------------------------------------------------------------


class TestPecPreparationServiceCommits:
    """Verify PEC preparation write operations commit properly."""

    @patch("app.services.pec_preparation_service.consolidation_service")
    @patch("app.services.pec_preparation_service.detect_incoherences")
    def test_prepare_pec_commits(self, mock_detect, mock_consolidation, db, seed_user):
        tenant = _get_tenant(db)
        customer = _make_customer(db, tenant.id)
        db.commit()

        profile = _make_profile()
        mock_consolidation.consolidate_client_for_pec.return_value = profile
        mock_detect.return_value = []

        pec_preparation_service.prepare_pec(
            db, tenant.id, customer.id, user_id=seed_user.id
        )
        _assert_committed(db)

    def test_validate_field_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        customer = _make_customer(db, tenant.id)
        prep = PecPreparation(
            tenant_id=tenant.id, customer_id=customer.id,
            consolidated_data=_make_profile().model_dump_json(),
            status="en_preparation", completude_score=70.0,
            errors_count=0, warnings_count=0,
        )
        db.add(prep)
        db.commit()

        pec_preparation_service.validate_field(
            db, tenant.id, prep.id, "nom", validated_by=seed_user.id
        )
        _assert_committed(db)

    def test_correct_field_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        customer = _make_customer(db, tenant.id)
        prep = PecPreparation(
            tenant_id=tenant.id, customer_id=customer.id,
            consolidated_data=_make_profile().model_dump_json(),
            status="en_preparation", completude_score=70.0,
            errors_count=0, warnings_count=0,
        )
        db.add(prep)
        db.commit()

        correct_field(
            db, tenant.id, prep.id,
            field_name="nom", new_value="Corrected", corrected_by=seed_user.id,
        )
        _assert_committed(db)

    def test_add_document_commits(self, db, seed_user):
        tenant = _get_tenant(db)
        customer = _make_customer(db, tenant.id)
        prep = PecPreparation(
            tenant_id=tenant.id, customer_id=customer.id,
            consolidated_data=_make_profile().model_dump_json(),
            status="en_preparation", completude_score=70.0,
            errors_count=0, warnings_count=0,
        )
        db.add(prep)
        db.commit()

        add_document(
            db, tenant.id, prep.id,
            document_role="ordonnance",
            user_id=seed_user.id,
        )
        _assert_committed(db)
