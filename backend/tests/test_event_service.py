"""Tests unitaires pour event_service — emission d'evenements et creation de notifications."""

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models import Tenant
from app.services import event_service, notification_service


class TestEmitEvent:
    """Tests d'emission d'evenements."""

    def test_known_event_creates_notification(self, db: Session, seed_user) -> None:
        """Un evenement connu doit creer une notification pour les admins."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        event_service.emit_event(
            db,
            tenant_id=tenant.id,
            event_type="DossierCree",
            entity_type="case",
            entity_id=42,
            user_id=seed_user.id,
        )

        listing = notification_service.list_notifications(db, tenant.id, seed_user.id)
        titles = [n.title for n in listing.items]
        assert "Nouveau dossier cree" in titles

    def test_unknown_event_no_notification(self, db: Session, seed_user) -> None:
        """Un evenement inconnu ne doit pas creer de notification."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        initial = notification_service.list_notifications(db, tenant.id, seed_user.id).total

        event_service.emit_event(
            db,
            tenant_id=tenant.id,
            event_type="EvenementInconnu",
            entity_type="case",
            entity_id=1,
            user_id=seed_user.id,
        )

        after = notification_service.list_notifications(db, tenant.id, seed_user.id).total
        assert after == initial

    def test_notification_message_contains_entity_id(self, db: Session, seed_user) -> None:
        """Le message de notification doit contenir l'ID de l'entite."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        event_service.emit_event(
            db,
            tenant_id=tenant.id,
            event_type="PaiementRecu",
            entity_type="payment",
            entity_id=777,
            user_id=seed_user.id,
        )

        listing = notification_service.list_notifications(db, tenant.id, seed_user.id)
        payment_notifs = [n for n in listing.items if n.title == "Paiement recu"]
        assert len(payment_notifs) >= 1
        assert "777" in payment_notifs[0].message

    def test_notification_type_matches_config(self, db: Session, seed_user) -> None:
        """Le type de notification doit correspondre a la configuration."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        event_service.emit_event(
            db,
            tenant_id=tenant.id,
            event_type="PECRefusee",
            entity_type="pec",
            entity_id=10,
            user_id=seed_user.id,
        )

        listing = notification_service.list_notifications(db, tenant.id, seed_user.id)
        pec_notifs = [n for n in listing.items if n.title == "PEC refusee"]
        assert len(pec_notifs) >= 1
        assert pec_notifs[0].type == "warning"

    def test_multiple_events_create_multiple_notifications(self, db: Session, seed_user) -> None:
        """Emettre plusieurs evenements cree autant de notifications."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()

        initial = notification_service.list_notifications(db, tenant.id, seed_user.id).total

        event_service.emit_event(
            db, tenant_id=tenant.id, event_type="DevisCree",
            entity_type="devis", entity_id=1, user_id=seed_user.id,
        )
        event_service.emit_event(
            db, tenant_id=tenant.id, event_type="DevisEnvoye",
            entity_type="devis", entity_id=1, user_id=seed_user.id,
        )
        event_service.emit_event(
            db, tenant_id=tenant.id, event_type="DevisSigne",
            entity_type="devis", entity_id=1, user_id=seed_user.id,
        )

        after = notification_service.list_notifications(db, tenant.id, seed_user.id).total
        assert after >= initial + 3
