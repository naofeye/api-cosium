"""
Tests unitaires pour onboarding_service et erp_auth_service.

Scope : logique metier pure (service layer), sans appels HTTP.
Les connecteurs Cosium et les couches infra sont systematiquement mockees.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core.encryption import encrypt
from app.core.exceptions import BusinessError, ValidationError
from app.domain.schemas.onboarding import ConnectCosiumRequest, SignupRequest
from app.models import Tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signup_payload(**overrides) -> SignupRequest:
    defaults = {
        "company_name": "Optique Dupont",
        "owner_email": "owner@dupont.fr",
        "owner_password": "Secret12345!",
        "owner_first_name": "Jean",
        "owner_last_name": "Dupont",
    }
    defaults.update(overrides)
    return SignupRequest(**defaults)


def _make_connect_payload(**overrides) -> ConnectCosiumRequest:
    defaults = {
        "cosium_tenant": "dupont",
        "cosium_login": "jean.dupont",
        "cosium_password": "ERP_pass1!",
    }
    defaults.update(overrides)
    return ConnectCosiumRequest(**defaults)


# ---------------------------------------------------------------------------
# onboarding_service — signup
# ---------------------------------------------------------------------------

class TestSignup:
    def test_signup_creates_org_tenant_user_and_returns_tokens(self, db):
        """Signup valide : organisation, tenant et utilisateur crees, tokens retournes."""
        from app.services import onboarding_service

        payload = _make_signup_payload()
        result = onboarding_service.signup(db, payload)

        assert result.access_token
        assert result.refresh_token
        assert result.role == "admin"
        assert result.tenant_id is not None
        assert result.tenant_name == "Optique Dupont"
        assert len(result.available_tenants) == 1
        assert result.available_tenants[0]["role"] == "admin"

    def test_signup_duplicate_email_raises_validation_error(self, db):
        """Un deuxieme signup avec le meme email doit lever ValidationError."""
        from app.services import onboarding_service

        payload = _make_signup_payload(owner_email="dup@example.fr")
        onboarding_service.signup(db, payload)

        with pytest.raises(ValidationError) as exc_info:
            onboarding_service.signup(db, _make_signup_payload(
                owner_email="dup@example.fr",
                company_name="Autre Magasin",
            ))
        assert "owner_email" in str(exc_info.value)

    def test_signup_slugifies_company_name(self, db):
        """Le slug organisation est derive du nom de l'entreprise."""
        from app.models import Organization
        from app.services import onboarding_service

        onboarding_service.signup(db, _make_signup_payload(
            company_name="L'Optique & Co.",
            owner_email="slug@test.fr",
        ))

        org = db.query(Organization).filter(Organization.slug == "l-optique-co").first()
        assert org is not None

    def test_signup_handles_slug_collision(self, db):
        """Un second signup avec un nom identique obtient un slug suffixe."""
        from app.models import Tenant
        from app.services import onboarding_service

        onboarding_service.signup(db, _make_signup_payload(
            company_name="Collision",
            owner_email="first@collision.fr",
        ))
        onboarding_service.signup(db, _make_signup_payload(
            company_name="Collision",
            owner_email="second@collision.fr",
        ))

        slugs = [t.slug for t in db.query(Tenant).all()]
        # Les deux slugs doivent etre distincts
        assert len(set(s for s in slugs if "collision" in s)) >= 2


# ---------------------------------------------------------------------------
# onboarding_service — connect_cosium
# ---------------------------------------------------------------------------

