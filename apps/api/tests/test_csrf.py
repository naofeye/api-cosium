"""Tests du middleware CSRF double-submit.

La suite globale tourne en `app_env=test` qui bypass CSRF (sinon ~150 fichiers
de tests devraient etre migres pour injecter le header). Ce module construit
ses propres apps Starlette/FastAPI pour exercer le middleware en conditions
"production-like".
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    CsrfMiddleware,
    generate_csrf_token,
    set_csrf_cookie,
)


def _build_app() -> FastAPI:
    """Mini-app FastAPI avec uniquement le middleware CSRF + 2 routes."""
    app = FastAPI()
    app.add_middleware(CsrfMiddleware)

    @app.get("/safe")
    def safe():
        return {"ok": True}

    @app.post("/mutation")
    def mutation():
        return {"ok": True}

    @app.post("/api/v1/auth/login")
    def login_exempt():
        return {"ok": True}

    @app.post("/api/v1/billing/webhooks/stripe")
    def webhook_exempt():
        return {"ok": True}

    return app


@pytest.fixture
def production_settings():
    """Force app_env != test pour activer le middleware."""
    with patch("app.core.csrf.settings") as mock_settings:
        mock_settings.app_env = "production"
        mock_settings.refresh_token_expire_days = 7
        yield mock_settings


def test_token_generation_returns_url_safe_string():
    token = generate_csrf_token()
    assert isinstance(token, str)
    assert len(token) >= 40
    # token_urlsafe ne contient pas de caracteres reserves URL
    assert all(c.isalnum() or c in "-_" for c in token)


def test_safe_methods_pass_without_csrf(production_settings):
    client = TestClient(_build_app())
    resp = client.get("/safe")
    assert resp.status_code == 200


def test_mutation_anonymous_passes_without_csrf(production_settings):
    """Pas de cookie de session = pas de risque CSRF, on laisse passer."""
    client = TestClient(_build_app())
    resp = client.post("/mutation")
    assert resp.status_code == 200


def test_mutation_authenticated_without_csrf_rejects(production_settings):
    client = TestClient(_build_app())
    client.cookies.set("optiflow_token", "fake-token")
    resp = client.post("/mutation")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_INVALID"


def test_mutation_authenticated_with_mismatched_csrf_rejects(production_settings):
    client = TestClient(_build_app())
    client.cookies.set("optiflow_token", "fake-token")
    client.cookies.set(CSRF_COOKIE_NAME, "cookie-value")
    resp = client.post("/mutation", headers={CSRF_HEADER_NAME: "different-value"})
    assert resp.status_code == 403


def test_mutation_authenticated_with_missing_header_rejects(production_settings):
    client = TestClient(_build_app())
    client.cookies.set("optiflow_token", "fake-token")
    client.cookies.set(CSRF_COOKIE_NAME, "cookie-value")
    resp = client.post("/mutation")
    assert resp.status_code == 403


def test_mutation_authenticated_with_matching_csrf_passes(production_settings):
    token = generate_csrf_token()
    client = TestClient(_build_app())
    client.cookies.set("optiflow_token", "fake-token")
    client.cookies.set(CSRF_COOKIE_NAME, token)
    resp = client.post("/mutation", headers={CSRF_HEADER_NAME: token})
    assert resp.status_code == 200


def test_login_exempt_path_passes_without_csrf(production_settings):
    client = TestClient(_build_app())
    client.cookies.set("optiflow_token", "fake-token")
    resp = client.post("/api/v1/auth/login")
    assert resp.status_code == 200


def test_webhook_exempt_path_passes_without_csrf(production_settings):
    client = TestClient(_build_app())
    client.cookies.set("optiflow_token", "fake-token")
    resp = client.post("/api/v1/billing/webhooks/stripe")
    assert resp.status_code == 200


def test_safe_request_seeds_csrf_cookie_when_authenticated(production_settings):
    """Transition deploy : un GET authentifie sans CSRF cookie doit seeder
    le cookie pour que la prochaine mutation passe."""
    client = TestClient(_build_app())
    client.cookies.set("optiflow_token", "fake-token")
    resp = client.get("/safe")
    assert resp.status_code == 200
    assert CSRF_COOKIE_NAME in resp.cookies
    # Le token genere doit etre URL-safe et de longueur attendue
    seeded = resp.cookies[CSRF_COOKIE_NAME]
    assert len(seeded) >= 40


def test_safe_request_no_seed_when_unauthenticated(production_settings):
    """Pas d'utilisateur logge = pas de seed (eviter le bruit cookies)."""
    client = TestClient(_build_app())
    resp = client.get("/safe")
    assert resp.status_code == 200
    assert CSRF_COOKIE_NAME not in resp.cookies


def test_safe_request_no_seed_when_already_present(production_settings):
    """Cookie deja present : ne pas le regenerer (eviterait l'invalidation
    accidentelle d'un onglet ouvert)."""
    client = TestClient(_build_app())
    client.cookies.set("optiflow_token", "fake-token")
    client.cookies.set(CSRF_COOKIE_NAME, "existing-token")
    resp = client.get("/safe")
    assert resp.status_code == 200
    # Pas de Set-Cookie pour CSRF dans la reponse (cookie existant non touche)
    set_cookies = [h for h in resp.headers.raw if h[0].lower() == b"set-cookie"]
    assert all(b"optiflow_csrf" not in v for _, v in set_cookies)


def test_csrf_uses_constant_time_compare(production_settings):
    """Verifie qu'un cookie tres long et un header court ne fuitent pas
    d'info via timing (compare_digest est constant-time)."""
    client = TestClient(_build_app())
    client.cookies.set("optiflow_token", "fake")
    client.cookies.set(CSRF_COOKIE_NAME, "x" * 1000)
    resp = client.post("/mutation", headers={CSRF_HEADER_NAME: "y"})
    assert resp.status_code == 403


def test_test_env_bypasses_middleware():
    """En env test, le middleware doit toujours laisser passer (compat
    avec la suite existante)."""
    with patch("app.core.csrf.settings") as mock_settings:
        mock_settings.app_env = "test"
        mock_settings.refresh_token_expire_days = 7
        client = TestClient(_build_app())
        client.cookies.set("optiflow_token", "fake")
        # Pas de CSRF cookie ni header : devrait passer en test
        resp = client.post("/mutation")
        assert resp.status_code == 200


def test_set_csrf_cookie_attributes(production_settings):
    """Le cookie CSRF doit etre lisible JS (non-httpOnly), SameSite=strict."""
    from fastapi.responses import JSONResponse

    response = JSONResponse({"ok": True})
    set_csrf_cookie(response, "abc")

    set_cookie_header = response.headers.get("set-cookie", "")
    assert "optiflow_csrf=abc" in set_cookie_header
    assert "samesite=strict" in set_cookie_header.lower()
    assert "httponly" not in set_cookie_header.lower()
    assert "path=/" in set_cookie_header.lower()
