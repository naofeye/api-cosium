"""Tests unitaires pour marketing_service — segments, campagnes, consentement."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.domain.schemas.marketing import CampaignCreate, SegmentCreate
from app.models import Customer, MarketingConsent, Tenant
from app.services import marketing_service


def _make_client_with_email(db: Session, tenant_id: int, email: str = "test@example.com") -> Customer:
    c = Customer(tenant_id=tenant_id, first_name="Marketing", last_name="Client", email=email)
    db.add(c)
    db.flush()
    return c


def _grant_consent(db: Session, tenant_id: int, client_id: int, channel: str = "email") -> None:
    consent = MarketingConsent(tenant_id=tenant_id, client_id=client_id, channel=channel, consented=True)
    db.add(consent)
    db.commit()


class TestSegments:
    """Tests de creation et gestion des segments."""

    def test_create_segment_empty_rules(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = SegmentCreate(name="Tous les clients", rules_json={})
        result = marketing_service.create_segment(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.name == "Tous les clients"
        assert result.member_count >= 0

    def test_create_segment_with_email_rule(self, db, seed_user):
        """Un segment avec critere has_email doit inclure les clients avec email."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        _make_client_with_email(db, tenant.id, "seg@test.com")
        db.commit()

        payload = SegmentCreate(name="Clients email", rules_json={"has_email": True})
        result = marketing_service.create_segment(db, tenant.id, payload, seed_user.id)

        assert result.member_count >= 1

    def test_list_segments(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        marketing_service.create_segment(db, tenant.id, SegmentCreate(name="Seg1", rules_json={}), seed_user.id)
        marketing_service.create_segment(db, tenant.id, SegmentCreate(name="Seg2", rules_json={}), seed_user.id)

        results = marketing_service.list_segments(db, tenant.id)
        assert len(results) >= 2

    def test_refresh_segment(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        segment = marketing_service.create_segment(
            db, tenant.id, SegmentCreate(name="Refresh test", rules_json={"has_email": True}), seed_user.id
        )

        # Ajouter un nouveau client apres creation du segment
        _make_client_with_email(db, tenant.id, "new@test.com")
        db.commit()

        refreshed = marketing_service.refresh_segment(db, tenant.id, segment.id)
        assert refreshed.member_count >= 1

    def test_refresh_segment_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            marketing_service.refresh_segment(db, tenant.id, 99999)


class TestCampaigns:
    """Tests de creation et envoi de campagnes."""

    def test_create_campaign_happy_path(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        segment = marketing_service.create_segment(
            db, tenant.id, SegmentCreate(name="Camp seg", rules_json={}), seed_user.id
        )
        payload = CampaignCreate(
            name="Promo ete", segment_id=segment.id, channel="email",
            subject="Offre speciale", template="Bonjour {{client_name}} !"
        )
        result = marketing_service.create_campaign(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.name == "Promo ete"
        assert result.status == "draft"
        assert result.segment_name == "Camp seg"

    def test_create_campaign_segment_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = CampaignCreate(
            name="Bad seg", segment_id=99999, channel="email", template="Test"
        )
        with pytest.raises(NotFoundError):
            marketing_service.create_campaign(db, tenant.id, payload, seed_user.id)

    def test_send_campaign_no_consent(self, db, seed_user):
        """Campagne envoyee sans consentement = 0 envoi."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        _make_client_with_email(db, tenant.id, "noconsent@test.com")
        db.commit()

        segment = marketing_service.create_segment(
            db, tenant.id, SegmentCreate(name="No consent", rules_json={"has_email": True}), seed_user.id
        )
        campaign = marketing_service.create_campaign(
            db, tenant.id,
            CampaignCreate(name="No consent", segment_id=segment.id, channel="email", template="Hi"),
            seed_user.id,
        )
        stats = marketing_service.send_campaign(db, tenant.id, campaign.id, seed_user.id)

        assert stats.total_sent == 0

    def test_send_campaign_already_sent(self, db, seed_user):
        """Renvoyer une campagne deja envoyee doit lever une erreur."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        segment = marketing_service.create_segment(
            db, tenant.id, SegmentCreate(name="Sent seg", rules_json={}), seed_user.id
        )
        campaign = marketing_service.create_campaign(
            db, tenant.id,
            CampaignCreate(name="Sent camp", segment_id=segment.id, channel="email", template="Hi"),
            seed_user.id,
        )
        marketing_service.send_campaign(db, tenant.id, campaign.id, seed_user.id)

        with pytest.raises(BusinessError):
            marketing_service.send_campaign(db, tenant.id, campaign.id, seed_user.id)

    def test_get_campaign_stats(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        segment = marketing_service.create_segment(
            db, tenant.id, SegmentCreate(name="Stats seg", rules_json={}), seed_user.id
        )
        campaign = marketing_service.create_campaign(
            db, tenant.id,
            CampaignCreate(name="Stats camp", segment_id=segment.id, channel="email", template="Hi"),
            seed_user.id,
        )
        stats = marketing_service.get_campaign_stats(db, tenant.id, campaign.id)

        assert stats.campaign_id == campaign.id
        assert stats.total_sent >= 0
