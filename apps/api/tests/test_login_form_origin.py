"""Regression tests for /api/v1/auth/login-form Origin/Referer validation.

Audit Codex 2026-05-02 finding M1 : la verification utilisait `startswith()` ce
qui rendait `https://app.example.com.evil.test` acceptable comme origine quand
`https://app.example.com` etait dans la liste autorisee. La correction parse
l'URL et compare strictement scheme://host[:port].
"""
from app.core.config import settings


def test_login_form_rejects_origin_with_suffix_attack(client, seed_user, monkeypatch):
    """Un origin malicieux qui prefixe une origine autorisee doit etre refuse."""
    monkeypatch.setattr(settings, "cors_origins", "https://app.example.com")
    resp = client.post(
        "/api/v1/auth/login-form",
        data={"email": "test@optiflow.com", "password": "test123"},
        headers={"Origin": "https://app.example.com.evil.test"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "Origine+non+autorisee" in resp.headers.get("location", "") or \
        "Origine%20non%20autorisee" in resp.headers.get("location", "")


def test_login_form_rejects_origin_with_path_suffix(client, seed_user, monkeypatch):
    """Un origin avec path malveillant ne doit pas matcher non plus."""
    monkeypatch.setattr(settings, "cors_origins", "https://app.example.com")
    resp = client.post(
        "/api/v1/auth/login-form",
        data={"email": "test@optiflow.com", "password": "test123"},
        headers={"Referer": "https://evil.com/?https://app.example.com"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "error=Origine" in resp.headers.get("location", "")


def test_login_form_accepts_exact_allowed_origin(client, seed_user, monkeypatch):
    """Un origin exactement dans l'allowlist doit passer."""
    monkeypatch.setattr(settings, "cors_origins", "http://localhost:3000")
    resp = client.post(
        "/api/v1/auth/login-form",
        data={"email": "test@optiflow.com", "password": "test123"},
        headers={"Origin": "http://localhost:3000"},
        follow_redirects=False,
    )
    # Authentification reussie => 303 vers /actions
    assert resp.status_code == 303
    assert resp.headers.get("location") == "/actions"


def test_login_form_accepts_referer_with_path(client, seed_user, monkeypatch):
    """Un Referer avec path mais bonne origine doit passer (on compare scheme://host)."""
    monkeypatch.setattr(settings, "cors_origins", "http://localhost:3000")
    resp = client.post(
        "/api/v1/auth/login-form",
        data={"email": "test@optiflow.com", "password": "test123"},
        headers={"Referer": "http://localhost:3000/login?error=foo"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers.get("location") == "/actions"
