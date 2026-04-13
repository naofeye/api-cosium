"""Tests RGPD consent : opt-in/opt-out par canal + check_consent + audit trail."""
import pytest

from app.models import AuditLog, Customer, Tenant
from app.services import consent_service


@pytest.fixture(name="customer")
def customer_fixture(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    cust = Customer(tenant_id=tenant.id, first_name="Marie", last_name="Curie", email="marie@test.local")
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


def test_consent_default_is_no_record(db, customer):
    """Pas de consentement enregistre = pas de record (check_consent retourne False)."""
    consents = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
    assert consents == []
    assert consent_service.check_consent(db, customer.tenant_id, customer.id, "email") is False


def test_opt_in_email(db, customer):
    """Opt-in sur canal email cree un record consented=True."""
    from app.domain.schemas.marketing import ConsentUpdate
    payload = ConsentUpdate(consented=True, source="formulaire_compte_client")
    result = consent_service.update_consent(
        db, tenant_id=customer.tenant_id, client_id=customer.id,
        channel="email", payload=payload, user_id=0,
    )
    assert result.consented is True
    assert result.channel == "email"
    assert result.source == "formulaire_compte_client"

    assert consent_service.check_consent(db, customer.tenant_id, customer.id, "email") is True


def test_opt_out_then_opt_in_again_idempotent(db, customer):
    """Opt-out puis opt-in retoggle : 1 seul record, etat final consented=True."""
    from app.domain.schemas.marketing import ConsentUpdate
    consent_service.update_consent(
        db, tenant_id=customer.tenant_id, client_id=customer.id,
        channel="sms", payload=ConsentUpdate(consented=True, source="sms_initial"),
        user_id=0,
    )
    consent_service.update_consent(
        db, tenant_id=customer.tenant_id, client_id=customer.id,
        channel="sms", payload=ConsentUpdate(consented=False, source="lien_unsubscribe"),
        user_id=0,
    )
    consent_service.update_consent(
        db, tenant_id=customer.tenant_id, client_id=customer.id,
        channel="sms", payload=ConsentUpdate(consented=True, source="formulaire_reinscription"),
        user_id=0,
    )

    consents = consent_service.get_consents(db, tenant_id=customer.tenant_id, client_id=customer.id)
    sms_consents = [c for c in consents if c.channel == "sms"]
    assert len(sms_consents) == 1, "1 seul record par canal (upsert)"
    assert sms_consents[0].consented is True
    assert sms_consents[0].source == "formulaire_reinscription"


def test_consent_per_channel_independent(db, customer):
    """Email opt-in + SMS opt-out : les 2 canaux ont des etats independants."""
    from app.domain.schemas.marketing import ConsentUpdate
    consent_service.update_consent(
        db, tenant_id=customer.tenant_id, client_id=customer.id,
        channel="email", payload=ConsentUpdate(consented=True), user_id=0,
    )
    consent_service.update_consent(
        db, tenant_id=customer.tenant_id, client_id=customer.id,
        channel="sms", payload=ConsentUpdate(consented=False), user_id=0,
    )
    consent_service.update_consent(
        db, tenant_id=customer.tenant_id, client_id=customer.id,
        channel="postal", payload=ConsentUpdate(consented=True), user_id=0,
    )

    assert consent_service.check_consent(db, customer.tenant_id, customer.id, "email") is True
    assert consent_service.check_consent(db, customer.tenant_id, customer.id, "sms") is False
    assert consent_service.check_consent(db, customer.tenant_id, customer.id, "postal") is True


def test_consent_update_creates_audit_log_when_user_provided(db, customer, seed_user):
    """Toute modif de consentement avec user_id doit creer un AuditLog."""
    from app.domain.schemas.marketing import ConsentUpdate
    consent_service.update_consent(
        db, tenant_id=customer.tenant_id, client_id=customer.id,
        channel="email", payload=ConsentUpdate(consented=True, source="formulaire"),
        user_id=seed_user.id,
    )
    audit = db.query(AuditLog).filter(
        AuditLog.tenant_id == customer.tenant_id,
        AuditLog.entity_type == "marketing_consent",
        AuditLog.user_id == seed_user.id,
    ).first()
    assert audit is not None
    assert audit.action == "update"


def test_consent_unknown_channel_still_recorded(db, customer):
    """Le service ne valide pas la liste des canaux (extensible : telegram, whatsapp...)."""
    from app.domain.schemas.marketing import ConsentUpdate
    result = consent_service.update_consent(
        db, tenant_id=customer.tenant_id, client_id=customer.id,
        channel="whatsapp", payload=ConsentUpdate(consented=True), user_id=0,
    )
    assert result.channel == "whatsapp"
    assert result.consented is True
