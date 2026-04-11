"""Tests unitaires pour search_service — recherche globale multi-entites."""

from sqlalchemy.orm import Session

from app.models import Customer, Tenant
from app.services import search_service


def _create_customer(
    db: Session, tenant_id: int, first_name: str, last_name: str,
    email: str | None = None, phone: str | None = None,
) -> Customer:
    """Helper pour creer un client de test."""
    c = Customer(
        tenant_id=tenant_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


class TestGlobalSearch:
    """Tests de la recherche globale."""

    def test_search_by_last_name(self, db: Session, seed_user) -> None:
        """Recherche par nom de famille."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        _create_customer(db, tenant.id, "Jean", "Dupont", email="jd@test.fr")

        results = search_service.global_search(db, tenant.id, "Dupont")
        assert len(results["clients"]) >= 1
        assert any("Dupont" in c["label"] for c in results["clients"])

    def test_search_by_first_name(self, db: Session, seed_user) -> None:
        """Recherche par prenom."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        _create_customer(db, tenant.id, "Marguerite", "Fleur")

        results = search_service.global_search(db, tenant.id, "Marguerite")
        assert len(results["clients"]) >= 1
        assert any("Marguerite" in c["label"] for c in results["clients"])

    def test_search_by_email(self, db: Session, seed_user) -> None:
        """Recherche par email."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        _create_customer(db, tenant.id, "Email", "Test", email="unique_email_search@test.fr")

        results = search_service.global_search(db, tenant.id, "unique_email_search")
        assert len(results["clients"]) >= 1
        assert any("unique_email_search" in c["detail"] for c in results["clients"])

    def test_search_by_phone(self, db: Session, seed_user) -> None:
        """Recherche par telephone."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        _create_customer(db, tenant.id, "Phone", "Test", phone="0698765432")

        results = search_service.global_search(db, tenant.id, "0698765432")
        assert len(results["clients"]) >= 1

    def test_search_empty_results(self, db: Session, seed_user) -> None:
        """Recherche sans resultats retourne des listes vides."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        results = search_service.global_search(db, tenant.id, "zzz_inexistant_xyz")
        assert results["clients"] == []
        assert results["dossiers"] == []
        assert results["devis"] == []
        assert results["factures"] == []

    def test_search_too_short_query(self, db: Session, seed_user) -> None:
        """Recherche avec moins de 2 caracteres retourne vide."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        results = search_service.global_search(db, tenant.id, "a")
        assert all(v == [] for v in results.values())

    def test_search_empty_string(self, db: Session, seed_user) -> None:
        """Recherche avec chaine vide retourne vide."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        results = search_service.global_search(db, tenant.id, "")
        assert all(v == [] for v in results.values())
