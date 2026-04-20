"""Tests unitaires pour app/services/erp_auth_service.py.

Couvre :
- Resolution du tenant et creation du connecteur (_get_connector_for_tenant)
- Dechiffrement des credentials (chiffres vs fallback plaintext)
- Authentification par cookies tenant
- Authentification basic (login/password)
- Authentification via ERP non-Cosium (erp_config)
- Erreurs : tenant inexistant, credentials absents
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models import Tenant
from app.services.erp_auth_service import (
    _authenticate_connector,
    _get_connector_for_tenant,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tenant(db, **kwargs) -> Tenant:
    """Cree et persiste un tenant de test avec des champs personnalises."""
    from app.models import Organization

    org = db.query(Organization).first()
    defaults = dict(
        organization_id=org.id,
        name="Magasin Test Auth",
        slug="magasin-test-auth",
        erp_type="cosium",
        cosium_tenant="my-tenant",
        cosium_login="user@optiflow.fr",
        cosium_password_enc=None,
        cosium_cookie_access_token_enc=None,
        cosium_cookie_device_credential_enc=None,
    )
    defaults.update(kwargs)
    tenant = Tenant(**defaults)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


# ---------------------------------------------------------------------------
# _get_connector_for_tenant
# ---------------------------------------------------------------------------


class TestGetConnectorForTenant:
    def test_tenant_not_found_raises(self, db):
        with pytest.raises(ValueError, match="Tenant 99999 introuvable"):
            _get_connector_for_tenant(db, 99999)

    def test_returns_connector_and_tenant(self, db):
        tenant = _make_tenant(db, slug="connector-ok")
        with patch("app.services.erp_auth_service.get_connector") as mock_get:
            mock_connector = MagicMock()
            mock_get.return_value = mock_connector

            connector, returned_tenant = _get_connector_for_tenant(db, tenant.id)

        mock_get.assert_called_once_with("cosium")
        assert connector is mock_connector
        assert returned_tenant.id == tenant.id

    def test_defaults_erp_type_to_cosium_when_null(self, db):
        """Si erp_type est None sur le tenant, le factory recoit 'cosium'."""
        tenant = _make_tenant(db, slug="erp-type-null", erp_type=None)

        with patch("app.services.erp_auth_service.get_connector") as mock_get:
            mock_get.return_value = MagicMock()
            _get_connector_for_tenant(db, tenant.id)

        mock_get.assert_called_once_with("cosium")


# ---------------------------------------------------------------------------
# _authenticate_connector — auth basic (login / password)
# ---------------------------------------------------------------------------


class TestAuthenticateConnectorBasic:
    """Tests de l'authentification basic Cosium (login + mot de passe chiffre)."""

    def _cosium_connector(self):
        """Cree un mock de CosiumConnector avec erp_type == 'cosium'."""
        connector = MagicMock()
        connector.erp_type = "cosium"
        # Simule isinstance(connector, CosiumConnector) -> False par defaut
        # -> le code passe en basic auth
        return connector

    def test_basic_auth_with_encrypted_password(self, db):
        """Le mot de passe chiffre est dechiffre avant d'appeler connector.authenticate."""
        from app.core.encryption import encrypt

        encrypted_pw = encrypt("secret123")
        tenant = _make_tenant(
            db,
            slug="basic-auth-enc",
            cosium_tenant="t1",
            cosium_login="user@test.fr",
            cosium_password_enc=encrypted_pw,
        )
        connector = self._cosium_connector()

        with (
            patch("app.services.erp_auth_service.settings") as mock_settings,
        ):
            mock_settings.cosium_base_url = "https://c1.cosium.biz"
            mock_settings.cosium_tenant = ""
            mock_settings.cosium_login = ""
            mock_settings.cosium_password = ""

            _authenticate_connector(connector, tenant)

        connector.authenticate.assert_called_once_with(
            "https://c1.cosium.biz", "t1", "user@test.fr", "secret123"
        )

    def test_basic_auth_plaintext_fallback(self, db):
        """Si decrypt echoue (mot de passe non chiffre), le plaintext est utilise."""
        tenant = _make_tenant(
            db,
            slug="basic-auth-plain",
            cosium_tenant="t2",
            cosium_login="user2@test.fr",
            cosium_password_enc="plaintext-password",
        )
        connector = self._cosium_connector()

        with (
            patch("app.services.erp_auth_service.settings") as mock_settings,
            patch("app.services.erp_auth_service.decrypt", side_effect=Exception("bad token")),
        ):
            mock_settings.cosium_base_url = "https://c1.cosium.biz"
            mock_settings.cosium_tenant = ""
            mock_settings.cosium_login = ""
            mock_settings.cosium_password = ""

            _authenticate_connector(connector, tenant)

        connector.authenticate.assert_called_once_with(
            "https://c1.cosium.biz", "t2", "user2@test.fr", "plaintext-password"
        )

    def test_falls_back_to_settings_when_tenant_has_no_credentials(self, db):
        """Les settings globaux sont utilises si le tenant n'a pas de credentials locaux."""
        tenant = _make_tenant(
            db,
            slug="basic-auth-settings",
            cosium_tenant=None,
            cosium_login=None,
            cosium_password_enc=None,
        )
        connector = self._cosium_connector()

        with (
            patch("app.services.erp_auth_service.settings") as mock_settings,
            patch("app.services.erp_auth_service.decrypt", return_value="pw-from-settings"),
        ):
            mock_settings.cosium_base_url = "https://c1.cosium.biz"
            mock_settings.cosium_tenant = "global-tenant"
            mock_settings.cosium_login = "global-login"
            mock_settings.cosium_password = "enc-global-pw"

            _authenticate_connector(connector, tenant)

        connector.authenticate.assert_called_once_with(
            "https://c1.cosium.biz", "global-tenant", "global-login", "pw-from-settings"
        )

    def test_raises_when_no_credentials_at_all(self, db):
        """ValueError levee si aucun credential n'est disponible."""
        tenant = _make_tenant(
            db,
            slug="no-creds",
            cosium_tenant=None,
            cosium_login=None,
            cosium_password_enc=None,
        )
        connector = self._cosium_connector()

        with (
            patch("app.services.erp_auth_service.settings") as mock_settings,
        ):
            mock_settings.cosium_base_url = "https://c1.cosium.biz"
            mock_settings.cosium_tenant = ""
            mock_settings.cosium_login = ""
            mock_settings.cosium_password = ""

            with pytest.raises(ValueError, match="Credentials ERP"):
                _authenticate_connector(connector, tenant)

        connector.authenticate.assert_not_called()


