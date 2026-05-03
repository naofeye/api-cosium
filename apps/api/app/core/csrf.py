"""Protection CSRF par double-submit cookie.

Pattern OWASP : pour toute methode mutante (POST/PUT/PATCH/DELETE) sur une
session authentifiee (cookie `optiflow_token` present), exige le header
`X-CSRF-Token` dont la valeur doit egaler le cookie `optiflow_csrf`.

Le cookie CSRF est volontairement non-httpOnly : le frontend doit pouvoir le
lire via JS pour l'injecter en header sur chaque mutation. SameSite=strict +
secure (en prod) bornent les fuites cross-origin.

Defense en profondeur :
- SameSite=strict sur tous les cookies de session bloque deja la majorite des
  CSRF classiques (cross-origin form submit avec cookies).
- Le double-submit ajoute une couche contre les attaques same-site (XSS dans
  un sous-domaine, redirection ouverte).

Transition (deploy initial / cookie expire) :
- Sur une requete GET authentifiee sans cookie CSRF, le middleware seede le
  cookie dans la reponse. La prochaine mutation aura un cookie a comparer.
"""
from __future__ import annotations

import secrets

from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

CSRF_COOKIE_NAME = "optiflow_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Endpoints qui posent le cookie CSRF (login/signup) ou s'authentifient par
# secret externe (Stripe webhooks, web-vitals beacon). On ne peut pas exiger
# un cookie qui n'existe pas encore. Le refresh token est protege par son
# cookie httpOnly SameSite=strict et doit pouvoir etre rejoue meme si le
# CSRF cookie a expire (rotation legitime).
EXEMPT_PREFIXES: tuple[str, ...] = (
    "/api/v1/auth/login",
    "/api/v1/auth/login-form",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/onboarding/signup",
    "/api/v1/billing/webhooks/",
    "/api/v1/web-vitals",
    "/api/v1/notifications/push/subscribe",
)


def generate_csrf_token() -> str:
    """Genere un token CSRF cryptographiquement sur (43 caracteres URL-safe)."""
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    """Pose le cookie CSRF (lisible JS, SameSite=strict, secure en prod)."""
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
        samesite="strict",
        secure=settings.app_env not in ("local", "development", "test"),
        httponly=False,
    )


def clear_csrf_cookie(response: Response) -> None:
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path="/",
        samesite="strict",
        secure=settings.app_env not in ("local", "development", "test"),
    )


def _is_exempt(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES)


class CsrfMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """Double-submit cookie CSRF protection.

    Skip:
    - Methodes safe (GET/HEAD/OPTIONS/TRACE)
    - Paths exemptes (login/signup/refresh/webhooks externes)
    - Requetes anonymes (pas de cookie de session a forger)
    - App env "test" (suite existante; voir tests/test_csrf.py pour la
      verification dediee qui force l'enforcement)
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if settings.app_env == "test":
            return await call_next(request)

        is_safe = request.method in SAFE_METHODS
        is_authenticated = bool(request.cookies.get("optiflow_token"))
        has_csrf_cookie = bool(request.cookies.get(CSRF_COOKIE_NAME))

        # Methode safe : pas de validation, mais on profite pour seeder le
        # cookie CSRF si l'utilisateur est authentifie sans cookie (transition
        # deploy initial / cookie expire).
        if is_safe:
            response = await call_next(request)
            if is_authenticated and not has_csrf_cookie:
                set_csrf_cookie(response, generate_csrf_token())
            return response

        if _is_exempt(request.url.path):
            return await call_next(request)

        # Pas de session authentifiee = pas de risque CSRF (la requete echouera
        # a la couche auth de toute facon).
        if not is_authenticated:
            return await call_next(request)

        cookie_csrf = request.cookies.get(CSRF_COOKIE_NAME)
        header_csrf = request.headers.get(CSRF_HEADER_NAME)

        if (
            not cookie_csrf
            or not header_csrf
            or not secrets.compare_digest(cookie_csrf, header_csrf)
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "CSRF_INVALID",
                        "message": (
                            "Token CSRF manquant ou invalide. Rechargez la page."
                        ),
                    }
                },
            )

        return await call_next(request)