class TestConnectCosium:
    @patch("app.integrations.erp_factory.get_connector")
    def test_connect_cosium_success_stores_encrypted_credentials(self, mock_get_connector, db, default_tenant):
        """Connexion ERP reussie : credentials chiffrees stockees, flag mis a True."""
        from app.services import onboarding_service

        mock_connector = MagicMock()
        mock_connector.authenticate.return_value = "fake-erp-token"
        mock_get_connector.return_value = mock_connector

        payload = _make_connect_payload(
            cosium_tenant="mysite",
            cosium_login="user1",
            cosium_password="SuperPass1!",
        )

        result = onboarding_service.connect_cosium(db, default_tenant.id, payload)

        assert result is True
        db.refresh(default_tenant)
        assert default_tenant.cosium_connected is True
        assert default_tenant.cosium_tenant == "mysite"
        assert default_tenant.cosium_login == "user1"
        # Le mot de passe doit etre chiffre (pas en clair)
        assert default_tenant.cosium_password_enc != "SuperPass1!"
        assert default_tenant.cosium_password_enc  # non nul

    @patch("app.integrations.erp_factory.get_connector")
    def test_connect_cosium_auth_failure_raises_business_error(self, mock_get_connector, db, default_tenant):
        """Si le connecteur ERP leve une exception, BusinessError est retournee (pas 500)."""
        from app.services import onboarding_service

        mock_connector = MagicMock()
        mock_connector.authenticate.side_effect = ConnectionError("refused")
        mock_get_connector.return_value = mock_connector

        with pytest.raises(BusinessError) as exc_info:
            onboarding_service.connect_cosium(db, default_tenant.id, _make_connect_payload())

        assert "ERP" in str(exc_info.value) or "identifiants" in str(exc_info.value).lower()

    @patch("app.integrations.erp_factory.get_connector")
    def test_connect_cosium_tenant_not_found_raises_business_error(self, mock_get_connector, db):
        """connect_cosium avec un tenant_id inexistant leve BusinessError."""
        from app.services import onboarding_service

        mock_get_connector.return_value = MagicMock()

        with pytest.raises(BusinessError):
            onboarding_service.connect_cosium(db, tenant_id=999999, payload=_make_connect_payload())

    @patch("app.integrations.erp_factory.get_connector")
    def test_connect_cosium_flag_not_set_on_auth_failure(self, mock_get_connector, db, default_tenant):
        """Si l'authentification echoue, cosium_connected ne doit pas passer a True."""
        from app.services import onboarding_service

        mock_connector = MagicMock()
        mock_connector.authenticate.side_effect = Exception("timeout")
        mock_get_connector.return_value = mock_connector

        with pytest.raises(BusinessError):
            onboarding_service.connect_cosium(db, default_tenant.id, _make_connect_payload())

        db.refresh(default_tenant)
        assert not default_tenant.cosium_connected

    @patch("app.integrations.erp_factory.get_connector")
    def test_connect_cosium_authenticate_called_with_correct_args(self, mock_get_connector, db, default_tenant):
        """Le connecteur est bien appele avec les credentials transmises."""
        from app.core.config import settings
        from app.services import onboarding_service

        mock_connector = MagicMock()
        mock_get_connector.return_value = mock_connector

        payload = _make_connect_payload(
            cosium_tenant="tenant-x",
            cosium_login="login-x",
            cosium_password="Pass12345!",
        )
        onboarding_service.connect_cosium(db, default_tenant.id, payload)

        mock_connector.authenticate.assert_called_once_with(
            base_url=settings.cosium_base_url,
            tenant="tenant-x",
            login="login-x",
            password="Pass12345!",
        )


# ---------------------------------------------------------------------------
# onboarding_service — get_onboarding_status
# ---------------------------------------------------------------------------

class TestGetOnboardingStatus:
    def test_status_fresh_tenant_current_step_is_cosium(self, db, default_tenant):
        """Apres signup sans ERP connecte, l'etape courante est 'cosium'."""
        from app.services import onboarding_service

        status = onboarding_service.get_onboarding_status(db, default_tenant.id)

        assert status.current_step == "cosium"
        assert status.cosium_connected is False
        assert status.first_sync_done is False

    def test_status_after_erp_connected_current_step_is_sync(self, db, default_tenant):
        """Apres connexion ERP, l'etape courante passe a 'sync'."""
        from app.services import onboarding_service

        default_tenant.cosium_connected = True
        db.commit()

        status = onboarding_service.get_onboarding_status(db, default_tenant.id)

        assert status.current_step == "sync"
        assert status.cosium_connected is True

    def test_status_unknown_tenant_raises_business_error(self, db):
        """get_onboarding_status avec tenant inconnu leve BusinessError."""
        from app.services import onboarding_service

        with pytest.raises(BusinessError):
            onboarding_service.get_onboarding_status(db, tenant_id=999999)

    def test_status_trial_days_remaining_is_positive(self, db):
        """trial_days_remaining doit etre >= 0 pour un nouveau compte."""
        from app.services import onboarding_service

        result = onboarding_service.signup(db, _make_signup_payload(
            owner_email="trial@test.fr",
            company_name="Trial Optique",
        ))
        status = onboarding_service.get_onboarding_status(db, result.tenant_id)

        assert status.trial_days_remaining is not None
        assert status.trial_days_remaining >= 13  # 14 jours - marge d'1 jour


# ---------------------------------------------------------------------------
# erp_auth_service — _authenticate_connector
# ---------------------------------------------------------------------------