# ---------------------------------------------------------------------------
# _authenticate_connector — cookie-based auth
# ---------------------------------------------------------------------------


class TestAuthenticateConnectorCookies:
    """Tests de l'authentification par cookies (chemin prioritaire Cosium)."""

    def test_cookie_auth_decrypts_and_calls_authenticate_cookie(self, db):
        """Quand les cookies sont presents, _authenticate_cookie est appele."""
        from app.core.encryption import encrypt
        from app.integrations.cosium.cosium_connector import CosiumConnector

        at_enc = encrypt("access-token-value")
        dc_enc = encrypt("device-cred-value")

        tenant = _make_tenant(
            db,
            slug="cookie-auth-ok",
            cosium_tenant="cookie-tenant",
            cosium_cookie_access_token_enc=at_enc,
            cosium_cookie_device_credential_enc=dc_enc,
        )

        # Cree un vrai CosiumConnector-like mock qui passe isinstance()
        mock_client = MagicMock()
        connector = MagicMock(spec=CosiumConnector)
        connector.erp_type = "cosium"
        connector._client = mock_client

        with patch("app.services.erp_auth_service.settings") as mock_settings:
            mock_settings.cosium_base_url = "https://c1.cosium.biz"
            mock_settings.cosium_tenant = "fallback-tenant"

            _authenticate_connector(connector, tenant)

        mock_client._authenticate_cookie.assert_called_once_with(
            access_token="access-token-value",
            device_credential="device-cred-value",
        )
        assert mock_client.base_url == "https://c1.cosium.biz"
        assert mock_client.tenant == "cookie-tenant"
        # authenticate() basic ne doit PAS etre appele
        connector.authenticate.assert_not_called()

    def test_cookie_auth_falls_back_to_basic_on_decrypt_error(self, db):
        """Si le dechiffrement des cookies echoue, on continue avec l'auth basic."""
        from app.integrations.cosium.cosium_connector import CosiumConnector

        tenant = _make_tenant(
            db,
            slug="cookie-fallback",
            cosium_tenant="t-fallback",
            cosium_login="user@fb.fr",
            cosium_password_enc=None,
            cosium_cookie_access_token_enc="bad-token",
            cosium_cookie_device_credential_enc="bad-device",
        )

        connector = MagicMock(spec=CosiumConnector)
        connector.erp_type = "cosium"

        with (
            patch("app.services.erp_auth_service.settings") as mock_settings,
            patch("app.services.erp_auth_service.decrypt", side_effect=ValueError("decrypt failed")),
        ):
            mock_settings.cosium_base_url = "https://c1.cosium.biz"
            mock_settings.cosium_tenant = ""
            mock_settings.cosium_login = ""
            mock_settings.cosium_password = "fallback-pw"

            # decrypt echoue -> credentials manquants -> ValueError
            with pytest.raises(ValueError, match="Credentials ERP"):
                _authenticate_connector(connector, tenant)

    def test_cookie_auth_uses_settings_tenant_when_tenant_field_null(self, db):
        """Le champ cosium_tenant du tenant peut etre None; settings.cosium_tenant est utilise."""
        from app.core.encryption import encrypt
        from app.integrations.cosium.cosium_connector import CosiumConnector

        at_enc = encrypt("at")
        dc_enc = encrypt("dc")

        tenant = _make_tenant(
            db,
            slug="cookie-no-tenant",
            cosium_tenant=None,
            cosium_cookie_access_token_enc=at_enc,
            cosium_cookie_device_credential_enc=dc_enc,
        )

        mock_client = MagicMock()
        connector = MagicMock(spec=CosiumConnector)
        connector.erp_type = "cosium"
        connector._client = mock_client

        with patch("app.services.erp_auth_service.settings") as mock_settings:
            mock_settings.cosium_base_url = "https://c1.cosium.biz"
            mock_settings.cosium_tenant = "settings-tenant"

            _authenticate_connector(connector, tenant)

        assert mock_client.tenant == "settings-tenant"


