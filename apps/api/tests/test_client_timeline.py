"""Tests du service de timeline unifiee cross-canal."""

from datetime import UTC, datetime, timedelta

from app.models import Customer
from app.models.interaction import Interaction
from app.models.marketing import Campaign, MessageLog, Segment
from app.services.client_timeline_service import build_client_timeline


def _make_customer(db, tenant, **overrides) -> Customer:
    c = Customer(
        tenant_id=tenant.id,
        first_name=overrides.get("first_name", "Jean"),
        last_name=overrides.get("last_name", "Dupont"),
        email=overrides.get("email"),
    )
    db.add(c)
    db.flush()
    return c


def test_timeline_retourne_liste_vide_si_client_inexistant(db, default_tenant) -> None:
    events = build_client_timeline(db, default_tenant.id, 999999)
    assert events == []


def test_timeline_trie_desc_par_date_interactions(db, default_tenant) -> None:
    c = _make_customer(db, default_tenant)
    now = datetime.now(UTC).replace(tzinfo=None)
    old = Interaction(
        tenant_id=default_tenant.id, client_id=c.id, type="email", direction="sortant",
        subject="Ancien", created_at=now - timedelta(days=5),
    )
    recent = Interaction(
        tenant_id=default_tenant.id, client_id=c.id, type="phone", direction="entrant",
        subject="Recent", created_at=now - timedelta(hours=1),
    )
    db.add_all([old, recent])
    db.commit()

    events = build_client_timeline(db, default_tenant.id, c.id)
    assert len(events) == 2
    assert events[0]["subject"] == "Recent"
    assert events[1]["subject"] == "Ancien"
    assert all(e["kind"] == "interaction" for e in events)


def test_timeline_inclus_campaign_messages(db, default_tenant) -> None:
    c = _make_customer(db, default_tenant)
    seg = Segment(tenant_id=default_tenant.id, name="seg1", rules_json="{}")
    db.add(seg)
    db.flush()
    camp = Campaign(
        tenant_id=default_tenant.id,
        name="Renouvellement Octobre",
        segment_id=seg.id,
        channel="email",
        template="Hello",
        status="sent",
        sent_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(camp)
    db.flush()
    ml = MessageLog(
        tenant_id=default_tenant.id, campaign_id=camp.id, client_id=c.id, channel="email",
        status="sent", sent_at=datetime.now(UTC).replace(tzinfo=None),
        variant_key="A",
    )
    db.add(ml)
    db.commit()

    events = build_client_timeline(db, default_tenant.id, c.id)
    assert any(e["kind"] == "campaign_message" for e in events)
    msg = next(e for e in events if e["kind"] == "campaign_message")
    assert "Renouvellement Octobre" in str(msg["subject"])
    assert "A" in str(msg["content"])


def test_timeline_filtre_par_kinds(db, default_tenant) -> None:
    c = _make_customer(db, default_tenant)
    db.add(
        Interaction(
            tenant_id=default_tenant.id, client_id=c.id, type="email", direction="sortant",
            subject="Test", created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    db.commit()

    events_only_messages = build_client_timeline(
        db, default_tenant.id, c.id, kinds=["campaign_message"]
    )
    assert all(e["kind"] == "campaign_message" for e in events_only_messages)
    assert len(events_only_messages) == 0

    events_only_interactions = build_client_timeline(
        db, default_tenant.id, c.id, kinds=["interaction"]
    )
    assert len(events_only_interactions) == 1
