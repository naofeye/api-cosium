"""Unit tests for auth_service — direct service function calls."""

from unittest.mock import patch

import pytest

from app.core.exceptions import AuthenticationError
from app.domain.schemas.auth import LoginRequest
from app.models import PasswordResetToken
from app.security import verify_password
from app.services import auth_service


class TestAuthenticate:
    def test_authenticate_valid_credentials(self, db, seed_user):
        payload = LoginRequest(email="test@optiflow.local", password="test123")
        result = auth_service.authenticate(db, payload)

        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.role == "admin"
        assert result.tenant_id is not None
        assert result.tenant_name == "Test Magasin"

    def test_authenticate_wrong_password_raises(self, db, seed_user):
        payload = LoginRequest(email="test@optiflow.local", password="wrongpassword")
        with pytest.raises(AuthenticationError):
            auth_service.authenticate(db, payload)

    def test_authenticate_nonexistent_email_raises(self, db, seed_user):
        payload = LoginRequest(email="nobody@optiflow.local", password="test123")
        with pytest.raises(AuthenticationError):
            auth_service.authenticate(db, payload)


class TestChangePassword:
    def test_change_password_success(self, db, seed_user):
        auth_service.change_password(db, seed_user.id, "test123", "NewPass1")

        # Verify new password works
        db.refresh(seed_user)
        assert verify_password("NewPass1", seed_user.password_hash)

    def test_change_password_wrong_old_raises(self, db, seed_user):
        with pytest.raises(AuthenticationError):
            auth_service.change_password(db, seed_user.id, "wrongold", "NewPass1")


class TestRequestPasswordReset:
    @patch("app.tasks.email_tasks.send_email_async")
    @patch("app.integrations.email_templates.render_email", return_value="<html>reset</html>")
    def test_existing_email_creates_token(self, mock_render, mock_send, db, seed_user):
        auth_service.request_password_reset(db, "test@optiflow.local")

        token = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == seed_user.id
        ).first()
        assert token is not None
        assert token.used is False

    def test_unknown_email_no_error(self, db, seed_user):
        # Should NOT raise — silent for security
        auth_service.request_password_reset(db, "unknown@example.com")
        # No PasswordResetToken created for unknown user
        count = db.query(PasswordResetToken).count()
        assert count == 0
