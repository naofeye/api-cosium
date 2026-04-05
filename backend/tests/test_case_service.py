"""Tests unitaires pour case_service — CRUD dossiers, transitions de statut, soft-delete."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.schemas.cases import CaseCreate
from app.models import Case, Customer, Tenant
from app.services import case_service


def _make_customer(db: Session, tenant_id: int) -> Customer:
    c = Customer(tenant_id=tenant_id, first_name="Marie", last_name="Durand")
    db.add(c)
    db.flush()
    return c


def _make_case(db: Session, tenant_id: int, customer_id: int, status: str = "draft") -> Case:
    case = Case(tenant_id=tenant_id, customer_id=customer_id, status=status)
    db.add(case)
    db.flush()
    return case


class TestCreateCase:
    """Tests de creation de dossier."""

    def test_create_case_happy_path(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = CaseCreate(first_name="Jean", last_name="Martin", phone="0601020304", source="manual")
        result = case_service.create_case(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.customer_name == "Jean Martin"
        assert result.status == "draft"
        assert result.source == "manual"

    def test_create_case_minimal_fields(self, db, seed_user):
        """Creation avec uniquement les champs obligatoires (prenom + nom)."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = CaseCreate(first_name="A", last_name="B")
        result = case_service.create_case(db, tenant.id, payload, seed_user.id)

        assert result.customer_name == "A B"
        assert result.source == "manual"  # valeur par defaut

    def test_create_case_with_email(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = CaseCreate(first_name="Sophie", last_name="Lemaire", email="sophie@test.com")
        result = case_service.create_case(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.customer_name == "Sophie Lemaire"


class TestListCases:
    """Tests de listing des dossiers."""

    def test_list_cases_empty(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        results = case_service.list_cases(db, tenant.id)
        assert results == []

    def test_list_cases_returns_created_cases(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        case_service.create_case(db, tenant.id, CaseCreate(first_name="A", last_name="B"), seed_user.id)
        case_service.create_case(db, tenant.id, CaseCreate(first_name="C", last_name="D"), seed_user.id)

        results = case_service.list_cases(db, tenant.id)
        assert len(results) == 2

    def test_list_cases_pagination(self, db, seed_user):
        """Verifie que la pagination limit/offset fonctionne."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        for i in range(5):
            case_service.create_case(db, tenant.id, CaseCreate(first_name=f"Client{i}", last_name="Test"), seed_user.id)

        page1 = case_service.list_cases(db, tenant.id, limit=2, offset=0)
        page2 = case_service.list_cases(db, tenant.id, limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id


class TestGetCaseDetail:
    """Tests du detail d'un dossier."""

    def test_get_case_detail_happy_path(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        created = case_service.create_case(
            db, tenant.id, CaseCreate(first_name="Detail", last_name="Test"), seed_user.id
        )
        detail = case_service.get_case_detail(db, tenant.id, created.id)

        assert detail.id == created.id
        assert detail.customer_name == "Detail Test"
        assert detail.documents == []
        assert detail.payments == []

    def test_get_case_detail_not_found(self, db, seed_user):
        """Un dossier inexistant doit lever NotFoundError."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            case_service.get_case_detail(db, tenant.id, 99999)
