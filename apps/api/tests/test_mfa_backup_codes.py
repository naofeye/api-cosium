"""Tests MFA backup codes : generation, consommation, integration login."""

import json

import pytest

from app.core.exceptions import BusinessError
from app.services import mfa_service


@pytest.fixture
def mfa_user(db, seed_user):
    """User avec MFA active + secret TOTP genere."""
    mfa_service.start_enrollment(db, seed_user)
    # Activation directe : bypass le check code TOTP pour les tests backup
    seed_user.totp_enabled = True
    db.commit()
    return seed_user


class TestGenerateBackupCodes:
    def test_generate_returns_10_codes(self, db, mfa_user):
        codes = mfa_service.generate_backup_codes(db, mfa_user)
        assert len(codes) == 10

    def test_all_codes_unique(self, db, mfa_user):
        codes = mfa_service.generate_backup_codes(db, mfa_user)
        assert len(set(codes)) == 10

    def test_codes_format_8_hex_upper(self, db, mfa_user):
        codes = mfa_service.generate_backup_codes(db, mfa_user)
        for c in codes:
            assert len(c) == 8
            assert c == c.upper()
            assert all(ch in "0123456789ABCDEF" for ch in c)

    def test_codes_stored_as_hashes_not_clear(self, db, mfa_user):
        codes = mfa_service.generate_backup_codes(db, mfa_user)
        stored = json.loads(mfa_user.totp_backup_codes_hash_json)
        assert len(stored) == 10
        # Aucun code clair n'apparait dans les hashes stockes
        for code in codes:
            assert code not in stored
            # bcrypt hashes commencent par $2b$
            for h in stored:
                assert h.startswith("$2b$")

    def test_generate_replaces_old_codes(self, db, mfa_user):
        codes1 = mfa_service.generate_backup_codes(db, mfa_user)
        codes2 = mfa_service.generate_backup_codes(db, mfa_user)
        assert codes1 != codes2
        # Un code du premier set ne doit plus fonctionner
        assert mfa_service._consume_backup_code_inplace(mfa_user, codes1[0]) is False

    def test_generate_fails_if_mfa_not_enabled(self, db, seed_user):
        with pytest.raises(BusinessError) as exc:
            mfa_service.generate_backup_codes(db, seed_user)
        assert exc.value.code == "MFA_NOT_ENABLED"


class TestCountBackupCodes:
    def test_zero_if_never_generated(self, db, mfa_user):
        assert mfa_service.count_remaining_backup_codes(mfa_user) == 0

    def test_ten_after_generation(self, db, mfa_user):
        mfa_service.generate_backup_codes(db, mfa_user)
        assert mfa_service.count_remaining_backup_codes(mfa_user) == 10

    def test_decrements_on_consume(self, db, mfa_user):
        codes = mfa_service.generate_backup_codes(db, mfa_user)
        mfa_service._consume_backup_code_inplace(mfa_user, codes[0])
        assert mfa_service.count_remaining_backup_codes(mfa_user) == 9


class TestConsumeBackupCode:
    def test_valid_code_consumed_once(self, db, mfa_user):
        codes = mfa_service.generate_backup_codes(db, mfa_user)
        assert mfa_service._consume_backup_code_inplace(mfa_user, codes[0]) is True
        # Meme code ne peut pas etre reutilise
        assert mfa_service._consume_backup_code_inplace(mfa_user, codes[0]) is False

    def test_invalid_code_rejected(self, db, mfa_user):
        mfa_service.generate_backup_codes(db, mfa_user)
        assert mfa_service._consume_backup_code_inplace(mfa_user, "DEADBEEF") is False

    def test_no_codes_stored_rejects(self, db, mfa_user):
        assert mfa_service._consume_backup_code_inplace(mfa_user, "ABCD1234") is False


class TestVerifyLoginCodeIntegration:
    def test_backup_code_accepted_via_verify_login_code(self, db, mfa_user):
        codes = mfa_service.generate_backup_codes(db, mfa_user)
        assert mfa_service.verify_login_code(mfa_user, codes[0]) is True
        # Consomme -> 9 restants
        assert mfa_service.count_remaining_backup_codes(mfa_user) == 9

    def test_backup_code_with_dash_accepted(self, db, mfa_user):
        codes = mfa_service.generate_backup_codes(db, mfa_user)
        c = codes[0]
        formatted = f"{c[:4]}-{c[4:]}"
        assert mfa_service.verify_login_code(mfa_user, formatted) is True

    def test_backup_code_lowercase_accepted(self, db, mfa_user):
        codes = mfa_service.generate_backup_codes(db, mfa_user)
        assert mfa_service.verify_login_code(mfa_user, codes[0].lower()) is True

    def test_invalid_backup_code_rejected(self, db, mfa_user):
        mfa_service.generate_backup_codes(db, mfa_user)
        assert mfa_service.verify_login_code(mfa_user, "ZZZZZZZZ") is False


class TestBackupCodesEndpoints:
    def test_generate_endpoint_requires_mfa_enabled(self, client, auth_headers):
        resp = client.post("/api/v1/auth/mfa/backup-codes/generate", headers=auth_headers)
        # MFA pas active sur le seed_user -> BusinessError 400
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "MFA_NOT_ENABLED"

    def test_count_endpoint_returns_zero_when_no_codes(self, client, auth_headers):
        resp = client.get("/api/v1/auth/mfa/backup-codes/count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == {"remaining": 0}
