"""Tests unitaires pour mfa_service.

Couvre les cas non couverts par test_mfa.py et test_mfa_backup_codes.py :
- generate_secret avec mock pyotp
- provisioning_uri construit correctement
- verify_code : cas limites (espace, non-digits, longueur incorrecte)
- enable_mfa : pas de secret pre-enrolement
- disable_mfa : reset complet des champs
- verify_login_code : decrypt failure, cas MFA inactif
- count_remaining_backup_codes : JSON invalide / None
- _consume_backup_code_inplace : JSON invalide en base
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError, BusinessError
from app.models import User
from app.security import hash_password
from app.services import mfa_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user(db, email: str = "mfa_svc@test.com") -> User:
    u = User(email=email, password_hash=hash_password("password123"), role="admin", is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ---------------------------------------------------------------------------
# generate_secret
# ---------------------------------------------------------------------------


class TestGenerateSecret:
    def test_delegates_to_pyotp_random_base32(self):
        with patch("app.services.mfa_service.pyotp.random_base32", return_value="MOCKED32CHARSSECRET12345678901") as mock_fn:
            result = mfa_service.generate_secret()
        mock_fn.assert_called_once()
        assert result == "MOCKED32CHARSSECRET12345678901"

    def test_real_secret_is_valid_base32(self):
        secret = mfa_service.generate_secret()
        assert len(secret) == 32
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567")
        assert all(c in valid_chars for c in secret)

    def test_two_secrets_are_different(self):
        s1 = mfa_service.generate_secret()
        s2 = mfa_service.generate_secret()
        assert s1 != s2


# ---------------------------------------------------------------------------
# provisioning_uri
# ---------------------------------------------------------------------------


class TestProvisioningUri:
    def test_uri_contains_email_and_issuer(self):
        secret = mfa_service.generate_secret()
        uri = mfa_service.provisioning_uri("user@example.com", secret)
        assert "user%40example.com" in uri or "user@example.com" in uri
        assert "OptiFlow" in uri

    def test_uri_starts_with_otpauth(self):
        secret = mfa_service.generate_secret()
        uri = mfa_service.provisioning_uri("u@test.com", secret)
        assert uri.startswith("otpauth://totp/")

    def test_uri_mocked(self):
        mock_totp = MagicMock()
        mock_totp.provisioning_uri.return_value = "otpauth://totp/mock"
        with patch("app.services.mfa_service.pyotp.totp.TOTP", return_value=mock_totp):
            result = mfa_service.provisioning_uri("a@b.com", "SECRET")
        mock_totp.provisioning_uri.assert_called_once_with(name="a@b.com", issuer_name="OptiFlow AI")
        assert result == "otpauth://totp/mock"


# ---------------------------------------------------------------------------
# verify_code
# ---------------------------------------------------------------------------


class TestVerifyCode:
    def test_empty_code_rejected(self):
        assert mfa_service.verify_code("SECRET", "") is False

    def test_whitespace_only_rejected(self):
        assert mfa_service.verify_code("SECRET", "   ") is False

    def test_non_digit_code_rejected(self):
        assert mfa_service.verify_code("SECRET", "abcdef") is False

    def test_too_short_code_rejected(self):
        assert mfa_service.verify_code("SECRET", "12345") is False

    def test_too_long_code_rejected(self):
        assert mfa_service.verify_code("SECRET", "1234567") is False

    def test_valid_code_with_leading_space_accepted(self):
        """verify_code doit strip() le code avant verification."""
        secret = mfa_service.generate_secret()
        import pyotp
        good_code = pyotp.TOTP(secret).now()
        # Le service applique .strip() donc l'espace autour ne doit pas poser probleme
        assert mfa_service.verify_code(secret, f" {good_code} ") is True

    def test_delegates_to_pyotp_totp_verify(self):
        mock_totp = MagicMock()
        mock_totp.verify.return_value = True
        with patch("app.services.mfa_service.pyotp.TOTP", return_value=mock_totp):
            result = mfa_service.verify_code("SECRET123", "123456", valid_window=2)
        mock_totp.verify.assert_called_once_with("123456", valid_window=2)
        assert result is True

    def test_wrong_code_returns_false_via_mock(self):
        mock_totp = MagicMock()
        mock_totp.verify.return_value = False
        with patch("app.services.mfa_service.pyotp.TOTP", return_value=mock_totp):
            result = mfa_service.verify_code("ANYSECRET", "999999")
        assert result is False


# ---------------------------------------------------------------------------
# start_enrollment
# ---------------------------------------------------------------------------


class TestStartEnrollment:
    def test_stores_encrypted_secret(self, db):
        u = _create_user(db, "enroll_enc@test.com")
        with patch("app.services.mfa_service.encrypt", return_value="ENCRYPTED") as mock_enc:
            result = mfa_service.start_enrollment(db, u)
        mock_enc.assert_called_once()
        db.refresh(u)
        assert u.totp_secret_enc == "ENCRYPTED"
        assert "secret" in result

    def test_raises_if_already_enabled(self, db):
        u = _create_user(db, "enroll_dup@test.com")
        u.totp_enabled = True
        db.commit()
        with pytest.raises(BusinessError) as exc:
            mfa_service.start_enrollment(db, u)
        assert exc.value.code == "MFA_ALREADY_ENABLED"

    def test_result_contains_issuer(self, db):
        u = _create_user(db, "enroll_issuer@test.com")
        result = mfa_service.start_enrollment(db, u)
        assert result["issuer"] == "OptiFlow AI"


# ---------------------------------------------------------------------------
# enable_mfa
# ---------------------------------------------------------------------------


class TestEnableMfa:
    def test_raises_already_enabled(self, db):
        u = _create_user(db, "enable_dup@test.com")
        u.totp_enabled = True
        db.commit()
        with pytest.raises(BusinessError) as exc:
            mfa_service.enable_mfa(db, u, "123456")
        assert exc.value.code == "MFA_ALREADY_ENABLED"

    def test_raises_if_no_secret_enrolled(self, db):
        u = _create_user(db, "enable_nosecret@test.com")
        # totp_secret_enc est None par defaut
        with pytest.raises(BusinessError) as exc:
            mfa_service.enable_mfa(db, u, "123456")
        assert exc.value.code == "MFA_NOT_ENROLLED"

    def test_raises_on_invalid_code(self, db):
        u = _create_user(db, "enable_badcode@test.com")
        mfa_service.start_enrollment(db, u)
        with pytest.raises(AuthenticationError):
            mfa_service.enable_mfa(db, u, "000000")

    def test_enable_sets_totp_last_used_at(self, db):
        import pyotp
        u = _create_user(db, "enable_ts@test.com")
        result = mfa_service.start_enrollment(db, u)
        code = pyotp.TOTP(result["secret"]).now()
        mfa_service.enable_mfa(db, u, code)
        db.refresh(u)
        assert u.totp_last_used_at is not None

    def test_enable_calls_decrypt_on_stored_secret(self, db):
        u = _create_user(db, "enable_decrypt@test.com")
        mfa_service.start_enrollment(db, u)
        import pyotp
        # Decrypt renverra un vrai secret genere par start_enrollment
        # On peut mocker verify_code pour ne pas avoir a generer un code valide
        with (
            patch("app.services.mfa_service.decrypt", return_value="FAUXSECRET") as mock_dec,
            patch("app.services.mfa_service.verify_code", return_value=True),
        ):
            mfa_service.enable_mfa(db, u, "123456")
        mock_dec.assert_called_once_with(u.totp_secret_enc)


# ---------------------------------------------------------------------------
# disable_mfa
# ---------------------------------------------------------------------------


class TestDisableMfa:
    def test_raises_if_password_not_verified(self, db):
        import pyotp
        u = _create_user(db, "disable_nopwd@test.com")
        result = mfa_service.start_enrollment(db, u)
        code = pyotp.TOTP(result["secret"]).now()
        mfa_service.enable_mfa(db, u, code)
        with pytest.raises(AuthenticationError):
            mfa_service.disable_mfa(db, u, password_verified=False)

    def test_clears_all_mfa_fields(self, db):
        import pyotp
        u = _create_user(db, "disable_clear@test.com")
        result = mfa_service.start_enrollment(db, u)
        code = pyotp.TOTP(result["secret"]).now()
        mfa_service.enable_mfa(db, u, code)
        mfa_service.disable_mfa(db, u, password_verified=True)
        db.refresh(u)
        assert u.totp_enabled is False
        assert u.totp_secret_enc is None
        assert u.totp_last_used_at is None

    def test_disable_works_even_if_mfa_not_active(self, db):
        """disable_mfa ne devrait pas lever d'erreur si MFA n'est pas active (password verifie)."""
        u = _create_user(db, "disable_inactive@test.com")
        # Ne doit pas lever d'exception
        mfa_service.disable_mfa(db, u, password_verified=True)
        db.refresh(u)
        assert u.totp_enabled is False


# ---------------------------------------------------------------------------
# verify_login_code
# ---------------------------------------------------------------------------


class TestVerifyLoginCode:
    def test_returns_true_when_mfa_disabled(self, db):
        u = _create_user(db, "vlc_disabled@test.com")
        assert u.totp_enabled is False
        assert mfa_service.verify_login_code(u, "") is True

    def test_returns_true_when_no_secret_stored(self, db):
        """totp_enabled=False et pas de secret => bypass MFA."""
        u = _create_user(db, "vlc_nosecret@test.com")
        assert mfa_service.verify_login_code(u, "123456") is True

    def test_returns_false_on_decrypt_failure(self, db):
        import pyotp
        u = _create_user(db, "vlc_decrypt_fail@test.com")
        result = mfa_service.start_enrollment(db, u)
        code = pyotp.TOTP(result["secret"]).now()
        mfa_service.enable_mfa(db, u, code)
        db.refresh(u)

        with patch("app.services.mfa_service.decrypt", side_effect=Exception("key error")):
            assert mfa_service.verify_login_code(u, "123456") is False

    def test_valid_totp_returns_true(self, db):
        import pyotp
        u = _create_user(db, "vlc_valid@test.com")
        result = mfa_service.start_enrollment(db, u)
        totp = pyotp.TOTP(result["secret"])
        mfa_service.enable_mfa(db, u, totp.now())
        db.refresh(u)
        assert mfa_service.verify_login_code(u, totp.now()) is True

    def test_invalid_totp_returns_false(self, db):
        import pyotp
        u = _create_user(db, "vlc_invalid@test.com")
        result = mfa_service.start_enrollment(db, u)
        totp = pyotp.TOTP(result["secret"])
        mfa_service.enable_mfa(db, u, totp.now())
        db.refresh(u)
        assert mfa_service.verify_login_code(u, "000000") is False

    def test_code_with_spaces_normalized(self, db):
        """Les espaces autour du code doivent etre ignores."""
        import pyotp
        u = _create_user(db, "vlc_space@test.com")
        result = mfa_service.start_enrollment(db, u)
        totp = pyotp.TOTP(result["secret"])
        mfa_service.enable_mfa(db, u, totp.now())
        db.refresh(u)
        good_code = totp.now()
        assert mfa_service.verify_login_code(u, f"  {good_code}  ") is True

    def test_non_digit_non_hex_code_rejected(self, db):
        import pyotp
        u = _create_user(db, "vlc_garbage@test.com")
        result = mfa_service.start_enrollment(db, u)
        totp = pyotp.TOTP(result["secret"])
        mfa_service.enable_mfa(db, u, totp.now())
        db.refresh(u)
        # Ni 6 digits, ni 8 hex chars => False
        assert mfa_service.verify_login_code(u, "SHORT") is False


# ---------------------------------------------------------------------------
# count_remaining_backup_codes — edge cases
# ---------------------------------------------------------------------------


class TestCountRemainingBackupCodesEdgeCases:
    def test_none_json_returns_zero(self, db):
        u = _create_user(db, "count_none@test.com")
        u.totp_backup_codes_hash_json = None
        assert mfa_service.count_remaining_backup_codes(u) == 0

    def test_invalid_json_returns_zero(self, db):
        u = _create_user(db, "count_invalid@test.com")
        u.totp_backup_codes_hash_json = "NOT_VALID_JSON{{{"
        assert mfa_service.count_remaining_backup_codes(u) == 0

    def test_empty_list_json_returns_zero(self, db):
        import json
        u = _create_user(db, "count_empty@test.com")
        u.totp_backup_codes_hash_json = json.dumps([])
        assert mfa_service.count_remaining_backup_codes(u) == 0

    def test_three_codes_returns_three(self, db):
        import json
        u = _create_user(db, "count_three@test.com")
        u.totp_backup_codes_hash_json = json.dumps(["$2b$12$aaa", "$2b$12$bbb", "$2b$12$ccc"])
        assert mfa_service.count_remaining_backup_codes(u) == 3


# ---------------------------------------------------------------------------
# _consume_backup_code_inplace — edge cases
# ---------------------------------------------------------------------------


class TestConsumeBackupCodeEdgeCases:
    def test_invalid_json_returns_false(self, db):
        u = _create_user(db, "consume_bad_json@test.com")
        u.totp_backup_codes_hash_json = "{INVALID"
        assert mfa_service._consume_backup_code_inplace(u, "ABCD1234") is False

    def test_none_json_returns_false(self, db):
        u = _create_user(db, "consume_none@test.com")
        u.totp_backup_codes_hash_json = None
        assert mfa_service._consume_backup_code_inplace(u, "ABCD1234") is False

    def test_remaining_codes_decremented_after_consume(self, db, seed_user):
        import pyotp
        mfa_service.start_enrollment(db, seed_user)
        seed_user.totp_enabled = True
        db.commit()
        codes = mfa_service.generate_backup_codes(db, seed_user)
        before = mfa_service.count_remaining_backup_codes(seed_user)
        mfa_service._consume_backup_code_inplace(seed_user, codes[3])
        after = mfa_service.count_remaining_backup_codes(seed_user)
        assert after == before - 1

    def test_code_no_longer_valid_after_consume(self, db, seed_user):
        mfa_service.start_enrollment(db, seed_user)
        seed_user.totp_enabled = True
        db.commit()
        codes = mfa_service.generate_backup_codes(db, seed_user)
        assert mfa_service._consume_backup_code_inplace(seed_user, codes[0]) is True
        assert mfa_service._consume_backup_code_inplace(seed_user, codes[0]) is False


# ---------------------------------------------------------------------------
# generate_backup_codes — via mocked hash_password
# ---------------------------------------------------------------------------


class TestGenerateBackupCodesMocked:
    def test_each_code_is_hashed_via_hash_password(self, db, seed_user):
        mfa_service.start_enrollment(db, seed_user)
        seed_user.totp_enabled = True
        db.commit()

        with patch("app.services.mfa_service.hash_password", side_effect=lambda c: f"HASH({c})") as mock_hash:
            codes = mfa_service.generate_backup_codes(db, seed_user)

        assert mock_hash.call_count == mfa_service.BACKUP_CODE_COUNT
        import json
        stored = json.loads(seed_user.totp_backup_codes_hash_json)
        for code in codes:
            assert f"HASH({code})" in stored

    def test_raises_if_mfa_not_enabled(self, db):
        u = _create_user(db, "gen_bkp_disabled@test.com")
        with pytest.raises(BusinessError) as exc:
            mfa_service.generate_backup_codes(db, u)
        assert exc.value.code == "MFA_NOT_ENABLED"
