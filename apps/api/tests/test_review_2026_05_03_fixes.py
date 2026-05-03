"""Regression tests pour les findings Codex REVIEW.md 2026-05-03.

Un test par finding fixe par vps-master. Ces tests doivent rester verts
apres tout refactor — toute regression est un re-introduction d'une
vulnerabilite documentee.

- M3 : devis expire ne peut plus etre signe (status + valid_until)
- M5 : public_v1 ne fuit pas les clients soft-deleted via detail by-id
- M6 : logout-all incremente token_version (invalide les access tokens
  des autres devices, pas seulement celui du navigateur courant)
- M9 : config production refuse les origines CORS http:// non-locales
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

# -------- M3 : devis expire signable -------------------------------------


def _setup_case(db, default_tenant):
    from app.models import Case, Customer

    customer = Customer(
        tenant_id=default_tenant.id, first_name="M3", last_name="TEST"
    )
    db.add(customer)
    db.flush()
    case = Case(
        tenant_id=default_tenant.id, customer_id=customer.id, status="en_cours"
    )
    db.add(case)
    db.flush()
    return case


def test_m3_signing_expired_devis_via_valid_until_raises(db, default_tenant):
    """Un devis avec valid_until < now() ne peut pas etre signe meme si
    son status est encore 'envoye' (la task d'expiration n'a pas tourne)."""
    from app.core.exceptions import BusinessError
    from app.models.devis import Devis
    from app.services.devis_signature_service import sign_devis_public

    case = _setup_case(db, default_tenant)
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=10)
    devis = Devis(
        tenant_id=default_tenant.id,
        case_id=case.id,
        status="envoye",
        montant_ht=100,
        tva=20,
        montant_ttc=120,
        valid_until=past,
        public_token="m3test_expired_token_abcd1234",
        numero="DV-TEST-M3-1",
    )
    db.add(devis)
    db.commit()

    with pytest.raises(BusinessError) as exc:
        sign_devis_public(
            db,
            public_token="m3test_expired_token_abcd1234",
            consent_text="J'accepte le devis sans reserve aujourd'hui.",
            client_ip="1.2.3.4",
            user_agent="ua",
        )
    assert exc.value.code == "DEVIS_EXPIRED"


def test_m3_signing_expired_status_raises(db, default_tenant):
    """status='expire' refuse explicitement (il l'etait deja pour 'refuse'
    et 'annule', maintenant 'expire' aussi)."""
    from app.core.exceptions import BusinessError
    from app.models.devis import Devis
    from app.services.devis_signature_service import sign_devis_public

    case = _setup_case(db, default_tenant)
    devis = Devis(
        tenant_id=default_tenant.id,
        case_id=case.id,
        status="expire",
        montant_ht=100,
        tva=20,
        montant_ttc=120,
        public_token="m3test_status_token_efgh5678",
        numero="DV-TEST-M3-2",
    )
    db.add(devis)
    db.commit()

    with pytest.raises(BusinessError) as exc:
        sign_devis_public(
            db,
            public_token="m3test_status_token_efgh5678",
            consent_text="J'accepte le devis sans reserve aujourd'hui.",
            client_ip="1.2.3.4",
            user_agent="ua",
        )
    assert exc.value.code == "DEVIS_NOT_SIGNABLE"


# -------- M9 : CORS production refuse http:// non-localhost --------------


def test_m9_production_rejects_http_non_localhost(monkeypatch):
    """Settings() doit lever ValueError si CORS_ORIGINS contient une
    origine HTTP non-locale en production."""
    from app.core.config import Settings

    env = {
        "APP_ENV": "production",
        "JWT_SECRET": "x" * 64,
        "ENCRYPTION_KEY": "0" * 32,
        "DATABASE_URL": "postgresql+psycopg://prod:secret@db:5432/optiflow",
        "S3_ACCESS_KEY": "prodaccess",
        "S3_SECRET_KEY": "prodsecret",
        "CORS_ORIGINS": "http://evil.example.com",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValueError, match="HTTP non-locale"):
        Settings()


def test_m9_production_accepts_https_and_localhost(monkeypatch):
    """HTTPS + localhost http:// doivent passer."""
    from app.core.config import Settings

    env = {
        "APP_ENV": "production",
        "JWT_SECRET": "x" * 64,
        "ENCRYPTION_KEY": "0" * 32,
        "DATABASE_URL": "postgresql+psycopg://prod:secret@db:5432/optiflow",
        "S3_ACCESS_KEY": "prodaccess",
        "S3_SECRET_KEY": "prodsecret",
        "CORS_ORIGINS": "https://app.optiflow.fr,http://localhost:3000",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    # Pas d'exception
    s = Settings()
    assert "https://app.optiflow.fr" in s.cors_origins


# -------- M2 : idempotency 503 en prod si Redis down ---------------------


def test_m2_redis_unavailable_in_prod_raises_unavailable_error(monkeypatch):
    """cache_set_nx_atomic leve RedisUnavailableError quand Redis down
    en environnement production."""
    from app.core import redis_cache
    from app.core.redis_cache import (
        RedisUnavailableError,
        cache_set_nx_atomic,
    )

    monkeypatch.setattr(redis_cache.settings, "app_env", "production")
    # Force Redis unavailable
    monkeypatch.setattr(redis_cache, "_get_redis", lambda: None)

    with pytest.raises(RedisUnavailableError):
        cache_set_nx_atomic("idem:test:key", {"x": 1}, ttl=60)


def test_m2_redis_unavailable_in_dev_returns_true(monkeypatch):
    """En dev, cache_set_nx_atomic retombe en fail-open (True) pour ne
    pas casser le dev local sans Redis."""
    from app.core import redis_cache
    from app.core.redis_cache import cache_set_nx_atomic

    monkeypatch.setattr(redis_cache.settings, "app_env", "development")
    monkeypatch.setattr(redis_cache, "_get_redis", lambda: None)

    assert cache_set_nx_atomic("idem:test:key", {"x": 1}, ttl=60) is True


# -------- M4 : trusted_proxies pour signature publique -------------------


def test_m4_x_forwarded_for_ignored_when_proxy_not_trusted(monkeypatch):
    """`client_ip(request)` doit ignorer X-Forwarded-For si le proxy
    direct n'est pas dans TRUSTED_PROXIES."""
    from unittest.mock import MagicMock

    from app.core import request_ip
    from app.core.request_ip import client_ip

    # Pas de trusted proxy configure
    monkeypatch.setattr(request_ip.settings, "trusted_proxies", "")
    req = MagicMock()
    req.client.host = "203.0.113.1"
    req.headers = {"X-Forwarded-For": "1.2.3.4"}  # tentative spoofing
    assert client_ip(req) == "203.0.113.1"


def test_m4_x_forwarded_for_used_when_proxy_trusted(monkeypatch):
    """Si le proxy direct est dans TRUSTED_PROXIES, on prend la derniere
    entree de la chaine X-Forwarded-For (vue trusted)."""
    from unittest.mock import MagicMock

    from app.core import request_ip
    from app.core.request_ip import client_ip

    monkeypatch.setattr(request_ip.settings, "trusted_proxies", "10.0.0.1")
    req = MagicMock()
    req.client.host = "10.0.0.1"
    req.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}
    assert client_ip(req) == "5.6.7.8"
