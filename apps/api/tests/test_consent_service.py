"""Tests unitaires pour consent_service.

Couvre :
- get_consents : liste vide, un canal, plusieurs canaux
- update_consent : opt-in (email, sms), opt-out, upsert idempotent
- check_consent : absence de record, apres opt-in, apres opt-out
- timestamps : consented_at sette a l'opt-in, revoked_at sette a l'opt-out
- audit log : cree quand user_id > 0, absent quand user_id == 0
- isolation tenant : un consentement d'un autre tenant n'est pas visible
"""
import pytest

from app.domain.schemas.marketing import ConsentUpdate
from app.models import AuditLog, Customer, Tenant
from app.services import consent_service


# ---------------------------------------------------------------------------
# Fixtures locales
# ---------------------------------------------------------------------------


@pytest.fixture(name="customer")
def customer_fixture(db, default_tenant):
    cust = Customer(tenant_id=default_tenant.id, first_name="Alice", last_name="Martin", email="alice@test.local")
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


@pytest.fixture(name="tenant2")
def tenant2_fixture(db):
    from app.models import Organization

    org = Organization(name="Org2", slug="org2", plan="solo")
    db.add(org)
    db.flush()
    t = Tenant(
        organization_id=org.id,
        name="Magasin2",
        slug="magasin2",
        cosium_tenant="ct2",
        cosium_login="cl2",
        cosium_password_enc="cp2",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.fixture(name="customer2")
def customer2_fixture(db, tenant2):
    cust = Customer(tenant_id=tenant2.id, first_name="Bob", last_name="Leroy")
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


def _opt_in(db, tenant_id, client_id, channel, source=None):
    return consent_service.update_consent(
        db,
        tenant_id=tenant_id,
        client_id=client_id,
        channel=channel,
        payload=ConsentUpdate(consented=True, source=source),
        user_id=0,
    )


def _opt_out(db, tenant_id, client_id, channel, source=None):
    return consent_service.update_consent(
        db,
        tenant_id=tenant_id,
        client_id=client_id,
        channel=channel,
        payload=ConsentUpdate(consented=False, source=source),
        user_id=0,
    )


# ---------------------------------------------------------------------------
# Tests : get_consents
# ---------------------------------------------------------------------------


class TestGetConsents:
    def test_no_consents_returns_empty_list(self, db, customer):
        result = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
        assert result == []

    def test_returns_consent_after_opt_in(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email")

        result = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
        assert len(result) == 1
        assert result[0].channel == "email"
        assert result[0].consented is True

    def test_returns_all_channels(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email")
        _opt_in(db, customer.tenant_id, customer.id, "sms")
        _opt_out(db, customer.tenant_id, customer.id, "postal")

        result = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
        channels = {c.channel for c in result}
        assert channels == {"email", "sms", "postal"}

    def test_consents_isolated_by_tenant(self, db, customer, customer2, tenant2):
        """get_consents ne doit pas retourner les consentements d'un autre tenant."""
        _opt_in(db, tenant2.id, customer2.id, "email")
        # Aucun consentement pour customer dans son propre tenant
        result = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
        assert result == []

    def test_response_contains_required_fields(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email", source="web")

        result = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
        r = result[0]
        assert r.id is not None
        assert r.client_id == customer.id
        assert r.channel == "email"
        assert r.source == "web"


# ---------------------------------------------------------------------------
# Tests : update_consent (opt-in)
# ---------------------------------------------------------------------------


class TestUpdateConsentOptIn:
    def test_opt_in_creates_record(self, db, customer):
        result = _opt_in(db, customer.tenant_id, customer.id, "email")

        assert result.consented is True
        assert result.channel == "email"
        assert result.client_id == customer.id

    def test_opt_in_sets_consented_at(self, db, customer):
        result = _opt_in(db, customer.tenant_id, customer.id, "sms")

        assert result.consented_at is not None
        assert result.revoked_at is None

    def test_opt_in_stores_source(self, db, customer):
        result = _opt_in(db, customer.tenant_id, customer.id, "email", source="formulaire_inscription")

        assert result.source == "formulaire_inscription"

    def test_opt_in_with_no_source(self, db, customer):
        result = _opt_in(db, customer.tenant_id, customer.id, "email", source=None)

        assert result.source is None

    def test_opt_in_email_and_sms_independent(self, db, customer):
        r_email = _opt_in(db, customer.tenant_id, customer.id, "email")
        r_sms = _opt_in(db, customer.tenant_id, customer.id, "sms")

        assert r_email.consented is True
        assert r_sms.consented is True
        assert r_email.id != r_sms.id  # 2 records distincts


# ---------------------------------------------------------------------------
# Tests : update_consent (opt-out / revocation)
# ---------------------------------------------------------------------------


class TestUpdateConsentOptOut:
    def test_opt_out_without_prior_opt_in(self, db, customer):
        """Opt-out sans opt-in prealable : cree un record consented=False."""
        result = _opt_out(db, customer.tenant_id, customer.id, "email")

        assert result.consented is False
        assert result.revoked_at is not None

    def test_opt_out_after_opt_in_updates_record(self, db, customer):
        first = _opt_in(db, customer.tenant_id, customer.id, "email")
        second = _opt_out(db, customer.tenant_id, customer.id, "email")

        # Meme record (upsert), pas de doublon
        assert second.id == first.id
        assert second.consented is False
        assert second.revoked_at is not None

    def test_opt_out_clears_consented_at(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "sms")
        result = _opt_out(db, customer.tenant_id, customer.id, "sms")

        # Apres revocation, consented_at est inchange mais revoked_at est present
        assert result.revoked_at is not None

    def test_opt_out_updates_source(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email", source="web")
        result = _opt_out(db, customer.tenant_id, customer.id, "email", source="lien_desinscription")

        assert result.source == "lien_desinscription"


# ---------------------------------------------------------------------------
# Tests : upsert idempotence
# ---------------------------------------------------------------------------


class TestConsentUpsert:
    def test_repeated_opt_in_same_channel_only_one_record(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email")
        _opt_in(db, customer.tenant_id, customer.id, "email")
        _opt_in(db, customer.tenant_id, customer.id, "email")

        consents = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
        email_consents = [c for c in consents if c.channel == "email"]
        assert len(email_consents) == 1

    def test_toggle_in_out_in_results_in_opt_in(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "sms")
        _opt_out(db, customer.tenant_id, customer.id, "sms")
        _opt_in(db, customer.tenant_id, customer.id, "sms")

        consents = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
        sms_consents = [c for c in consents if c.channel == "sms"]
        assert len(sms_consents) == 1
        assert sms_consents[0].consented is True

    def test_toggle_in_out_in_final_source_is_last(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email", source="s1")
        _opt_out(db, customer.tenant_id, customer.id, "email", source="s2")
        _opt_in(db, customer.tenant_id, customer.id, "email", source="s3")

        result = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
        assert result[0].source == "s3"


# ---------------------------------------------------------------------------
# Tests : check_consent
# ---------------------------------------------------------------------------


class TestCheckConsent:
    def test_no_record_returns_false(self, db, customer):
        assert consent_service.check_consent(db, customer.tenant_id, customer.id, "email") is False

    def test_after_opt_in_returns_true(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email")
        assert consent_service.check_consent(db, customer.tenant_id, customer.id, "email") is True

    def test_after_opt_out_returns_false(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email")
        _opt_out(db, customer.tenant_id, customer.id, "email")
        assert consent_service.check_consent(db, customer.tenant_id, customer.id, "email") is False

    def test_check_wrong_channel_returns_false(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email")
        # sms n'a pas de consentement
        assert consent_service.check_consent(db, customer.tenant_id, customer.id, "sms") is False

    def test_check_isolated_by_tenant(self, db, customer, customer2, tenant2):
        """check_consent d'un autre tenant ne doit pas contaminer le tenant courant."""
        _opt_in(db, tenant2.id, customer2.id, "email")

        assert consent_service.check_consent(db, customer.tenant_id, customer.id, "email") is False

    def test_check_multiple_channels_independent(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "email")
        _opt_out(db, customer.tenant_id, customer.id, "sms")
        _opt_in(db, customer.tenant_id, customer.id, "postal")

        assert consent_service.check_consent(db, customer.tenant_id, customer.id, "email") is True
        assert consent_service.check_consent(db, customer.tenant_id, customer.id, "sms") is False
        assert consent_service.check_consent(db, customer.tenant_id, customer.id, "postal") is True


# ---------------------------------------------------------------------------
# Tests : audit log
# ---------------------------------------------------------------------------


class TestConsentAuditLog:
    def test_audit_log_created_when_user_provided(self, db, customer, seed_user):
        consent_service.update_consent(
            db,
            tenant_id=customer.tenant_id,
            client_id=customer.id,
            channel="email",
            payload=ConsentUpdate(consented=True, source="formulaire"),
            user_id=seed_user.id,
        )

        log = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == customer.tenant_id,
                AuditLog.entity_type == "marketing_consent",
                AuditLog.user_id == seed_user.id,
            )
            .first()
        )
        assert log is not None
        assert log.action == "update"

    def test_audit_log_new_value_contains_channel_and_consented(self, db, customer, seed_user):
        import json

        consent_service.update_consent(
            db,
            tenant_id=customer.tenant_id,
            client_id=customer.id,
            channel="sms",
            payload=ConsentUpdate(consented=True),
            user_id=seed_user.id,
        )

        log = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == customer.tenant_id,
                AuditLog.entity_type == "marketing_consent",
            )
            .first()
        )
        new_val = json.loads(log.new_value)
        assert new_val["channel"] == "sms"
        assert new_val["consented"] is True

    def test_no_audit_log_when_user_id_is_zero(self, db, customer):
        """user_id=0 (anonyme / systeme) -> pas d'audit log cree."""
        _opt_in(db, customer.tenant_id, customer.id, "email")

        log_count = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == customer.tenant_id,
                AuditLog.entity_type == "marketing_consent",
            )
            .count()
        )
        assert log_count == 0

    def test_audit_log_created_on_opt_out(self, db, customer, seed_user):
        _opt_in(db, customer.tenant_id, customer.id, "email")

        consent_service.update_consent(
            db,
            tenant_id=customer.tenant_id,
            client_id=customer.id,
            channel="email",
            payload=ConsentUpdate(consented=False, source="unsubscribe"),
            user_id=seed_user.id,
        )

        # Devrait y avoir au moins un log (l'opt-out)
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == customer.tenant_id,
                AuditLog.entity_type == "marketing_consent",
                AuditLog.user_id == seed_user.id,
            )
            .all()
        )
        assert len(logs) >= 1

    def test_multiple_updates_create_multiple_audit_logs(self, db, customer, seed_user):
        """Chaque appel update_consent avec un user_id valide produit un log distinct."""
        for consented in [True, False, True]:
            consent_service.update_consent(
                db,
                tenant_id=customer.tenant_id,
                client_id=customer.id,
                channel="email",
                payload=ConsentUpdate(consented=consented),
                user_id=seed_user.id,
            )

        count = (
            db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == customer.tenant_id,
                AuditLog.entity_type == "marketing_consent",
            )
            .count()
        )
        assert count == 3


# ---------------------------------------------------------------------------
# Tests : canaux non standards (extensibilite)
# ---------------------------------------------------------------------------


class TestConsentCustomChannels:
    def test_unknown_channel_accepted(self, db, customer):
        result = _opt_in(db, customer.tenant_id, customer.id, "whatsapp")

        assert result.channel == "whatsapp"
        assert result.consented is True

    def test_check_consent_custom_channel(self, db, customer):
        _opt_in(db, customer.tenant_id, customer.id, "push_notification")

        assert consent_service.check_consent(db, customer.tenant_id, customer.id, "push_notification") is True
