"""Tests des 2 endpoints publics ajoutes : payments + pec-preparations."""
from __future__ import annotations

import pytest

from app.repositories import api_token_repo
from app.services.api_token_service import (
    display_prefix,
    generate_raw_token,
    hash_token,
)


def _make_token(db, tenant, scopes: list[str]) -> str:
    raw = generate_raw_token()
    api_token_repo.create_token(
        db,
        tenant_id=tenant.id,
        name="extra-tests",
        prefix=display_prefix(raw),
        hashed_token=hash_token(raw),
        scopes=scopes,
        description=None,
        expires_at=None,
        created_by_user_id=None,
    )
    db.commit()
    return raw


def test_public_payments_requires_token(client):
    resp = client.get("/api/public/v1/payments")
    assert resp.status_code == 401


def test_public_payments_rejects_wrong_scope(client, db, default_tenant):
    raw = _make_token(db, default_tenant, ["read:clients"])
    resp = client.get(
        "/api/public/v1/payments",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert resp.status_code == 403


def test_public_payments_with_valid_scope(client, db, default_tenant):
    raw = _make_token(db, default_tenant, ["read:payments"])
    resp = client.get(
        "/api/public/v1/payments",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["limit"] == 50


def test_public_pec_preparations_requires_token(client):
    resp = client.get("/api/public/v1/pec-preparations")
    assert resp.status_code == 401


def test_public_pec_preparations_with_valid_scope(client, db, default_tenant):
    raw = _make_token(db, default_tenant, ["read:pec"])
    resp = client.get(
        "/api/public/v1/pec-preparations",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert body["limit"] == 50


def test_public_payments_filter_by_status(client, db, default_tenant):
    raw = _make_token(db, default_tenant, ["read:payments"])
    resp = client.get(
        "/api/public/v1/payments?status=pending",
        headers={"Authorization": f"Bearer {raw}"},
    )
    assert resp.status_code == 200
