"""
Tests de regression securite — invariants qui ne doivent JAMAIS etre casses.

Couvre :
- Rejet des secrets par defaut en production (config)
- Chiffrement refuse le fallback en production
- JWT contient iss/aud et rejette les tokens invalides
- CosiumConnector est lecture seule (pas de put/post/delete/patch)
- Validation de force des mots de passe
"""

import inspect
from unittest.mock import patch

import jwt
import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.config import Settings, _DEV_JWT_SECRET, _DEV_S3_KEY
from app.domain.schemas.auth import (
    ChangePasswordRequest,
    PasswordMixin,
    ResetPasswordRequest,
)
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.security import create_access_token, decode_access_token


# ---------------------------------------------------------------------------
# 1. Config rejects default secrets in production
# ---------------------------------------------------------------------------


class TestConfigProductionSecrets:
    """Settings.model_validator doit refuser les valeurs par defaut en prod."""

    def test_config_rejects_default_secrets_in_production(self) -> None:
        """jwt_secret par defaut = interdit en production."""
        with pytest.raises(ValueError, match="JWT_SECRET"):
            Settings(
                app_env="production",
                jwt_secret=_DEV_JWT_SECRET,
                s3_access_key="real-key",
                s3_secret_key="real-secret",
                encryption_key="dGVzdC1rZXktMzItYnl0ZXMtbG9uZy1lbm91Z2g=",
                database_url="postgresql+psycopg://prod:secret@db:5432/prod",
            )

    def test_config_rejects_default_minio_creds_in_production(self) -> None:
        """MinIO credentials par defaut (minioadmin) = interdit en production."""
        with pytest.raises(ValueError, match="S3_ACCESS_KEY"):
            Settings(
                app_env="production",
                jwt_secret="super-secure-production-secret-key-2026",
                s3_access_key=_DEV_S3_KEY,
                s3_secret_key=_DEV_S3_KEY,
                encryption_key="dGVzdC1rZXktMzItYnl0ZXMtbG9uZy1lbm91Z2g=",
                database_url="postgresql+psycopg://prod:secret@db:5432/prod",
            )

    def test_config_rejects_missing_encryption_key_in_production(self) -> None:
        """encryption_key vide = interdit en production."""
        with pytest.raises(ValueError, match="ENCRYPTION_KEY"):
            Settings(
                app_env="production",
                jwt_secret="super-secure-production-secret-key-2026",
                s3_access_key="real-key",
                s3_secret_key="real-secret",
                encryption_key="",
                database_url="postgresql+psycopg://prod:secret@db:5432/prod",
            )

    def test_config_accepts_defaults_in_local(self) -> None:
        """En environnement local, les valeurs par defaut sont acceptees (pas de ValueError)."""
        # Settings() en mode local ne doit PAS lever de ValueError,
        # meme avec les valeurs par defaut. On verifie juste que ca ne plante pas.
        cfg = Settings(app_env="local")
        assert cfg.app_env == "local"


# ---------------------------------------------------------------------------
# 5. Encryption refuses fallback in production
# ---------------------------------------------------------------------------


class TestEncryptionProduction:
    def test_encryption_refuses_fallback_in_production(self) -> None:
        """get_fernet() doit lever RuntimeError en prod sans encryption_key."""
        with patch("app.core.encryption.settings") as mock_settings:
            mock_settings.app_env = "production"
            mock_settings.encryption_key = ""

            from app.core.encryption import get_fernet

            with pytest.raises(RuntimeError, match="ENCRYPTION_KEY est obligatoire"):
                get_fernet()


# ---------------------------------------------------------------------------
# 6-7. JWT iss/aud
# ---------------------------------------------------------------------------


class TestJWTClaims:
    def test_jwt_includes_iss_and_aud(self) -> None:
        """Le token JWT doit contenir iss=optiflow et aud=optiflow-api."""
        token = create_access_token(subject="test@example.com", role="admin")
        # Decode sans verification pour inspecter les claims bruts
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["iss"] == "optiflow"
        assert payload["aud"] == "optiflow-api"

    def test_jwt_rejects_wrong_issuer(self) -> None:
        """Un token avec un mauvais issuer doit etre rejete."""
        from app.core.config import settings

        payload = {
            "sub": "test@example.com",
            "role": "admin",
            "iss": "malicious-issuer",
            "aud": "optiflow-api",
        }
        bad_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        with pytest.raises(jwt.InvalidIssuerError):
            decode_access_token(bad_token)

    def test_jwt_rejects_wrong_audience(self) -> None:
        """Un token avec un mauvais audience doit etre rejete."""
        from app.core.config import settings

        payload = {
            "sub": "test@example.com",
            "role": "admin",
            "iss": "optiflow",
            "aud": "wrong-audience",
        }
        bad_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        with pytest.raises(jwt.InvalidAudienceError):
            decode_access_token(bad_token)


