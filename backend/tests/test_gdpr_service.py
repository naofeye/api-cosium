"""Tests unitaires pour gdpr_service — droit d'acces, export, anonymisation."""

import json

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Customer, MarketingConsent, Tenant
from app.services import gdpr_service


def _make_customer(db: Session, tenant_id: int) -> Customer:
    c = Customer(
        tenant_id=tenant_id, first_name="Jean", last_name="RGPD",
        email="jean.rgpd@test.com", phone="0601020304",
    )
    db.add(c)
    db.flush()
    return c


class TestGetClientData:
    """Tests du droit d'acces."""

    def test_returns_personal_data(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        data = gdpr_service.get_client_data(db, tenant.id, customer.id, seed_user.id)
        assert data["informations_personnelles"]["prenom"] == "Jean"
        assert data["informations_personnelles"]["nom"] == "RGPD"
        assert data["informations_personnelles"]["email"] == "jean.rgpd@test.com"

    def test_returns_all_sections(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        data = gdpr_service.get_client_data(db, tenant.id, customer.id, seed_user.id)
        assert "informations_personnelles" in data
        assert "dossiers" in data
        assert "consentements_marketing" in data
        assert "interactions" in data

    def test_nonexistent_client_raises(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            gdpr_service.get_client_data(db, tenant.id, 99999, seed_user.id)


class TestExportClientData:
    """Tests de portabilite (export JSON)."""

    def test_export_returns_valid_json_bytes(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        result = gdpr_service.export_client_data(db, tenant.id, customer.id, seed_user.id)
        assert isinstance(result, bytes)
        parsed = json.loads(result)
        assert "informations_personnelles" in parsed


class TestAnonymizeClient:
    """Tests du droit a l'oubli."""

    def test_anonymize_clears_personal_data(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        result = gdpr_service.anonymize_client(db, tenant.id, customer.id, seed_user.id)
        assert result["status"] == "anonymized"

        db.refresh(customer)
        assert customer.first_name == "ANONYMISE"
        assert customer.email is None
        assert customer.phone is None

    def test_anonymize_revokes_consents(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        consent = MarketingConsent(
            tenant_id=tenant.id, client_id=customer.id,
            channel="email", consented=True,
        )
        db.add(consent)
        db.commit()

        gdpr_service.anonymize_client(db, tenant.id, customer.id, seed_user.id)
        db.refresh(consent)
        assert consent.consented is False
        assert consent.revoked_at is not None

    def test_anonymize_nonexistent_raises(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            gdpr_service.anonymize_client(db, tenant.id, 99999, seed_user.id)
