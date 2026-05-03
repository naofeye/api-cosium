"""Resolution IP cliente sure (anti-spoofing X-Forwarded-For).

Helper centralise utilise par tout endpoint qui logge ou stocke une IP a
des fins d'audit / signature / preuve juridique.

Politique :
- Par defaut, on prend `request.client.host` (la connexion TCP directe).
- On accepte X-Forwarded-For UNIQUEMENT si `request.client.host` est dans
  la liste `TRUSTED_PROXIES` (settings.trusted_proxies, CSV). Dans ce cas,
  on prend le DERNIER element de la chaine (le hop juste avant le proxy
  trusted, qui est la vue la plus fiable du client reel).
- Vide ou pas de proxy trusted -> on retombe sur le direct_ip.

Codex critique M4 (REVIEW.md 2026-05-03) : la route `/api/public/v1/devis/
{token}/sign` lisait directement `request.headers["x-forwarded-for"]` sans
verifier que le proxy etait trusted. signature_ip etait donc forgeable et
ne valait rien comme preuve d'audit.
"""
from __future__ import annotations

from fastapi import Request

from app.core.config import settings


def trusted_proxies() -> set[str]:
    return {p.strip() for p in settings.trusted_proxies.split(",") if p.strip()}


def client_ip(request: Request) -> str:
    """Resout l'IP cliente avec verification du proxy trusted.

    Retourne `"unknown"` si aucune info disponible (cas tests sans client).
    """
    direct_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and direct_ip in trusted_proxies():
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            # Dernier element = vue du proxy trusted = client reel post-NAT
            return parts[-1]
    return direct_ip
