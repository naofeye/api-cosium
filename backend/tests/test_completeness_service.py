"""Tests unitaires pour completeness_service — score de completude des dossiers."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Case, Customer, Document, DocumentType, Tenant
from app.services import completeness_service


def _make_case(db: Session, tenant_id: int) -> Case:
    c = Customer(tenant_id=tenant_id, first_name="Comp", last_name="Test")
    db.add(c)
    db.flush()
    case = Case(tenant_id=tenant_id, customer_id=c.id, status="draft")
    db.add(case)
    db.flush()
    return case


class TestGetCompleteness:
    """Tests du calcul de completude."""

    def test_empty_case_has_all_missing(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        case = _make_case(db, tenant.id)
        result = completeness_service.get_completeness(db, tenant.id, case.id)
        assert result.case_id == case.id
        assert result.total_required >= 1
        assert result.total_present == 0
        assert result.total_missing == result.total_required

    def test_adding_document_reduces_missing(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        case = _make_case(db, tenant.id)

        # Find a required document type
        required_type = db.query(DocumentType).filter(DocumentType.is_required.is_(True)).first()
        assert required_type is not None

        # Add document matching that type
        doc = Document(
            tenant_id=tenant.id, case_id=case.id, type=required_type.code,
            filename="test.pdf", storage_key="test/test.pdf",
        )
        db.add(doc)
        db.commit()

        result = completeness_service.get_completeness(db, tenant.id, case.id)
        assert result.total_present >= 1
        assert result.total_missing < result.total_required

    def test_items_list_contains_all_types(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        case = _make_case(db, tenant.id)
        total_types = db.query(DocumentType).count()

        result = completeness_service.get_completeness(db, tenant.id, case.id)
        assert len(result.items) == total_types

    def test_nonexistent_case_raises(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            completeness_service.get_completeness(db, tenant.id, 99999)

    def test_cross_tenant_case_raises(self, db: Session, seed_user) -> None:
        """A case from another tenant should not be accessible."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        case = _make_case(db, tenant.id)
        with pytest.raises(NotFoundError):
            completeness_service.get_completeness(db, tenant.id + 999, case.id)
