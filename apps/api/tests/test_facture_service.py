"""Tests unitaires pour facture_service — creation depuis devis, numerotation, montants."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.domain.schemas.devis import DevisCreate, DevisLineCreate
from app.models import Case, Customer, Tenant
from app.services import devis_service, facture_service


def _make_customer(db: Session, tenant_id: int) -> Customer:
    c = Customer(tenant_id=tenant_id, first_name="Facture", last_name="Test")
    db.add(c)
    db.flush()
    return c


def _make_case(db: Session, tenant_id: int, customer_id: int) -> Case:
    case = Case(tenant_id=tenant_id, customer_id=customer_id, status="draft")
    db.add(case)
    db.flush()
    return case


def _default_lignes() -> list[DevisLineCreate]:
    return [
        DevisLineCreate(designation="Monture", quantite=1, prix_unitaire_ht=200.0, taux_tva=20.0),
        DevisLineCreate(designation="Verres", quantite=2, prix_unitaire_ht=100.0, taux_tva=20.0),
    ]


def _create_signed_devis(db: Session, tenant_id: int, user_id: int) -> int:
    """Cree un devis et le fait passer au statut signe."""
    customer = _make_customer(db, tenant_id)
    case = _make_case(db, tenant_id, customer.id)
    payload = DevisCreate(case_id=case.id, lignes=_default_lignes())
    devis = devis_service.create_devis(db, tenant_id, payload, user_id)
    devis_service.change_status(db, tenant_id, devis.id, "envoye", user_id)
    devis_service.change_status(db, tenant_id, devis.id, "signe", user_id)
    return devis.id


class TestCreateFromDevis:
    """Tests de generation de facture depuis un devis signe."""

    def test_create_facture_from_signed_devis(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        devis_id = _create_signed_devis(db, tenant.id, seed_user.id)

        result = facture_service.create_from_devis(db, tenant.id, devis_id, seed_user.id)

        assert result.id is not None
        assert result.numero.startswith("F-")
        assert result.montant_ht == 400.0  # 200 + 2*100
        assert result.tva == 80.0  # 400 * 0.20
        assert result.montant_ttc == 480.0
        assert result.status == "emise"

    def test_create_facture_from_draft_devis_raises(self, db, seed_user):
        """Un devis en brouillon ne peut pas generer de facture."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)
        payload = DevisCreate(case_id=case.id, lignes=_default_lignes())
        devis = devis_service.create_devis(db, tenant.id, payload, seed_user.id)

        with pytest.raises(BusinessError):
            facture_service.create_from_devis(db, tenant.id, devis.id, seed_user.id)

    def test_duplicate_facture_is_idempotent(self, db, seed_user):
        """Appeler deux fois create_from_devis retourne la meme facture (idempotent)."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        devis_id = _create_signed_devis(db, tenant.id, seed_user.id)

        first = facture_service.create_from_devis(db, tenant.id, devis_id, seed_user.id)
        second = facture_service.create_from_devis(db, tenant.id, devis_id, seed_user.id)
        assert first.id == second.id
        assert first.numero == second.numero

    def test_create_facture_devis_not_found(self, db, seed_user):
        """Un devis inexistant doit lever NotFoundError."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            facture_service.create_from_devis(db, tenant.id, 99999, seed_user.id)

    def test_devis_status_updates_to_facture(self, db, seed_user):
        """Apres generation de la facture, le devis passe au statut 'facture'."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        devis_id = _create_signed_devis(db, tenant.id, seed_user.id)

        facture_service.create_from_devis(db, tenant.id, devis_id, seed_user.id)

        from app.repositories import devis_repo
        devis = devis_repo.get_by_id(db, devis_id, tenant.id)
        assert devis.status == "facture"


class TestListFactures:
    """Tests du listing des factures."""

    def test_list_factures_empty(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        results = facture_service.list_factures(db, tenant.id)
        assert results == []

    def test_list_factures_returns_created(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        devis_id = _create_signed_devis(db, tenant.id, seed_user.id)
        facture_service.create_from_devis(db, tenant.id, devis_id, seed_user.id)

        results = facture_service.list_factures(db, tenant.id)
        assert len(results) == 1


class TestGetFactureDetail:
    """Tests du detail d'une facture."""

    def test_get_detail_includes_lignes(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        devis_id = _create_signed_devis(db, tenant.id, seed_user.id)
        facture = facture_service.create_from_devis(db, tenant.id, devis_id, seed_user.id)

        detail = facture_service.get_facture_detail(db, tenant.id, facture.id)
        assert len(detail.lignes) == 2
        assert detail.montant_ttc == 480.0

    def test_get_detail_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            facture_service.get_facture_detail(db, tenant.id, 99999)
