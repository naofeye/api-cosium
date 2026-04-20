"""Tests for app/services/auth_lockout.py.

Redis is mocked via unittest.mock.patch so no real Redis instance is needed.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import AuthenticationError
from app.services.auth_lockout import (
    MAX_LOGIN_ATTEMPTS,
    LOCKOUT_SECONDS,
    check_account_lockout,
    clear_login_attempts,
    record_failed_login,
)

EMAIL = "user@example.com"
REDIS_MODULE = "app.core.redis_cache.get_redis_client"


# ---------------------------------------------------------------------------
# check_account_lockout
# ---------------------------------------------------------------------------


class TestCheckAccountLockout:
    def test_no_lockout_when_no_attempts(self):
        """Account is not locked when Redis has no entry for the email."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch(REDIS_MODULE, return_value=mock_redis):
            # Should not raise
            check_account_lockout(EMAIL)

        mock_redis.get.assert_called_once_with(f"login_attempts:{EMAIL}")

    def test_no_lockout_below_max_attempts(self):
        """Account is not locked when attempts are below the threshold."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = str(MAX_LOGIN_ATTEMPTS - 1)

        with patch(REDIS_MODULE, return_value=mock_redis):
            check_account_lockout(EMAIL)  # must not raise

    def test_lockout_at_max_attempts(self):
        """AuthenticationError is raised exactly at MAX_LOGIN_ATTEMPTS."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = str(MAX_LOGIN_ATTEMPTS)
        mock_redis.ttl.return_value = 900  # 15 minutes remaining

        with patch(REDIS_MODULE, return_value=mock_redis):
            with pytest.raises(AuthenticationError) as exc_info:
                check_account_lockout(EMAIL)

        assert "15 minutes" in str(exc_info.value)
        assert str(MAX_LOGIN_ATTEMPTS) in str(exc_info.value)

    def test_lockout_above_max_attempts(self):
        """AuthenticationError is also raised when attempts exceed the threshold."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = str(MAX_LOGIN_ATTEMPTS + 3)
        mock_redis.ttl.return_value = 1800

        with patch(REDIS_MODULE, return_value=mock_redis):
            with pytest.raises(AuthenticationError):
                check_account_lockout(EMAIL)

    def test_lockout_message_uses_ttl_minutes(self):
        """Remaining minutes in the error message come from Redis TTL."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = str(MAX_LOGIN_ATTEMPTS)
        mock_redis.ttl.return_value = 600  # 10 minutes

        with patch(REDIS_MODULE, return_value=mock_redis):
            with pytest.raises(AuthenticationError) as exc_info:
                check_account_lockout(EMAIL)

        assert "10 minutes" in str(exc_info.value)

    def test_lockout_uses_fallback_minutes_when_ttl_is_none(self):
        """When Redis TTL returns None, fallback to LOCKOUT_SECONDS // 60."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = str(MAX_LOGIN_ATTEMPTS)
        mock_redis.ttl.return_value = None

        with patch(REDIS_MODULE, return_value=mock_redis):
            with pytest.raises(AuthenticationError) as exc_info:
                check_account_lockout(EMAIL)

        expected_minutes = LOCKOUT_SECONDS // 60
        assert str(expected_minutes) in str(exc_info.value)

    def test_no_lockout_when_redis_unavailable(self):
        """When Redis is None (unavailable), account check is silently skipped."""
        with patch(REDIS_MODULE, return_value=None):
            check_account_lockout(EMAIL)  # must not raise

    def test_redis_exception_is_swallowed(self):
        """Unexpected Redis errors are caught and the function returns silently."""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")

        with patch(REDIS_MODULE, return_value=mock_redis):
            check_account_lockout(EMAIL)  # must not raise

    def test_authentication_error_is_not_swallowed(self):
        """AuthenticationError must propagate and not be caught by the generic handler."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = str(MAX_LOGIN_ATTEMPTS)
        mock_redis.ttl.return_value = 60

        with patch(REDIS_MODULE, return_value=mock_redis):
            with pytest.raises(AuthenticationError):
                check_account_lockout(EMAIL)


# ---------------------------------------------------------------------------
# record_failed_login
# ---------------------------------------------------------------------------


