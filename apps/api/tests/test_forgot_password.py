import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.models import PasswordResetToken


class TestForgotPassword:
    """Tests for POST /api/v1/auth/forgot-password."""

    def test_forgot_password_existing_email_returns_204(self, client, seed_user):
        with patch("app.integrations.email_sender.email_sender") as mock_email:
            mock_email.send_email.return_value = True
            resp = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@optiflow.com"},
            )
        assert resp.status_code == 204

    def test_forgot_password_unknown_email_returns_204(self, client):
        """Security: unknown email must return same 204 — no information leak."""
        resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "unknown@example.com"},
        )
        assert resp.status_code == 204

    def test_forgot_password_creates_token_in_db(self, client, db, seed_user):
        with patch("app.integrations.email_sender.email_sender") as mock_email:
            mock_email.send_email.return_value = True
            client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@optiflow.com"},
            )
        tokens = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == seed_user.id,
        ).all()
        assert len(tokens) == 1
        assert tokens[0].used is False

    def test_forgot_password_sends_email(self, client, seed_user):
        with patch("app.tasks.email_tasks.send_email_async") as mock_task:
            client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@optiflow.com"},
            )
            mock_task.delay.assert_called_once()
            kwargs = mock_task.delay.call_args[1]
            assert kwargs["to"] == "test@optiflow.com"
            assert "reinitialisation" in kwargs["subject"].lower()


class TestResetPassword:
    """Tests for POST /api/v1/auth/reset-password."""

    def _create_valid_token(self, db, user_id: int) -> str:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
        reset = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset)
        db.commit()
        return raw_token

    def test_reset_password_valid_token(self, client, db, seed_user):
        raw_token = self._create_valid_token(db, seed_user.id)
        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass123!"},
        )
        assert resp.status_code == 204

        # Verify token is marked as used
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        reset = db.query(PasswordResetToken).filter(
            PasswordResetToken.token_hash == token_hash,
        ).first()
        assert reset is not None
        assert reset.used is True

    def test_reset_password_can_login_with_new_password(self, client, db, seed_user):
        raw_token = self._create_valid_token(db, seed_user.id)
        client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass123!"},
        )
        # Login with new password
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@optiflow.com", "password": "NewPass123!"},
        )
        assert resp.status_code == 200

    def test_reset_password_invalid_token(self, client):
        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalid-token-value", "new_password": "NewPass123!"},
        )
        assert resp.status_code == 401

    def test_reset_password_expired_token(self, client, db, seed_user):
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
        reset = PasswordResetToken(
            user_id=seed_user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset)
        db.commit()

        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass123!"},
        )
        assert resp.status_code == 401

    def test_reset_password_already_used_token(self, client, db, seed_user):
        raw_token = self._create_valid_token(db, seed_user.id)
        # Use it once
        resp1 = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPass123!"},
        )
        assert resp1.status_code == 204

        # Try to use it again
        resp2 = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "AnotherPass1!"},
        )
        assert resp2.status_code == 401

    def test_reset_password_weak_password_rejected(self, client, db, seed_user):
        raw_token = self._create_valid_token(db, seed_user.id)
        resp = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": "weak"},
        )
        assert resp.status_code == 422
