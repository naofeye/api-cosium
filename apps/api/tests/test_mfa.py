"""Tests du service MFA/TOTP."""

import pyotp
import pytest

from app.core.exceptions import AuthenticationError, BusinessError
from app.models import User
from app.security import hash_password
from app.services import mfa_service


def _create_user(db) -> User:
    u = User(email=f"mfa_user@test.com", password_hash=hash_password("password123"), role="admin", is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_generate_secret_is_base32_16_chars() -> None:
    s = mfa_service.generate_secret()
    assert len(s) == 32
    # Base32 alphabet
    assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in s)


def test_verify_code_accepts_valid_and_rejects_invalid(db) -> None:
    secret = mfa_service.generate_secret()
    totp = pyotp.TOTP(secret)
    assert mfa_service.verify_code(secret, totp.now()) is True
    assert mfa_service.verify_code(secret, "000000") is False
    assert mfa_service.verify_code(secret, "abc") is False
    assert mfa_service.verify_code(secret, "") is False


def test_start_enrollment_generates_secret(db) -> None:
    u = _create_user(db)
    result = mfa_service.start_enrollment(db, u)
    assert "secret" in result
    assert result["otpauth_uri"].startswith("otpauth://totp/")
    db.refresh(u)
    assert u.totp_secret_enc is not None
    assert u.totp_enabled is False


def test_start_enrollment_fails_if_already_enabled(db) -> None:
    u = _create_user(db)
    u.totp_enabled = True
    db.commit()
    with pytest.raises(BusinessError):
        mfa_service.start_enrollment(db, u)


def test_enable_mfa_with_valid_code(db) -> None:
    u = _create_user(db)
    result = mfa_service.start_enrollment(db, u)
    totp = pyotp.TOTP(result["secret"])
    mfa_service.enable_mfa(db, u, totp.now())
    db.refresh(u)
    assert u.totp_enabled is True


def test_enable_mfa_rejects_invalid_code(db) -> None:
    u = _create_user(db)
    mfa_service.start_enrollment(db, u)
    with pytest.raises(AuthenticationError):
        mfa_service.enable_mfa(db, u, "123456")


def test_disable_mfa_requires_password_verified(db) -> None:
    u = _create_user(db)
    result = mfa_service.start_enrollment(db, u)
    totp = pyotp.TOTP(result["secret"])
    mfa_service.enable_mfa(db, u, totp.now())
    with pytest.raises(AuthenticationError):
        mfa_service.disable_mfa(db, u, password_verified=False)
    mfa_service.disable_mfa(db, u, password_verified=True)
    db.refresh(u)
    assert u.totp_enabled is False
    assert u.totp_secret_enc is None


def test_verify_login_code_no_mfa_returns_true(db) -> None:
    u = _create_user(db)
    # Pas de MFA → toujours True (bypass)
    assert mfa_service.verify_login_code(u, "") is True


def test_verify_login_code_with_mfa(db) -> None:
    u = _create_user(db)
    result = mfa_service.start_enrollment(db, u)
    totp = pyotp.TOTP(result["secret"])
    mfa_service.enable_mfa(db, u, totp.now())
    db.refresh(u)
    assert mfa_service.verify_login_code(u, totp.now()) is True
    assert mfa_service.verify_login_code(u, "000000") is False