# ---------------------------------------------------------------------------
# _authenticate_connector — ERP non-Cosium (erp_config)
# ---------------------------------------------------------------------------


class TestAuthenticateConnectorNonCosium:
    """Tests de l'authentification pour un ERP autre que Cosium."""

    def test_non_cosium_uses_erp_config(self, db):
        """Les credentials viennent de erp_config pour les ERP non-Cosium."""
        tenant = _make_tenant(
            db,
            slug="non-cosium-erp",
            erp_type="icanopee",
            erp_config={
                "base_url": "https://icanopee.example.com",
                "tenant": "opt123",
                "login": "admin",
                "password": "secret",
            },
        )
        connector = MagicMock()
        connector.erp_type = "icanopee"

        _authenticate_connector(connector, tenant)

        connector.authenticate.assert_called_once_with(
            "https://icanopee.example.com", "opt123", "admin", "secret"
        )

    def test_non_cosium_missing_config_raises(self, db):
        """ValueError si erp_config est vide pour un ERP non-Cosium."""
        tenant = _make_tenant(
            db,
            slug="non-cosium-no-cfg",
            erp_type="icanopee",
            erp_config={},
        )
        connector = MagicMock()
        connector.erp_type = "icanopee"

        with pytest.raises(ValueError, match="Credentials ERP"):
            _authenticate_connector(connector, tenant)

        connector.authenticate.assert_not_called()

    def test_non_cosium_null_erp_config_raises(self, db):
        """ValueError si erp_config est None pour un ERP non-Cosium."""
        tenant = _make_tenant(
            db,
            slug="non-cosium-null-cfg",
            erp_type="icanopee",
            erp_config=None,
        )
        connector = MagicMock()
        connector.erp_type = "icanopee"

        with pytest.raises(ValueError, match="Credentials ERP"):
            _authenticate_connector(connector, tenant)
