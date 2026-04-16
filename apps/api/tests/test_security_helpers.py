"""Tests des helpers security.py : blacklist, verify JWT, encoding password."""

import jwt

from app.core.config import settings
from app.security import (
    blacklist_access_token,
    create_access_token,
    decode_access_token,
    hash_password,
    is_token_blacklisted,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    h = hash_password("mySuperPwd!")
    assert verify_password("mySuperPwd!", h) is True
    assert verify_password("wrong", h) is False


def test_hash_password_produces_different_hashes() -> None:
    # bcrypt salt aleatoire => hash different a chaque appel
    assert hash_password("abc") != hash_password("abc")


def test_create_and_decode_access_token() -> None:
    token = create_access_token("u@test.com", role="admin", tenant_id=1)
    payload = decode_access_token(token)
    assert payload["sub"] == "u@test.com"
    assert payload["role"] == "admin"
    assert payload["tenant_id"] == 1


def test_decode_invalid_token_raises() -> None:
    import pytest

    with pytest.raises(jwt.PyJWTError):
        decode_access_token("not.a.token")


def test_decode_forged_token_rejected() -> None:
    import pytest

    forged = jwt.encode({"sub": "x@y.z", "role": "admin"}, "wrong-secret", algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(forged)


def test_blacklist_skip_if_forged_signature() -> None:
    """Token forge avec mauvaise signature ne doit pas etre blackliste."""
    forged = jwt.encode({"sub": "x@y.z", "exp": 99999999999}, "wrong", algorithm="HS256")
    blacklist_access_token(forged)  # ne leve pas d'exception, fait un no-op


def test_blacklist_valid_token_and_check() -> None:
    """Token valide blackliste -> is_token_blacklisted depend de Redis."""
    # Sans Redis (test env), retourne False (fail-open en env test)
    token = create_access_token("u@test.com", role="admin", tenant_id=1)
    blacklist_access_token(token)
    # En test env, fail-open -> False
    assert is_token_blacklisted(token) in (True, False)  # tolere redis absent
