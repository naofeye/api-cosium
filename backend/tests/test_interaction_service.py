"""Tests unitaires pour interaction_service — creation, timeline, suppression."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.schemas.interactions import InteractionCreate
from app.models import Customer, Tenant
from app.services import interaction_service


def _make_customer(db: Session, tenant_id: int) -> Customer:
    c = Customer(tenant_id=tenant_id, first_name="Timeline", last_name="Test")
    db.add(c)
    db.flush()
    return c


class TestAddInteraction:
    """Tests de creation d'interaction."""

    def test_create_interaction_returns_response(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        payload = InteractionCreate(
            client_id=customer.id, type="appel", direction="entrant", subject="Demande info"
        )
        result = interaction_service.add_interaction(db, tenant.id, payload, seed_user.id)
        assert result.id is not None
        assert result.type == "appel"
        assert result.direction == "entrant"
        assert result.subject == "Demande info"

    def test_create_interaction_with_content(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        payload = InteractionCreate(
            client_id=customer.id, type="note", direction="interne",
            subject="Note interne", content="Detail de la note"
        )
        result = interaction_service.add_interaction(db, tenant.id, payload, seed_user.id)
        assert result.content == "Detail de la note"


class TestGetClientTimeline:
    """Tests de recuperation de la timeline."""

    def test_timeline_returns_interactions(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        for i in range(3):
            payload = InteractionCreate(
                client_id=customer.id, type="appel", direction="entrant", subject=f"Appel {i}"
            )
            interaction_service.add_interaction(db, tenant.id, payload, seed_user.id)

        items, total = interaction_service.get_client_timeline(db, tenant.id, customer.id)
        assert total == 3
        assert len(items) == 3

    def test_timeline_filter_by_type(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        interaction_service.add_interaction(
            db, tenant.id,
            InteractionCreate(client_id=customer.id, type="appel", direction="entrant", subject="A"),
            seed_user.id,
        )
        interaction_service.add_interaction(
            db, tenant.id,
            InteractionCreate(client_id=customer.id, type="email", direction="sortant", subject="B"),
            seed_user.id,
        )
        items, total = interaction_service.get_client_timeline(db, tenant.id, customer.id, type="appel")
        assert total == 1
        assert items[0].type == "appel"


class TestDeleteInteraction:
    """Tests de suppression d'interaction."""

    def test_delete_existing_interaction(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        payload = InteractionCreate(
            client_id=customer.id, type="note", direction="interne", subject="A supprimer"
        )
        result = interaction_service.add_interaction(db, tenant.id, payload, seed_user.id)
        interaction_service.delete_interaction(db, tenant.id, result.id, seed_user.id)

        items, total = interaction_service.get_client_timeline(db, tenant.id, customer.id)
        assert total == 0

    def test_delete_nonexistent_raises(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            interaction_service.delete_interaction(db, tenant.id, 99999, seed_user.id)
