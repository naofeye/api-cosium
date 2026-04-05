"""Unit tests for devis_service — direct service function calls."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.domain.schemas.devis import DevisCreate, DevisLineCreate, DevisUpdate
from app.models import Case, Customer, Tenant
from app.services import devis_service


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


def _default_lignes() -> list[DevisLineCreate]:
    return [
        DevisLineCreate(designation="Verre progressif", quantite=2, prix_unitaire_ht=150.0, taux_tva=20.0),
        DevisLineCreate(designation="Monture", quantite=1, prix_unitaire_ht=80.0, taux_tva=20.0),
    ]


class TestCreateDevis:
    def test_create_devis_returns_response_with_numero(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)

        payload = DevisCreate(case_id=case.id, lignes=_default_lignes())
        result = devis_service.create_devis(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.numero.startswith("DEV-")
        assert result.status == "brouillon"
        assert result.case_id == case.id

    def test_create_devis_calculates_totals_correctly(self, db, seed_user):
        """2x 150 HT + 1x 80 HT = 380 HT. TVA 20% => 456 TTC."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)

        payload = DevisCreate(
            case_id=case.id,
            part_secu=100.0,
            part_mutuelle=50.0,
            lignes=_default_lignes(),
        )
        result = devis_service.create_devis(db, tenant.id, payload, seed_user.id)

        assert result.montant_ht == 380.0
        assert result.montant_ttc == 456.0
        assert result.tva == 76.0
        assert result.part_secu == 100.0
        assert result.part_mutuelle == 50.0
        # reste_a_charge = max(456 - 100 - 50, 0) = 306
        assert result.reste_a_charge == 306.0


class TestChangeStatus:
    def test_valid_transition_brouillon_to_envoye(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)

        payload = DevisCreate(case_id=case.id, lignes=_default_lignes())
        devis = devis_service.create_devis(db, tenant.id, payload, seed_user.id)

        updated = devis_service.change_status(db, tenant.id, devis.id, "envoye", seed_user.id)
        assert updated.status == "envoye"

    def test_invalid_transition_signe_to_brouillon_raises(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)

        payload = DevisCreate(case_id=case.id, lignes=_default_lignes())
        devis = devis_service.create_devis(db, tenant.id, payload, seed_user.id)

        # Move to envoye then signe
        devis_service.change_status(db, tenant.id, devis.id, "envoye", seed_user.id)
        devis_service.change_status(db, tenant.id, devis.id, "signe", seed_user.id)

        with pytest.raises(BusinessError):
            devis_service.change_status(db, tenant.id, devis.id, "brouillon", seed_user.id)

    def test_change_status_not_found_raises(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            devis_service.change_status(db, tenant.id, 99999, "envoye", seed_user.id)


class TestUpdateDevis:
    def test_update_replaces_lignes_and_recalculates(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)

        payload = DevisCreate(case_id=case.id, lignes=_default_lignes())
        devis = devis_service.create_devis(db, tenant.id, payload, seed_user.id)
        assert devis.montant_ht == 380.0

        # Replace with a single cheaper line
        new_lignes = [DevisLineCreate(designation="Lentilles", quantite=1, prix_unitaire_ht=50.0, taux_tva=20.0)]
        update = DevisUpdate(lignes=new_lignes, part_secu=10.0)
        updated = devis_service.update_devis(db, tenant.id, devis.id, update, seed_user.id)

        assert updated.montant_ht == 50.0
        assert updated.montant_ttc == 60.0
        assert updated.part_secu == 10.0
        assert updated.reste_a_charge == 50.0

    def test_update_non_brouillon_raises(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)

        payload = DevisCreate(case_id=case.id, lignes=_default_lignes())
        devis = devis_service.create_devis(db, tenant.id, payload, seed_user.id)
        devis_service.change_status(db, tenant.id, devis.id, "envoye", seed_user.id)

        with pytest.raises(BusinessError):
            devis_service.update_devis(
                db, tenant.id, devis.id,
                DevisUpdate(lignes=_default_lignes()),
                seed_user.id,
            )


class TestDevisSchemaValidation:
    def test_devis_create_requires_at_least_one_ligne(self):
        """Schema enforces min_length=1 on lignes."""
        with pytest.raises(Exception):
            DevisCreate(case_id=1, lignes=[])
