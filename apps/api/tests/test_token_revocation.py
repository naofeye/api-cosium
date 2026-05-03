"""Tests token revocation per-user (logout-everywhere)."""
from __future__ import annotations

from app.security import create_access_token, decode_access_token


def test_create_access_token_includes_token_version():
    token = create_access_token(
        subject="user@test", role="admin", tenant_id=1, token_version=5
    )
    payload = decode_access_token(token)
    assert payload.get("tv") == 5


def test_create_access_token_default_token_version_zero():
    token = create_access_token(subject="user@test", role="admin", tenant_id=1)
    payload = decode_access_token(token)
    assert payload.get("tv") == 0


def test_revoke_all_tokens_increments_version(client, auth_headers, db, seed_user):
    """Endpoint revoke increments user.token_version + revokes refresh tokens."""
    initial_version = seed_user.token_version or 0

    resp = client.post(
        "/api/v1/auth/revoke-all-tokens", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "revoked"
    assert body["token_version"] == initial_version + 1

    db.refresh(seed_user)
    assert seed_user.token_version == initial_version + 1


def test_old_token_rejected_after_revocation(client, db, seed_user):
    """Apres revoke, un JWT emis avant doit etre rejete a la prochaine requete."""
    # Login pour obtenir le token initial (token_version=0)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    assert login.status_code == 200
    old_token = login.cookies.get("optiflow_token")
    assert old_token

    # Revoke (utilise le token actuel, donc accepte)
    revoke = client.post(
        "/api/v1/auth/revoke-all-tokens",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert revoke.status_code == 200

    # Le old_token doit maintenant etre rejete
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert resp.status_code == 401


def test_new_token_after_revocation_works(client, db, seed_user):
    """Apres revoke + login, le nouveau token (avec nouveau token_version)
    doit fonctionner normalement."""
    # Login initial
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    old_token = login.cookies.get("optiflow_token")
    assert old_token

    # Revoke
    client.post(
        "/api/v1/auth/revoke-all-tokens",
        headers={"Authorization": f"Bearer {old_token}"},
    )

    # Re-login : nouveau token avec token_version incrementee
    login2 = client.post(
        "/api/v1/auth/login",
        json={"email": "test@optiflow.com", "password": "test123"},
    )
    assert login2.status_code == 200
    new_token = login2.cookies.get("optiflow_token")
    assert new_token

    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert resp.status_code == 200
