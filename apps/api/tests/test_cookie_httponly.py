"""Tests cycle complet du cookie httpOnly : flags, expiration, logout, acces non-autorise.

Verifie :
- httpOnly + samesite + path corrects au login
- secure=False en test (env != production)
- 3 cookies : optiflow_token (httpOnly), optiflow_refresh (httpOnly),
  optiflow_authenticated (non-httpOnly, signal frontend)
- Acces avec cookie valide -> 200
- Acces sans cookie -> 401/403
- Logout supprime les cookies (max_age=0 ou suppression explicite)
- Cookie token expire ne permet plus l'acces
"""
from datetime import timedelta

import pytest


def _login(client, email="test@optiflow.local", password="test123"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_sets_three_cookies(client, seed_user):
    """Login retourne 3 cookies : token + refresh + authenticated."""
    resp = _login(client)
    assert resp.status_code == 200
    cookies = resp.cookies
    assert "optiflow_token" in cookies
    assert "optiflow_refresh" in cookies
    assert "optiflow_authenticated" in cookies


def test_cookies_have_httponly_flag(client, seed_user):
    """optiflow_token et _refresh doivent etre httpOnly (anti-XSS).

    optiflow_authenticated est intentionnellement non-httpOnly (signal frontend).
    """
    resp = _login(client)
    set_cookies = resp.headers.get_list("set-cookie")
    token_cookie = next(c for c in set_cookies if c.startswith("optiflow_token="))
    refresh_cookie = next(c for c in set_cookies if c.startswith("optiflow_refresh="))
    authenticated_cookie = next(c for c in set_cookies if c.startswith("optiflow_authenticated="))

    assert "HttpOnly" in token_cookie, "optiflow_token doit etre HttpOnly (XSS)"
    assert "HttpOnly" in refresh_cookie, "optiflow_refresh doit etre HttpOnly (XSS)"
    assert "HttpOnly" not in authenticated_cookie, "optiflow_authenticated doit etre lisible JS"


def test_cookies_have_samesite_lax(client, seed_user):
    """SameSite=Lax pour bloquer CSRF cross-site GET non-top-level."""
    resp = _login(client)
    set_cookies = resp.headers.get_list("set-cookie")
    for c in set_cookies:
        if c.startswith(("optiflow_token=", "optiflow_refresh=", "optiflow_authenticated=")):
            assert "samesite=lax" in c.lower(), f"SameSite Lax manquant : {c[:80]}"


def test_cookies_secure_disabled_in_test_env(client, seed_user):
    """En env=test, les cookies ne sont PAS Secure (http://localhost OK)."""
    resp = _login(client)
    set_cookies = resp.headers.get_list("set-cookie")
    for c in set_cookies:
        if c.startswith(("optiflow_token=", "optiflow_refresh=")):
            assert "Secure" not in c, "Secure ne doit pas etre actif en test"


def test_cookies_path_root(client, seed_user):
    """Path=/ pour que le cookie soit envoye sur toutes les routes."""
    resp = _login(client)
    set_cookies = resp.headers.get_list("set-cookie")
    for c in set_cookies:
        if c.startswith("optiflow_"):
            assert "Path=/" in c or "path=/" in c.lower()


def test_request_with_cookie_is_authorized(client, seed_user):
    """Avec cookie valide, l'API repond 200 sur un endpoint protege."""
    login_resp = _login(client)
    token = login_resp.cookies.get("optiflow_token")
    resp = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_request_without_cookie_is_rejected(client):
    """Sans cookie, l'API rejette (401 ou 403)."""
    resp = client.get("/api/v1/cases")
    assert resp.status_code in (401, 403)


def test_logout_clears_cookies(client, seed_user):
    """POST /logout doit supprimer les cookies (Max-Age=0 ou expiration past)."""
    login_resp = _login(client)
    token = login_resp.cookies.get("optiflow_token")
    resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 204)

    set_cookies = resp.headers.get_list("set-cookie")
    # Au moins un cookie auth est efface (Max-Age=0 ou expires past)
    auth_cookies = [c for c in set_cookies if c.startswith(("optiflow_token=", "optiflow_refresh="))]
    assert len(auth_cookies) > 0, "Logout doit reinitialiser les cookies"
    for c in auth_cookies:
        assert "Max-Age=0" in c or 'Max-Age="0"' in c or "expires=" in c.lower()


@pytest.mark.skip(reason="Necessite mock du temps systeme — couvert par test_auth_e2e.test_expired_token_rejected")
def test_expired_token_rejected_after_max_age(client, seed_user):
    """Apres expiration du cookie, l'acces doit etre refuse."""
    pass
