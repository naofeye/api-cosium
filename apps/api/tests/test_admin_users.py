"""Tests for admin user management endpoints."""

import pytest


def test_list_users_returns_current_user(client, auth_headers):
    """List users should return at least the seeded admin user."""
    resp = client.get("/api/v1/admin/users", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert "total" in data
    assert data["total"] >= 1
    emails = [u["email"] for u in data["users"]]
    assert "test@optiflow.com" in emails


def test_create_user_with_valid_data(client, auth_headers):
    """Creating a user with valid data should succeed."""
    payload = {
        "email": "new.user@optiflow.com",
        "password": "StrongPass1",
        "role": "operator",
        "first_name": "Jean",
        "last_name": "Dupont",
    }
    resp = client.post("/api/v1/admin/users", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new.user@optiflow.com"
    assert data["role"] == "operator"
    assert data["is_active"] is True


def test_create_user_duplicate_email_fails(client, auth_headers):
    """Creating a user with an email that already exists in the tenant should fail."""
    payload = {
        "email": "duplicate@optiflow.com",
        "password": "StrongPass1",
        "role": "operator",
    }
    resp1 = client.post("/api/v1/admin/users", json=payload, headers=auth_headers)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/admin/users", json=payload, headers=auth_headers)
    assert resp2.status_code == 400
    assert "existe deja" in resp2.json().get("error", {}).get("message", "").lower()


def test_update_user_role(client, auth_headers):
    """Updating a user's role should succeed."""
    # Create a user first
    create_resp = client.post(
        "/api/v1/admin/users",
        json={
            "email": "role.change@optiflow.com",
            "password": "StrongPass1",
            "role": "operator",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Update role
    resp = client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"role": "manager"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "manager"


def test_deactivate_user(client, auth_headers):
    """Deactivating a user should set is_active to False."""
    # Create a user first
    create_resp = client.post(
        "/api/v1/admin/users",
        json={
            "email": "to.deactivate@optiflow.com",
            "password": "StrongPass1",
            "role": "viewer",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    user_id = create_resp.json()["id"]

    # Deactivate
    resp = client.delete(
        f"/api/v1/admin/users/{user_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
