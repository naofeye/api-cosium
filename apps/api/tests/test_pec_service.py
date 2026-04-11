"""Tests unitaires pour pec_service — workflow PEC, transitions de statut, montants."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.domain.schemas.pec import (
    PayerOrgCreate,
    PecCreate,
    PecStatusUpdate,
    RelanceCreate,
)
from app.models import Case, Customer, Tenant
from app.services import pec_service


def _make_customer(db: Session, tenant_id: int) -> Customer:
    c = Customer(tenant_id=tenant_id, first_name="PEC", last_name="Client")
    db.add(c)
    db.flush()
    return c


def _make_case(db: Session, tenant_id: int, customer_id: int) -> Case:
    case = Case(tenant_id=tenant_id, customer_id=customer_id, status="draft")
    db.add(case)
    db.flush()
    return case


def _setup_pec(db: Session, tenant_id: int, user_id: int) -> tuple[int, int]:
    """Cree un organisme et un dossier, retourne (org_id, case_id)."""
    org = pec_service.create_organization(
        db, tenant_id,
        PayerOrgCreate(name="MGEN Test", type="mutuelle", code=f"MGEN{user_id}"),
        user_id,
    )
    customer = _make_customer(db, tenant_id)
    case = _make_case(db, tenant_id, customer.id)
    return org.id, case.id


class TestCreateOrganization:
    """Tests de creation d'organisme payeur."""

    def test_create_organization_mutuelle(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = PayerOrgCreate(name="MGEN", type="mutuelle", code="MGEN001")
        result = pec_service.create_organization(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.name == "MGEN"
        assert result.type == "mutuelle"
        assert result.code == "MGEN001"

    def test_create_organization_secu(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = PayerOrgCreate(name="CPAM Paris", type="secu", code="CPAM75")
        result = pec_service.create_organization(db, tenant.id, payload, seed_user.id)

        assert result.type == "secu"

    def test_list_organizations(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        pec_service.create_organization(
            db, tenant.id, PayerOrgCreate(name="Org1", type="mutuelle", code="ORG1"), seed_user.id
        )
        results = pec_service.list_organizations(db, tenant.id)
        assert len(results) >= 1


class TestCreatePec:
    """Tests de creation de demande de PEC."""

    def test_create_pec_happy_path(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        org_id, case_id = _setup_pec(db, tenant.id, seed_user.id)
        payload = PecCreate(case_id=case_id, organization_id=org_id, montant_demande=250.0)
        result = pec_service.create_pec(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.status == "soumise"
        assert result.montant_demande == 250.0
        assert result.montant_accorde is None

    def test_create_pec_organization_not_found(self, db, seed_user):
        """Organisme inexistant doit lever NotFoundError."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)
        payload = PecCreate(case_id=case.id, organization_id=99999, montant_demande=100.0)

        with pytest.raises(NotFoundError):
            pec_service.create_pec(db, tenant.id, payload, seed_user.id)


class TestPecStatusTransitions:
    """Tests des transitions de statut PEC."""

    def test_valid_transition_soumise_to_en_attente(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        org_id, case_id = _setup_pec(db, tenant.id, seed_user.id)
        pec = pec_service.create_pec(
            db, tenant.id, PecCreate(case_id=case_id, organization_id=org_id, montant_demande=300.0), seed_user.id
        )
        update = PecStatusUpdate(status="en_attente", comment="Dossier en cours")
        result = pec_service.change_status(db, tenant.id, pec.id, update, seed_user.id)

        assert result.status == "en_attente"

    def test_valid_transition_to_acceptee_with_montant(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        org_id, case_id = _setup_pec(db, tenant.id, seed_user.id)
        pec = pec_service.create_pec(
            db, tenant.id, PecCreate(case_id=case_id, organization_id=org_id, montant_demande=500.0), seed_user.id
        )
        pec_service.change_status(db, tenant.id, pec.id, PecStatusUpdate(status="en_attente"), seed_user.id)
        result = pec_service.change_status(
            db, tenant.id, pec.id,
            PecStatusUpdate(status="acceptee", montant_accorde=450.0),
            seed_user.id,
        )

        assert result.status == "acceptee"
        assert result.montant_accorde == 450.0

    def test_invalid_transition_soumise_to_cloturee(self, db, seed_user):
        """Transition directe soumise -> cloturee est interdite."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        org_id, case_id = _setup_pec(db, tenant.id, seed_user.id)
        pec = pec_service.create_pec(
            db, tenant.id, PecCreate(case_id=case_id, organization_id=org_id, montant_demande=100.0), seed_user.id
        )

        with pytest.raises(BusinessError):
            pec_service.change_status(db, tenant.id, pec.id, PecStatusUpdate(status="cloturee"), seed_user.id)

    def test_change_status_pec_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            pec_service.change_status(
                db, tenant.id, 99999, PecStatusUpdate(status="en_attente"), seed_user.id
            )


class TestPecDetail:
    """Tests du detail PEC avec historique."""

    def test_get_detail_includes_history(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        org_id, case_id = _setup_pec(db, tenant.id, seed_user.id)
        pec = pec_service.create_pec(
            db, tenant.id, PecCreate(case_id=case_id, organization_id=org_id, montant_demande=200.0), seed_user.id
        )
        pec_service.change_status(db, tenant.id, pec.id, PecStatusUpdate(status="en_attente"), seed_user.id)

        detail = pec_service.get_pec_detail(db, tenant.id, pec.id)
        assert len(detail.history) >= 2  # soumise + en_attente

    def test_get_detail_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            pec_service.get_pec_detail(db, tenant.id, 99999)


class TestRelance:
    """Tests des relances PEC."""

    def test_create_relance(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        org_id, case_id = _setup_pec(db, tenant.id, seed_user.id)
        pec = pec_service.create_pec(
            db, tenant.id, PecCreate(case_id=case_id, organization_id=org_id, montant_demande=150.0), seed_user.id
        )
        payload = RelanceCreate(type="email", contenu="Relance pour dossier en attente")
        result = pec_service.create_relance(db, tenant.id, pec.id, payload, seed_user.id)

        assert result.id is not None
        assert result.type == "email"
        assert result.pec_request_id == pec.id

    def test_relance_pec_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = RelanceCreate(type="telephone")
        with pytest.raises(NotFoundError):
            pec_service.create_relance(db, tenant.id, 99999, payload, seed_user.id)