class TestAuthenticateConnector:
    def _make_tenant_with_credentials(self, db, default_tenant, *, encrypted: bool = True) -> Tenant:
        """Retourne le default_tenant enrichi avec des credentials de test."""
        password = "ERPpassword1!"
        default_tenant.cosium_tenant = "site-test"
        default_tenant.cosium_login = "jean.opticien"
        if encrypted:
            default_tenant.cosium_password_enc = encrypt(password)
        else:
            # Simule un mot de passe stocke en clair (migration legacy)
            default_tenant.cosium_password_enc = password
        db.commit()
        return default_tenant

    def test_credential_decryption_calls_connector_with_plaintext(self, db, default_tenant):
        """Les credentials chiffreees sont dechiffrees avant d'etre passees au connecteur."""
        from app.services.erp_auth_service import _authenticate_connector

        self._make_tenant_with_credentials(db, default_tenant, encrypted=True)

        mock_connector = MagicMock()
        mock_connector.erp_type = "cosium"

        _authenticate_connector(mock_connector, default_tenant)

        mock_connector.authenticate.assert_called_once()
        call_args = mock_connector.authenticate.call_args
        # connector.authenticate(base_url, erp_tenant, login, password) — positional
        positional = call_args[0]
        keyword = call_args[1]
        password_passed = positional[3] if len(positional) > 3 else keyword.get("password", "")
        assert password_passed == "ERPpassword1!"

    def test_fallback_for_non_encrypted_password(self, db, default_tenant):
        """Si le dechiffrement echoue (mot de passe non chiffre), le mot de passe brut est utilise."""
        from app.services.erp_auth_service import _authenticate_connector

        # Stocke un mot de passe en clair (legacy — pas un ciphertext Fernet valide)
        self._make_tenant_with_credentials(db, default_tenant, encrypted=False)

        mock_connector = MagicMock()
        mock_connector.erp_type = "cosium"

        # Ne doit pas lever d'exception meme si decrypt() echoue
        _authenticate_connector(mock_connector, default_tenant)

        mock_connector.authenticate.assert_called_once()

    def test_missing_credentials_raises_value_error(self, db, default_tenant):
        """Un tenant sans credentials ERP configurees leve ValueError."""
        from app.services.erp_auth_service import _authenticate_connector

        default_tenant.cosium_tenant = ""
        default_tenant.cosium_login = ""
        default_tenant.cosium_password_enc = ""
        db.commit()

        mock_connector = MagicMock()
        mock_connector.erp_type = "cosium"

        with pytest.raises(ValueError, match="non configurees"):
            _authenticate_connector(mock_connector, default_tenant)

    def test_cookie_auth_takes_priority_over_basic_auth(self, db, default_tenant):
        """Les cookies tenant ont la priorite sur les credentials basic auth."""
        from app.integrations.cosium.cosium_connector import CosiumConnector
        from app.services.erp_auth_service import _authenticate_connector

        at_enc = encrypt("access-token-value")
        dc_enc = encrypt("device-credential-value")
        default_tenant.cosium_cookie_access_token_enc = at_enc
        default_tenant.cosium_cookie_device_credential_enc = dc_enc
        default_tenant.cosium_tenant = "site-test"
        db.commit()

        mock_client = MagicMock()
        mock_connector = MagicMock(spec=CosiumConnector)
        mock_connector.erp_type = "cosium"
        mock_connector._client = mock_client

        _authenticate_connector(mock_connector, default_tenant)

        # Le cookie auth doit avoir ete appele, pas le basic auth
        mock_client._authenticate_cookie.assert_called_once_with(
            access_token="access-token-value",
            device_credential="device-credential-value",
        )
        mock_connector.authenticate.assert_not_called()


# ---------------------------------------------------------------------------
# erp_auth_service — _get_connector_for_tenant
# ---------------------------------------------------------------------------

class TestGetConnectorForTenant:
    def test_returns_connector_and_tenant(self, db, default_tenant):
        """Retourne un tuple (connector, tenant) pour un tenant existant."""
        from app.services.erp_auth_service import _get_connector_for_tenant

        with patch("app.services.erp_auth_service.get_connector") as mock_gc:
            mock_gc.return_value = MagicMock()
            connector, tenant = _get_connector_for_tenant(db, default_tenant.id)

        assert connector is not None
        assert tenant.id == default_tenant.id

    def test_unknown_tenant_raises_value_error(self, db):
        """Un tenant_id inexistant leve ValueError."""
        from app.services.erp_auth_service import _get_connector_for_tenant

        with pytest.raises(ValueError, match="introuvable"):
            _get_connector_for_tenant(db, tenant_id=999999)

    def test_uses_cosium_erp_type_by_default(self, db, default_tenant):
        """Sans erp_type configure, 'cosium' est utilise par defaut."""
        from app.services.erp_auth_service import _get_connector_for_tenant

        default_tenant.erp_type = None
        db.commit()

        with patch("app.services.erp_auth_service.get_connector") as mock_gc:
            mock_gc.return_value = MagicMock()
            _get_connector_for_tenant(db, default_tenant.id)
            mock_gc.assert_called_once_with("cosium")
