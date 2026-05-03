"""Tests signature electronique devis."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models import Case, Customer
from app.models.devis import Devis
from app.services import devis_signature_service


@pytest.fixture
def signed_setup(db, default_tenant):
    """Cree un client + case + devis envoye, retourne le devis."""
    customer = Customer(
        tenant_id=default_tenant.id,
        first_name="Jean",
        last_name="DUPONT",
    )
    db.add(customer)
    db.flush()
    case = Case(
        tenant_id=default_tenant.id,
        customer_id=customer.id,
        status="en_cours",
    )
    db.add(case)
    db.flush()
    devis = Devis(
        tenant_id=default_tenant.id,
        case_id=case.id,
        numero="D-001",
        status="envoye",
        montant_ht=100,
        tva=20,
        montant_ttc=120,
    )
    db.add(devis)
    db.commit()
    return devis


def test_generate_public_token_unique():
    a = devis_signature_service.generate_public_token()
    b = devis_signature_service.generate_public_token()
    assert a != b
    assert len(a) == 32
    assert all(c in "0123456789abcdef" for c in a)


def test_ensure_public_link_creates_token(db, default_tenant, signed_setup):
    token = devis_signature_service.ensure_public_link(
        db, default_tenant.id, signed_setup.id, user_id=1
    )
    assert len(token) == 32
    db.refresh(signed_setup)
    assert signed_setup.public_token == token


def test_ensure_public_link_idempotent(db, default_tenant, signed_setup):
    """2 appels successifs retournent le meme token (pas de regen)."""
    t1 = devis_signature_service.ensure_public_link(
        db, default_tenant.id, signed_setup.id, user_id=1
    )
    t2 = devis_signature_service.ensure_public_link(
        db, default_tenant.id, signed_setup.id, user_id=1
    )
    assert t1 == t2


def test_ensure_public_link_rejects_signed_devis(db, default_tenant, signed_setup):
    """Devis deja signe : pas de regen de lien."""
    signed_setup.status = "signe"
    db.commit()
    from app.core.exceptions import BusinessError

    with pytest.raises(BusinessError):
        devis_signature_service.ensure_public_link(
            db, default_tenant.id, signed_setup.id, user_id=1
        )


def test_get_devis_by_public_token(db, default_tenant, signed_setup):
    devis_signature_service.ensure_public_link(
        db, default_tenant.id, signed_setup.id, user_id=1
    )
    db.refresh(signed_setup)
    found = devis_signature_service.get_devis_by_public_token(
        db, signed_setup.public_token
    )
    assert found is not None
    assert found.id == signed_setup.id


def test_get_devis_by_public_token_unknown(db):
    assert (
        devis_signature_service.get_devis_by_public_token(db, "x" * 32) is None
    )
    assert devis_signature_service.get_devis_by_public_token(db, "") is None


def test_sign_devis_public_persists_signature(db, default_tenant, signed_setup):
    token = devis_signature_service.ensure_public_link(
        db, default_tenant.id, signed_setup.id, user_id=1
    )
    response = devis_signature_service.sign_devis_public(
        db,
        public_token=token,
        consent_text="J'accepte le devis.",
        client_ip="1.2.3.4",
        user_agent="Mozilla/5.0 test",
    )
    assert response.status == "signe"

    db.refresh(signed_setup)
    assert signed_setup.signed_at is not None
    assert signed_setup.signature_method == "clickwrap"
    assert signed_setup.signature_ip == "1.2.3.4"
    assert signed_setup.signature_consent_text == "J'accepte le devis."
    assert signed_setup.status == "signe"


def test_sign_devis_public_idempotent(db, default_tenant, signed_setup):
    """2e signature avec le meme token : refusee (deja signe)."""
    from app.core.exceptions import BusinessError

    token = devis_signature_service.ensure_public_link(
        db, default_tenant.id, signed_setup.id, user_id=1
    )
    devis_signature_service.sign_devis_public(
        db, public_token=token, consent_text="ok", client_ip=None, user_agent=None
    )
    with pytest.raises(BusinessError):
        devis_signature_service.sign_devis_public(
            db, public_token=token, consent_text="ok", client_ip=None, user_agent=None
        )


def test_sign_devis_unknown_token(db):
    from app.core.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        devis_signature_service.sign_devis_public(
            db, public_token="x" * 32, consent_text="ok", client_ip=None, user_agent=None
        )


def test_get_public_devis_endpoint(client, db, default_tenant, signed_setup):
    """GET /api/public/v1/devis/{public_token} retourne la vue limitee."""
    token = devis_signature_service.ensure_public_link(
        db, default_tenant.id, signed_setup.id, user_id=1
    )
    resp = client.get(f"/api/public/v1/devis/{token}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["numero"] == "D-001"
    assert body["status"] == "envoye"
    assert body["is_signed"] is False
    # Pas de PII
    assert "customer_email" not in body
    assert "first_name" not in body


def test_post_sign_endpoint(client, db, default_tenant, signed_setup):
    token = devis_signature_service.ensure_public_link(
        db, default_tenant.id, signed_setup.id, user_id=1
    )
    resp = client.post(
        f"/api/public/v1/devis/{token}/sign",
        json={"consent_text": "J'accepte les conditions et signe ce devis."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "signe"


def test_admin_generate_public_link_endpoint(
    client, auth_headers, db, default_tenant, signed_setup
):
    resp = client.post(
        f"/api/v1/devis/{signed_setup.id}/public-link",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "public_token" in body
    assert body["public_url"] == f"/devis/sign/{body['public_token']}"
