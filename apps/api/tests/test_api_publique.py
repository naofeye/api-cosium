"""Tests API publique v1 (admin CRUD + auth Bearer + read endpoints)."""
from __future__ import annotations

import pytest

from app.models.api_token import ApiToken
from app.repositories import api_token_repo
from app.services.api_token_service import (
    display_prefix,
    generate_raw_token,
    hash_token,
    has_scope,
    verify_api_token,
)


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------


def test_generate_raw_token_has_prefix():
    raw = generate_raw_token()
    assert raw.startswith("opf_")
    assert len(raw) >= 40


def test_hash_token_deterministic():
    raw = "opf_abc123"
    h1 = hash_token(raw)
    h2 = hash_token(raw)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_hash_token_different_for_different_inputs():
    assert hash_token("opf_a") != hash_token("opf_b")


def test_display_prefix_exposes_first_chars():
    raw = "opf_AbCdEfGhIjKlMn"
    assert display_prefix(raw) == "opf_AbCdEfGh"


def test_has_scope_match():
    token = ApiToken(scopes=["read:clients", "read:devis"])
    assert has_scope(token, "read:clients") is True
    assert has_scope(token, "read:factures") is False


def test_verify_api_token_returns_token_when_valid(db, default_tenant):
    raw = generate_raw_token()
    api_token_repo.create_token(
        db,
        tenant_id=default_tenant.id,
        name="test",
        prefix=display_prefix(raw),
        hashed_token=hash_token(raw),
        scopes=["read:clients"],
        description=None,
        expires_at=None,
        created_by_user_id=None,
    )
    db.commit()

    result = verify_api_token(db, raw)
    assert result is not None
    assert result.tenant_id == default_tenant.id
    assert result.last_used_at is not None  # Best-effort update


def test_verify_api_token_returns_none_when_invalid(db, default_tenant):
    assert verify_api_token(db, "opf_unknown") is None
    assert verify_api_token(db, "") is None
    assert verify_api_token(db, None) is None


def test_verify_api_token_returns_none_when_revoked(db, default_tenant):
    raw = generate_raw_token()
    token = api_token_repo.create_token(
        db,
        tenant_id=default_tenant.id,
        name="revoked",
        prefix=display_prefix(raw),
        hashed_token=hash_token(raw),
        scopes=["read:clients"],
        description=None,
        expires_at=None,
        created_by_user_id=None,
    )
    token.revoked = True
    db.commit()

    assert verify_api_token(db, raw) is None


def test_verify_api_token_returns_none_when_expired(db, default_tenant):
    from datetime import UTC, datetime, timedelta

    raw = generate_raw_token()
    api_token_repo.create_token(
        db,
        tenant_id=default_tenant.id,
        name="expired",
        prefix=display_prefix(raw),
        hashed_token=hash_token(raw),
        scopes=["read:clients"],
        description=None,
        expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1),
        created_by_user_id=None,
    )
    db.commit()

    assert verify_api_token(db, raw) is None


# ---------------------------------------------------------------------------
# Admin CRUD endpoints
# ---------------------------------------------------------------------------


def test_list_allowed_scopes(client, auth_headers):
    resp = client.get("/api/v1/admin/api-tokens/scopes", headers=auth_headers)
    assert resp.status_code == 200
    scopes = resp.json()["scopes"]
    assert "read:clients" in scopes
    assert scopes == sorted(scopes)


def test_create_token_returns_secret_once(client, auth_headers):
    resp = client.post(
        "/api/v1/admin/api-tokens",
        headers=auth_headers,
        json={
            "name": "Test",
            "scopes": ["read:clients", "read:devis"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test"
    assert data["token"].startswith("opf_")
    assert data["prefix"].startswith("opf_")
    assert data["prefix"] in data["token"]


def test_create_token_rejects_invalid_scope(client, auth_headers):
    resp = client.post(
        "/api/v1/admin/api-tokens",
        headers=auth_headers,
        json={"name": "Bad", "scopes": ["write:clients"]},
    )
    assert resp.status_code == 422


def test_list_tokens_excludes_secret(client, auth_headers):
    client.post(
        "/api/v1/admin/api-tokens",
        headers=auth_headers,
        json={"name": "T1", "scopes": ["read:clients"]},
    )
    resp = client.get("/api/v1/admin/api-tokens", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    for t in items:
        assert "token" not in t  # Le secret n'est jamais expose
        assert "prefix" in t


def test_revoke_token_via_patch(client, auth_headers):
    create = client.post(
        "/api/v1/admin/api-tokens",
        headers=auth_headers,
        json={"name": "ToRevoke", "scopes": ["read:clients"]},
    )
    token_id = create.json()["id"]

    resp = client.patch(
        f"/api/v1/admin/api-tokens/{token_id}",
        headers=auth_headers,
        json={"revoked": True},
    )
    assert resp.status_code == 200
    assert resp.json()["revoked"] is True


def test_delete_token(client, auth_headers):
    create = client.post(
        "/api/v1/admin/api-tokens",
        headers=auth_headers,
        json={"name": "Doomed", "scopes": ["read:clients"]},
    )
    token_id = create.json()["id"]

    resp = client.delete(
        f"/api/v1/admin/api-tokens/{token_id}", headers=auth_headers
    )
    assert resp.status_code == 204

    not_found = client.get(
        f"/api/v1/admin/api-tokens/{token_id}", headers=auth_headers
    )
    assert not_found.status_code == 404


# ---------------------------------------------------------------------------
# Public API endpoints (auth Bearer)
# ---------------------------------------------------------------------------


@pytest.fixture
def api_token_clients_only(client, auth_headers):
    """Cree un token avec scope read:clients."""
    resp = client.post(
        "/api/v1/admin/api-tokens",
        headers=auth_headers,
        json={"name": "RC", "scopes": ["read:clients"]},
    )
    assert resp.status_code == 201
    return resp.json()["token"]


def test_public_clients_requires_token(client):
    resp = client.get("/api/public/v1/clients")
    assert resp.status_code == 401


def test_public_clients_with_valid_token(client, api_token_clients_only):
    resp = client.get(
        "/api/public/v1/clients",
        headers={"Authorization": f"Bearer {api_token_clients_only}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["limit"] == 50
    assert body["offset"] == 0


def test_public_devis_rejects_token_without_scope(client, api_token_clients_only):
    """Token has only read:clients, devis requires read:devis."""
    resp = client.get(
        "/api/public/v1/devis",
        headers={"Authorization": f"Bearer {api_token_clients_only}"},
    )
    assert resp.status_code == 403
    assert "Scope manquant" in resp.json()["detail"]


def test_public_with_revoked_token_rejects(
    client, auth_headers, api_token_clients_only
):
    # Get the just-created token id by listing
    tokens = client.get("/api/v1/admin/api-tokens", headers=auth_headers).json()
    token_id = tokens[0]["id"]

    # Revoke
    client.patch(
        f"/api/v1/admin/api-tokens/{token_id}",
        headers=auth_headers,
        json={"revoked": True},
    )

    resp = client.get(
        "/api/public/v1/clients",
        headers={"Authorization": f"Bearer {api_token_clients_only}"},
    )
    assert resp.status_code == 401
