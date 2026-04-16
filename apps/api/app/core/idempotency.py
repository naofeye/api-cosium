"""Idempotence générique Redis-backed pour endpoints POST critiques.

Usage (route POST) :

    @router.post("/devis", response_model=DevisResponse, status_code=201)
    def create_devis(
        payload: DevisCreate,
        request: Request,
        tenant_ctx: TenantContext = Depends(get_tenant_context),
        idem: IdempotencyContext = Depends(idempotency("devis:create")),
    ):
        if idem.cached:
            return idem.cached
        result = devis_service.create_devis(...)
        idem.store(result)
        return result

Si le client fournit `X-Idempotency-Key`, la réponse est cachée 24h par clé
`idempotency:{tenant_id}:{scope}:{key}:{body_hash}`. Un rejeu avec les mêmes
key+body retourne la réponse originale sans ré-exécution.

Collisions (même key, body différent) → 409.
Pas de clé fournie → pas d'idempotence, exécution normale.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.redis_cache import cache_get, cache_set
from app.core.tenant_context import TenantContext, get_tenant_context

_TTL_SECONDS = 24 * 3600


def _hash_body(body: bytes) -> str:
    return hashlib.sha256(body or b"").hexdigest()[:16]


def _key(scope: str, tenant_id: int, idem_key: str) -> str:
    return f"idempotency:{tenant_id}:{scope}:{idem_key}"


@dataclass
class IdempotencyContext:
    scope: str
    tenant_id: int
    key: str | None
    body_hash: str | None
    cached: Any | None = None
    _redis_key: str | None = field(default=None, repr=False)

    def store(self, response: Any) -> None:
        """Persiste la réponse (dict/list/serializable) pour les replays."""
        if not self._redis_key or self.body_hash is None:
            return
        try:
            payload = response if isinstance(response, (dict, list)) else json.loads(
                json.dumps(response, default=lambda o: getattr(o, "model_dump", lambda: str(o))())
            )
        except Exception:
            payload = {"_stored": True}
        cache_set(
            self._redis_key,
            {"body_hash": self.body_hash, "response": payload},
            ttl=_TTL_SECONDS,
        )


def idempotency(scope: str):
    """Factory de dependance FastAPI pour un scope donné (ex: 'devis:create')."""

    async def _dep(
        request: Request,
        tenant_ctx: TenantContext = Depends(get_tenant_context),
        x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    ) -> IdempotencyContext:
        ctx = IdempotencyContext(
            scope=scope,
            tenant_id=tenant_ctx.tenant_id,
            key=x_idempotency_key,
            body_hash=None,
        )
        if not x_idempotency_key:
            return ctx

        body = await request.body()
        ctx.body_hash = _hash_body(body)
        ctx._redis_key = _key(scope, tenant_ctx.tenant_id, x_idempotency_key)

        existing = cache_get(ctx._redis_key)
        if existing:
            if existing.get("body_hash") and existing["body_hash"] != ctx.body_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "IDEMPOTENCY_KEY_REUSED",
                        "message": "Cette cle d'idempotence a deja ete utilisee avec un corps different.",
                    },
                )
            ctx.cached = existing.get("response")
        return ctx

    return _dep