class TestRecordFailedLogin:
    def test_increments_counter_on_first_attempt(self):
        """First failed attempt: key is incremented and TTL is set."""
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 1

        with patch(REDIS_MODULE, return_value=mock_redis):
            record_failed_login(EMAIL)

        key = f"login_attempts:{EMAIL}"
        mock_redis.incr.assert_called_once_with(key)
        mock_redis.expire.assert_called_once_with(key, LOCKOUT_SECONDS)

    def test_increments_counter_on_subsequent_attempt(self):
        """Subsequent failed attempts: counter incremented, TTL not reset."""
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 3  # already had 2 previous failures

        with patch(REDIS_MODULE, return_value=mock_redis):
            record_failed_login(EMAIL)

        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_not_called()

    def test_sets_ttl_only_on_first_attempt(self):
        """expire() is called only when incr() returns 1 (first attempt)."""
        mock_redis = MagicMock()

        for count in [2, 3, MAX_LOGIN_ATTEMPTS]:
            mock_redis.reset_mock()
            mock_redis.incr.return_value = count

            with patch(REDIS_MODULE, return_value=mock_redis):
                record_failed_login(EMAIL)

            mock_redis.expire.assert_not_called()

    def test_no_op_when_redis_unavailable(self):
        """When Redis is None, the function returns silently without error."""
        with patch(REDIS_MODULE, return_value=None):
            record_failed_login(EMAIL)  # must not raise

    def test_redis_exception_is_swallowed(self):
        """Redis errors during recording are caught silently."""
        mock_redis = MagicMock()
        mock_redis.incr.side_effect = OSError("network failure")

        with patch(REDIS_MODULE, return_value=mock_redis):
            record_failed_login(EMAIL)  # must not raise


# ---------------------------------------------------------------------------
# clear_login_attempts
# ---------------------------------------------------------------------------


class TestClearLoginAttempts:
    def test_deletes_redis_key_on_success(self):
        """Successful login clears the attempt counter from Redis."""
        mock_redis = MagicMock()

        with patch(REDIS_MODULE, return_value=mock_redis):
            clear_login_attempts(EMAIL)

        mock_redis.delete.assert_called_once_with(f"login_attempts:{EMAIL}")

    def test_no_op_when_redis_unavailable(self):
        """When Redis is None, the function returns silently without error."""
        with patch(REDIS_MODULE, return_value=None):
            clear_login_attempts(EMAIL)  # must not raise

    def test_redis_exception_is_swallowed(self):
        """Redis errors during clearing are caught silently."""
        mock_redis = MagicMock()
        mock_redis.delete.side_effect = RuntimeError("unexpected")

        with patch(REDIS_MODULE, return_value=mock_redis):
            clear_login_attempts(EMAIL)  # must not raise


# ---------------------------------------------------------------------------
# Integration-style: full lockout lifecycle
# ---------------------------------------------------------------------------


class TestLockoutLifecycle:
    def test_lockout_after_max_failed_attempts(self):
        """Simulates the full lifecycle: attempts accumulate then trigger lockout."""
        attempt_store: dict[str, int] = {}
        key = f"login_attempts:{EMAIL}"

        def fake_get(k):
            v = attempt_store.get(k)
            return str(v) if v is not None else None

        def fake_incr(k):
            attempt_store[k] = attempt_store.get(k, 0) + 1
            return attempt_store[k]

        def fake_expire(k, ttl):
            pass  # no-op in this simulation

        def fake_ttl(k):
            return LOCKOUT_SECONDS

        mock_redis = MagicMock()
        mock_redis.get.side_effect = fake_get
        mock_redis.incr.side_effect = fake_incr
        mock_redis.expire.side_effect = fake_expire
        mock_redis.ttl.side_effect = fake_ttl

        with patch(REDIS_MODULE, return_value=mock_redis):
            # No lockout initially
            check_account_lockout(EMAIL)

            # Record MAX_LOGIN_ATTEMPTS failures
            for _ in range(MAX_LOGIN_ATTEMPTS):
                record_failed_login(EMAIL)

            # Should now be locked
            with pytest.raises(AuthenticationError):
                check_account_lockout(EMAIL)

    def test_clear_removes_lockout(self):
        """After clearing, a previously locked account can attempt login again."""
        attempt_store: dict[str, int] = {f"login_attempts:{EMAIL}": MAX_LOGIN_ATTEMPTS}

        def fake_get(k):
            v = attempt_store.get(k)
            return str(v) if v is not None else None

        def fake_delete(k):
            attempt_store.pop(k, None)

        mock_redis = MagicMock()
        mock_redis.get.side_effect = fake_get
        mock_redis.ttl.return_value = LOCKOUT_SECONDS
        mock_redis.delete.side_effect = fake_delete

        with patch(REDIS_MODULE, return_value=mock_redis):
            # Locked
            with pytest.raises(AuthenticationError):
                check_account_lockout(EMAIL)

            # Clear on successful login
            clear_login_attempts(EMAIL)

            # No longer locked
            check_account_lockout(EMAIL)
