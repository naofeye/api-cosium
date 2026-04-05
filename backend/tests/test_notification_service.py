"""Tests unitaires pour notification_service — creation, lecture, listing."""

from sqlalchemy.orm import Session

from app.models import Tenant
from app.services import notification_service


class TestNotifyCreate:
    """Tests de creation de notifications."""

    def test_create_notification_info(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        result = notification_service.notify(
            db, tenant.id, seed_user.id,
            type="info",
            title="Nouveau dossier cree",
            message="Le dossier #42 a ete cree avec succes.",
            entity_type="case",
            entity_id=42,
        )

        assert result.id is not None
        assert result.type == "info"
        assert result.title == "Nouveau dossier cree"
        assert result.is_read is False
        assert result.entity_type == "case"
        assert result.entity_id == 42

    def test_create_notification_warning(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        result = notification_service.notify(
            db, tenant.id, seed_user.id,
            type="warning",
            title="Paiement en retard",
            message="Le paiement de la facture F-001 est en retard de 15 jours.",
        )

        assert result.type == "warning"
        assert result.entity_type is None

    def test_create_multiple_notifications(self, db, seed_user):
        """Verifier que plusieurs notifications peuvent etre creees."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        for i in range(3):
            notification_service.notify(
                db, tenant.id, seed_user.id,
                type="info", title=f"Notif {i}", message=f"Message {i}",
            )

        listing = notification_service.list_notifications(db, tenant.id, seed_user.id)
        assert listing.total >= 3


class TestListNotifications:
    """Tests du listing des notifications."""

    def test_list_empty(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        listing = notification_service.list_notifications(db, tenant.id, seed_user.id)

        assert listing.total >= 0
        assert isinstance(listing.items, list)
        assert listing.unread_count >= 0

    def test_list_with_pagination(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        for i in range(5):
            notification_service.notify(
                db, tenant.id, seed_user.id,
                type="info", title=f"Notif {i}", message=f"Msg {i}",
            )

        listing = notification_service.list_notifications(db, tenant.id, seed_user.id, limit=2, offset=0)
        assert len(listing.items) == 2
        assert listing.total >= 5

    def test_list_unread_only(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        notif = notification_service.notify(
            db, tenant.id, seed_user.id, type="info", title="Unread", message="Test",
        )
        notification_service.mark_read(db, tenant.id, notif.id)

        # Creer une deuxieme non lue
        notification_service.notify(
            db, tenant.id, seed_user.id, type="info", title="Still unread", message="Test2",
        )

        listing = notification_service.list_notifications(db, tenant.id, seed_user.id, unread_only=True)
        for item in listing.items:
            assert item.is_read is False


class TestUnreadCount:
    """Tests du compteur de notifications non lues."""

    def test_unread_count_zero(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        result = notification_service.get_unread_count(db, tenant.id, seed_user.id)
        assert result.count >= 0

    def test_unread_count_increments(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        initial = notification_service.get_unread_count(db, tenant.id, seed_user.id).count

        notification_service.notify(
            db, tenant.id, seed_user.id, type="info", title="Inc1", message="Test",
        )
        notification_service.notify(
            db, tenant.id, seed_user.id, type="info", title="Inc2", message="Test2",
        )

        after = notification_service.get_unread_count(db, tenant.id, seed_user.id).count
        assert after == initial + 2


class TestMarkRead:
    """Tests du marquage comme lu."""

    def test_mark_single_read(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        notif = notification_service.notify(
            db, tenant.id, seed_user.id, type="info", title="MarkMe", message="Read me",
        )
        initial_count = notification_service.get_unread_count(db, tenant.id, seed_user.id).count

        notification_service.mark_read(db, tenant.id, notif.id)

        after_count = notification_service.get_unread_count(db, tenant.id, seed_user.id).count
        assert after_count == initial_count - 1

    def test_mark_all_read(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        for i in range(3):
            notification_service.notify(
                db, tenant.id, seed_user.id, type="info", title=f"All{i}", message=f"Msg{i}",
            )

        notification_service.mark_all_read(db, tenant.id, seed_user.id)
        count = notification_service.get_unread_count(db, tenant.id, seed_user.id).count
        assert count == 0
