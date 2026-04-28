"""Helpers pour poser/effacer les cookies d'authentification HttpOnly.

Centralise la logique pour eviter la divergence entre les routes (login,
signup, refresh, switch-tenant) qui doivent toutes poser exactement le meme
jeu de cookies.
"""
from fastapi import Response

from app.core.config import settings
from app.domain.schemas.auth import TokenResponse


def _cookie_opts() -> dict:
    return {
        "httponly": True,
        "samesite": "strict",
        "secure": settings.app_env not in ("local", "development", "test"),
        "path": "/",
    }


def set_auth_cookies(response: Response, result: TokenResponse) -> None:
    opts = _cookie_opts()
    response.set_cookie(
        "optiflow_token", result.access_token, max_age=settings.access_token_expire_minutes * 60, **opts
    )
    response.set_cookie(
        "optiflow_refresh", result.refresh_token, max_age=settings.refresh_token_expire_days * 86400, **opts
    )
    # Reste non-httpOnly (lisible JS) mais secure=True en prod pour eviter fuite sur HTTP.
    response.set_cookie(
        "optiflow_authenticated",
        "true",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
        samesite="strict",
        secure=settings.app_env not in ("local", "development", "test"),
    )


def clear_auth_cookies(response: Response) -> None:
    opts = _cookie_opts()
    response.delete_cookie("optiflow_token", **opts)
    response.delete_cookie("optiflow_refresh", **opts)
    response.delete_cookie(
        "optiflow_authenticated",
        path="/",
        samesite="strict",
        secure=settings.app_env not in ("local", "development", "test"),
    )