# ---------------------------------------------------------------------------
# 8. CosiumConnector read-only
# ---------------------------------------------------------------------------


class TestCosiumReadOnly:
    def test_cosium_connector_has_no_write_methods(self) -> None:
        """CosiumConnector ne doit avoir aucune methode put/post/delete/patch.

        Seule exception : authenticate() qui fait un POST /authenticate/basic.
        """
        forbidden_prefixes = ("put", "delete", "patch")
        # 'post' is forbidden except 'authenticate' uses POST internally
        members = inspect.getmembers(CosiumConnector, predicate=inspect.isfunction)
        public_methods = [name for name, _ in members if not name.startswith("_")]

        for method_name in public_methods:
            for prefix in forbidden_prefixes:
                assert not method_name.lower().startswith(prefix), (
                    f"CosiumConnector a une methode interdite : {method_name} "
                    f"(commence par '{prefix}'). Cosium est LECTURE SEULE."
                )

        # Verify no generic 'post' method exists (authenticate is the only POST)
        assert "post" not in public_methods, (
            "CosiumConnector ne doit pas avoir de methode 'post' generique. "
            "Seul authenticate() est autorise a faire un POST."
        )

    def test_cosium_connector_only_reads(self) -> None:
        """Toutes les methodes publiques (hors authenticate) doivent etre des lectures (get_*)."""
        members = inspect.getmembers(CosiumConnector, predicate=inspect.isfunction)
        public_methods = [name for name, _ in members if not name.startswith("_")]

        # get_*, list_*, search_* sont tous des verbes de LECTURE (HTTP GET).
        # authenticate fait POST /authenticate/basic (seul POST autorise par charte).
        # Toute methode put/post/delete/patch/create/update/save/etc serait BLOQUEE.
        READ_PREFIXES = ("get_", "list_", "search_")
        ALLOWED_NAMES = {"authenticate", "erp_type", "is_authenticated"}
        for method_name in public_methods:
            assert method_name.startswith(READ_PREFIXES) or method_name in ALLOWED_NAMES, (
                f"Methode inattendue sur CosiumConnector : {method_name}. "
                "Seules les methodes get_*/list_*/search_* (lectures) et authenticate sont autorisees."
            )


# ---------------------------------------------------------------------------
# 9-10. Password validation
# ---------------------------------------------------------------------------


class TestPasswordValidation:
    def test_password_minimum_length(self) -> None:
        """Un mot de passe de moins de 10 caracteres doit etre rejete."""
        with pytest.raises(ValueError, match="au moins 10 caracteres"):
            PasswordMixin.validate_password_strength("Ab1!short")

    def test_password_requires_special_char(self) -> None:
        """Un mot de passe sans caractere special doit etre rejete."""
        with pytest.raises(ValueError, match="caractere special"):
            PasswordMixin.validate_password_strength("Abcdefgh12")

    def test_password_requires_uppercase(self) -> None:
        """Un mot de passe sans majuscule doit etre rejete."""
        with pytest.raises(ValueError, match="majuscule"):
            PasswordMixin.validate_password_strength("abcdefgh1!")

    def test_password_requires_lowercase(self) -> None:
        """Un mot de passe sans minuscule doit etre rejete."""
        with pytest.raises(ValueError, match="minuscule"):
            PasswordMixin.validate_password_strength("ABCDEFGH1!")

    def test_password_requires_digit(self) -> None:
        """Un mot de passe sans chiffre doit etre rejete."""
        with pytest.raises(ValueError, match="chiffre"):
            PasswordMixin.validate_password_strength("Abcdefghi!")

    def test_valid_password_accepted(self) -> None:
        """Un mot de passe conforme doit etre accepte."""
        result = PasswordMixin.validate_password_strength("Abcdefgh1!")
        assert result == "Abcdefgh1!"

    def test_reset_password_schema_rejects_weak(self) -> None:
        """Le schema ResetPasswordRequest refuse un mot de passe faible."""
        with pytest.raises(PydanticValidationError):
            ResetPasswordRequest(token="valid-token", new_password="weak")

    def test_change_password_schema_rejects_weak(self) -> None:
        """Le schema ChangePasswordRequest refuse un mot de passe faible."""
        with pytest.raises(PydanticValidationError):
            ChangePasswordRequest(old_password="anything", new_password="short")
