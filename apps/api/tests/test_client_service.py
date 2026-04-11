"""Unit tests for client_service — direct service function calls."""

from sqlalchemy.orm import Session

from app.domain.schemas.clients import ClientCreate
from app.models import Customer, Tenant
from app.services import client_service


def _tenant_id(db: Session) -> int:
    return db.query(Tenant).filter(Tenant.slug == "test-magasin").first().id


class TestSearchClients:
    def test_returns_paginated_results(self, db, seed_user):
        tid = _tenant_id(db)
        # Create 3 clients
        for i in range(3):
            payload = ClientCreate(first_name=f"Client{i}", last_name="Test")
            client_service.create_client(db, tid, payload, seed_user.id)

        result = client_service.search_clients(db, tid, query="", page=1, page_size=2)
        assert result.total == 3
        assert len(result.items) == 2
        assert result.page == 1
        assert result.page_size == 2


class TestCreateClient:
    def test_creates_with_all_fields(self, db, seed_user):
        tid = _tenant_id(db)
        payload = ClientCreate(
            first_name="Marie",
            last_name="Curie",
            phone="0612345678",
            email="marie@example.com",
            address="12 rue de la Science",
            city="Paris",
            postal_code="75005",
        )
        result = client_service.create_client(db, tid, payload, seed_user.id)

        assert result.id is not None
        assert result.first_name == "Marie"
        assert result.last_name == "Curie"
        assert result.phone == "0612345678"
        assert result.email == "marie@example.com"
        assert result.city == "Paris"


class TestDeleteAndRestore:
    def test_soft_delete_sets_deleted_at(self, db, seed_user):
        tid = _tenant_id(db)
        payload = ClientCreate(first_name="ToDelete", last_name="Client")
        created = client_service.create_client(db, tid, payload, seed_user.id)

        client_service.delete_client(db, tid, created.id, seed_user.id)

        # The customer record still exists in DB but has deleted_at set
        customer = db.query(Customer).filter(Customer.id == created.id).first()
        assert customer is not None
        assert customer.deleted_at is not None

    def test_restore_clears_deleted_at(self, db, seed_user):
        tid = _tenant_id(db)
        payload = ClientCreate(first_name="ToRestore", last_name="Client")
        created = client_service.create_client(db, tid, payload, seed_user.id)

        client_service.delete_client(db, tid, created.id, seed_user.id)
        restored = client_service.restore_client(db, tid, created.id, seed_user.id)

        assert restored.deleted_at is None


class TestFindDuplicates:
    def test_detects_same_name_duplicates(self, db, seed_user):
        tid = _tenant_id(db)
        # Create two clients with the same name
        for _ in range(2):
            payload = ClientCreate(first_name="Doublon", last_name="Dupont")
            client_service.create_client(db, tid, payload, seed_user.id)

        dupes = client_service.find_duplicates(db, tid)
        assert len(dupes) >= 1
        group = next(g for g in dupes if "doublon" in g.name.lower())
        assert group.count == 2
        assert len(group.clients) == 2


class TestImportFromCsv:
    def test_valid_csv_imports_correctly(self, db, seed_user):
        tid = _tenant_id(db)
        csv_content = (
            b"nom;prenom;email;telephone;adresse;ville;code_postal\n"
            b"Martin;Alice;alice@test.com;0601020304;1 rue A;Lyon;69001\n"
            b"Bernard;Bob;;0605060708;;Marseille;13001\n"
            b";;;;;;\n"  # empty line — should be skipped (no nom)
        )

        result = client_service.import_from_file(db, tid, csv_content, "test.csv", seed_user.id)
        assert result.imported == 2
        assert result.skipped == 1
        # The skipped row (empty name) produces an error entry
        assert any(e.line == 4 for e in result.errors)
