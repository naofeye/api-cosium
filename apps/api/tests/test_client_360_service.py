"""Tests for client_360_service — building the 360 view for a customer."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.schemas.client_360 import (
    Client360Response,
    CosiumDataBundle,
    CosiumPrescriptionSummary,
)
from app.models.case import Case
from app.models.client import Customer
from app.models.interaction import Interaction
from app.models.marketing import MarketingConsent
from app.models.tenant import Organization, Tenant
from app.services.client_360_service import get_client_360, get_client_cosium_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def customer(db: Session, default_tenant: Tenant) -> Customer:
    c = Customer(
        tenant_id=default_tenant.id,
        first_name="Alice",
        last_name="Dupont",
        email="alice.dupont@test.fr",
        phone="0612345678",
        birth_date=date(1985, 6, 20),
        city="Paris",
        postal_code="75001",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture()
def customer_with_case(db: Session, default_tenant: Tenant, customer: Customer) -> tuple[Customer, Case]:
    case = Case(
        tenant_id=default_tenant.id,
        customer_id=customer.id,
        status="en_cours",
        source="test",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return customer, case


# ---------------------------------------------------------------------------
# Shared patch context that stubs out all Cosium sub-calls
# ---------------------------------------------------------------------------

def _cosium_patches(
    prescriptions=None,
    invoices=None,
):
    """Return a context manager that patches all Cosium-related sub-service calls."""
    if prescriptions is None:
        prescriptions = []
    if invoices is None:
        invoices = ([], [])  # (summaries, raw)

    return [
        patch(
            "app.services.client_360_service.fetch_cosium_invoices",
            return_value=invoices,
        ),
        patch(
            "app.services.client_360_service.build_prescriptions",
            return_value=(prescriptions, []),
        ),
        patch(
            "app.services.client_360_service.build_correction_actuelle",
            return_value=None,
        ),
        patch(
            "app.services.client_360_service.build_equipments",
            return_value=[],
        ),
        patch(
            "app.services.client_360_service.build_cosium_payments",
            return_value=[],
        ),
        patch(
            "app.services.client_360_service.build_calendar_events",
            return_value=([], []),
        ),
        patch(
            "app.services.client_360_service.compute_total_ca_cosium",
            return_value=0.0,
        ),
        patch(
            "app.services.client_360_service.get_last_visit_date",
            return_value=None,
        ),
        patch(
            "app.services.client_360_service.get_customer_tags",
            return_value=[],
        ),
        patch(
            "app.services.client_360_service.build_ocr_data",
            return_value=None,
        ),
        patch(
            "app.services.client_360_service.client_mutuelle_repo.get_by_customer",
            return_value=[],
        ),
        patch(
            "app.services.client_360_service.build_prescription_warning",
            return_value=None,
        ),
    ]


def _apply_all_patches(patches):
    """Enter a list of patch context managers and return them."""
    entered = []
    for p in patches:
        entered.append(p.__enter__())
    return entered


def _exit_all_patches(patches):
    for p in patches:
        p.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Basic 360 structure tests
# ---------------------------------------------------------------------------

class TestGetClient360Structure:
    def test_returns_client360_response(self, db: Session, default_tenant: Tenant, customer: Customer):
        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert isinstance(result, Client360Response)

    def test_basic_fields_populated(self, db: Session, default_tenant: Tenant, customer: Customer):
        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert result.id == customer.id
        assert result.first_name == "Alice"
        assert result.last_name == "Dupont"
        assert result.email == "alice.dupont@test.fr"
        assert result.phone == "0612345678"
        assert result.birth_date == "1985-06-20"
        assert result.city == "Paris"

    def test_empty_lists_when_no_related_data(self, db: Session, default_tenant: Tenant, customer: Customer):
        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert result.dossiers == []
        assert result.documents == []
        assert result.devis == []
        assert result.factures == []
        assert result.paiements == []
        assert result.pec == []
        assert result.consentements == []
        assert result.interactions == []
        assert result.cosium_invoices == []

    def test_financial_summary_zero_when_no_data(self, db: Session, default_tenant: Tenant, customer: Customer):
        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        fin = result.resume_financier
        assert fin.total_facture == 0.0
        assert fin.total_paye == 0.0
        assert fin.reste_du == 0.0
        assert fin.taux_recouvrement == 0.0

    def test_cosium_data_is_bundle(self, db: Session, default_tenant: Tenant, customer: Customer):
        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert isinstance(result.cosium_data, CosiumDataBundle)


# ---------------------------------------------------------------------------
# Dossiers (cases) section
# ---------------------------------------------------------------------------

class TestGetClient360WithCases:
    def test_dossiers_included(self, db: Session, default_tenant: Tenant, customer_with_case):
        customer, case = customer_with_case
        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert len(result.dossiers) == 1
        dossier = result.dossiers[0]
        assert dossier.id == case.id
        assert dossier.statut == "en_cours"
        assert dossier.source == "test"

    def test_multiple_cases_all_returned(self, db: Session, default_tenant: Tenant, customer: Customer):
        for i in range(3):
            db.add(Case(
                tenant_id=default_tenant.id,
                customer_id=customer.id,
                status="draft",
                source=f"source_{i}",
            ))
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert len(result.dossiers) == 3


# ---------------------------------------------------------------------------
# Interactions section
# ---------------------------------------------------------------------------

class TestGetClient360WithInteractions:
    def test_interactions_included(self, db: Session, default_tenant: Tenant, customer: Customer):
        interaction = Interaction(
            tenant_id=default_tenant.id,
            client_id=customer.id,
            type="note",
            direction="interne",
            subject="Test note",
            content="Some content",
        )
        db.add(interaction)
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert len(result.interactions) == 1
        assert result.interactions[0].subject == "Test note"

    def test_interactions_ordered_most_recent_first(self, db: Session, default_tenant: Tenant, customer: Customer):
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        for i, label in enumerate(["First", "Second", "Third"]):
            db.add(Interaction(
                tenant_id=default_tenant.id,
                client_id=customer.id,
                type="note",
                direction="interne",
                subject=label,
                created_at=now + timedelta(hours=i),
            ))
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        subjects = [i.subject for i in result.interactions]
        # Most recent first
        assert subjects[0] == "Third"
        assert subjects[-1] == "First"


# ---------------------------------------------------------------------------
# Consents section
# ---------------------------------------------------------------------------

class TestGetClient360WithConsents:
    def test_consentements_included(self, db: Session, default_tenant: Tenant, customer: Customer):
        db.add(MarketingConsent(
            tenant_id=default_tenant.id,
            client_id=customer.id,
            channel="email",
            consented=True,
        ))
        db.add(MarketingConsent(
            tenant_id=default_tenant.id,
            client_id=customer.id,
            channel="sms",
            consented=False,
        ))
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert len(result.consentements) == 2
        channels = {c.canal for c in result.consentements}
        assert channels == {"email", "sms"}

    def test_email_consent_value_preserved(self, db: Session, default_tenant: Tenant, customer: Customer):
        db.add(MarketingConsent(
            tenant_id=default_tenant.id,
            client_id=customer.id,
            channel="email",
            consented=True,
        ))
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        email_consent = next(c for c in result.consentements if c.canal == "email")
        assert email_consent.consenti is True


# ---------------------------------------------------------------------------
# Not found error
# ---------------------------------------------------------------------------

class TestGetClient360NotFound:
    def test_raises_not_found_for_missing_client(self, db: Session, default_tenant: Tenant):
        with pytest.raises(NotFoundError) as exc_info:
            get_client_360(db, default_tenant.id, 999999)

        assert exc_info.value.entity == "client"
        assert exc_info.value.entity_id == 999999

    def test_raises_not_found_for_deleted_client(self, db: Session, default_tenant: Tenant):
        from datetime import UTC, datetime

        soft_deleted = Customer(
            tenant_id=default_tenant.id,
            first_name="Deleted",
            last_name="Client",
            deleted_at=datetime.now(UTC),
        )
        db.add(soft_deleted)
        db.commit()

        with pytest.raises(NotFoundError):
            get_client_360(db, default_tenant.id, soft_deleted.id)


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------

class TestGetClient360TenantIsolation:
    def test_cannot_access_other_tenant_customer(self, db: Session, default_tenant: Tenant):
        """A client from another tenant must not be accessible."""
        other_org = Organization(name="Other Org", slug="other-org-360", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(
            organization_id=other_org.id,
            name="Other Shop 360",
            slug="other-shop-360",
        )
        db.add(other_tenant)
        db.flush()

        other_customer = Customer(
            tenant_id=other_tenant.id,
            first_name="Bob",
            last_name="Secret",
            email="secret@othershop.fr",
        )
        db.add(other_customer)
        db.commit()

        # Try to access other_customer via default_tenant — must raise NotFoundError
        with pytest.raises(NotFoundError):
            get_client_360(db, default_tenant.id, other_customer.id)

    def test_cases_scoped_to_tenant(self, db: Session, default_tenant: Tenant, customer: Customer):
        """Cases belonging to other tenants must NOT appear in the 360 view."""
        other_org = Organization(name="Org Scope", slug="org-scope-360", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(
            organization_id=other_org.id,
            name="Other Shop Scope",
            slug="other-shop-scope-360",
        )
        db.add(other_tenant)
        db.flush()

        # Deliberately assign a case with the wrong tenant_id (should not appear)
        wrong_case = Case(
            tenant_id=other_tenant.id,
            customer_id=customer.id,
            status="en_cours",
            source="wrong_tenant",
        )
        # Correct case in default_tenant
        correct_case = Case(
            tenant_id=default_tenant.id,
            customer_id=customer.id,
            status="draft",
            source="correct_tenant",
        )
        db.add(wrong_case)
        db.add(correct_case)
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert len(result.dossiers) == 1
        assert result.dossiers[0].source == "correct_tenant"

    def test_interactions_scoped_to_tenant(self, db: Session, default_tenant: Tenant, customer: Customer):
        """Interactions from another tenant must not bleed into the 360 view."""
        other_org = Organization(name="Org Int", slug="org-int-360", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(
            organization_id=other_org.id,
            name="Other Int Shop",
            slug="other-int-shop-360",
        )
        db.add(other_tenant)
        db.flush()

        db.add(Interaction(
            tenant_id=other_tenant.id,
            client_id=customer.id,
            type="note",
            direction="interne",
            subject="Other tenant note",
        ))
        db.add(Interaction(
            tenant_id=default_tenant.id,
            client_id=customer.id,
            type="note",
            direction="interne",
            subject="My tenant note",
        ))
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert len(result.interactions) == 1
        assert result.interactions[0].subject == "My tenant note"

    def test_consents_scoped_to_tenant(self, db: Session, default_tenant: Tenant, customer: Customer):
        other_org = Organization(name="Org Consent", slug="org-consent-360", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(
            organization_id=other_org.id,
            name="Other Consent Shop",
            slug="other-consent-shop-360",
        )
        db.add(other_tenant)
        db.flush()

        db.add(MarketingConsent(
            tenant_id=other_tenant.id,
            client_id=customer.id,
            channel="email",
            consented=True,
        ))
        db.add(MarketingConsent(
            tenant_id=default_tenant.id,
            client_id=customer.id,
            channel="sms",
            consented=False,
        ))
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert len(result.consentements) == 1
        assert result.consentements[0].canal == "sms"


# ---------------------------------------------------------------------------
# get_client_cosium_data
# ---------------------------------------------------------------------------

class TestGetClientCosiumData:
    def test_returns_cosium_data_bundle(self, db: Session, default_tenant: Tenant, customer: Customer):
        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_cosium_data(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert isinstance(result, CosiumDataBundle)

    def test_raises_not_found_for_missing_client(self, db: Session, default_tenant: Tenant):
        with pytest.raises(NotFoundError):
            get_client_cosium_data(db, default_tenant.id, 999999)

    def test_prescriptions_forwarded_in_bundle(self, db: Session, default_tenant: Tenant, customer: Customer):
        fake_prescription = CosiumPrescriptionSummary(
            id=1,
            cosium_id=42,
            prescription_date="2024-01-15",
            prescriber_name="Dr Leblanc",
        )
        patches = _cosium_patches(prescriptions=[fake_prescription])
        _apply_all_patches(patches)
        try:
            result = get_client_cosium_data(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert len(result.prescriptions) == 1
        assert result.prescriptions[0].prescriber_name == "Dr Leblanc"

    def test_isolated_from_other_tenant(self, db: Session, default_tenant: Tenant):
        other_org = Organization(name="Org Cosium", slug="org-cosium-360", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = Tenant(
            organization_id=other_org.id,
            name="Other Cosium Shop",
            slug="other-cosium-shop-360",
        )
        db.add(other_tenant)
        db.flush()
        other_customer = Customer(
            tenant_id=other_tenant.id,
            first_name="X",
            last_name="Y",
        )
        db.add(other_customer)
        db.commit()

        # Accessing other_customer via default_tenant must fail
        with pytest.raises(NotFoundError):
            get_client_cosium_data(db, default_tenant.id, other_customer.id)


# ---------------------------------------------------------------------------
# Avatar URL logic
# ---------------------------------------------------------------------------

class TestGetClient360AvatarUrl:
    def test_avatar_url_set_when_customer_has_avatar(self, db: Session, default_tenant: Tenant):
        c = Customer(
            tenant_id=default_tenant.id,
            first_name="WithAvatar",
            last_name="User",
            avatar_url="some-s3-key",
        )
        db.add(c)
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, c.id)
        finally:
            _exit_all_patches(patches)

        assert result.avatar_url == f"/api/v1/clients/{c.id}/avatar"

    def test_avatar_url_none_when_no_avatar(self, db: Session, default_tenant: Tenant, customer: Customer):
        # customer fixture has no avatar_url
        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert result.avatar_url is None


# ---------------------------------------------------------------------------
# cosium_id field
# ---------------------------------------------------------------------------

class TestGetClient360CosiumId:
    def test_cosium_id_forwarded_when_present(self, db: Session, default_tenant: Tenant):
        c = Customer(
            tenant_id=default_tenant.id,
            first_name="Cosium",
            last_name="Client",
            cosium_id="COS-12345",
        )
        db.add(c)
        db.commit()

        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, c.id)
        finally:
            _exit_all_patches(patches)

        assert result.cosium_id == "COS-12345"

    def test_cosium_id_none_when_not_set(self, db: Session, default_tenant: Tenant, customer: Customer):
        patches = _cosium_patches()
        _apply_all_patches(patches)
        try:
            result = get_client_360(db, default_tenant.id, customer.id)
        finally:
            _exit_all_patches(patches)

        assert result.cosium_id is None
