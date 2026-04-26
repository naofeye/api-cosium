"""
Service d'authentification ERP pour OptiFlow.

Gere la resolution du connecteur ERP par tenant et l'authentification
(credentials chiffres, cookies, basic auth).

SYNCHRONISATION UNIDIRECTIONNELLE : ERP -> OptiFlow uniquement.
"""

from sqlalchemy.orm import Session

from app.core.encryption import decrypt
from app.core.logging import get_logger
from app.integrations.erp_connector import ERPConnector
from app.integrations.erp_factory import get_connector
from app.models import Tenant

logger = get_logger("erp_auth_service")


def _get_connector_for_tenant(db: Session, tenant_id: int) -> tuple[ERPConnector, Tenant]:
    """Retourne le connecteur ERP configure pour un tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} introuvable")

    erp_type = tenant.erp_type or "cosium"
    connector = get_connector(erp_type)
    return connector, tenant


def _authenticate_connector(connector: ERPConnector, tenant: Tenant) -> None:
    """Authentifie le connecteur avec les credentials du tenant.

    Priority for Cosium:
    1. Tenant DB cookie credentials (cosium_cookie_access_token_enc)
    2. Settings cookie credentials (COSIUM_ACCESS_TOKEN env var)
    3. OIDC / basic auth credentials
    """
    from app.core.config import settings

    if connector.erp_type == "cosium":
        base_url = settings.cosium_base_url

        # Try tenant-stored cookies first
        tenant_at = getattr(tenant, "cosium_cookie_access_token_enc", None)
        tenant_dc = getattr(tenant, "cosium_cookie_device_credential_enc", None)
        if tenant_at and tenant_dc:
            try:
                at_plain = decrypt(tenant_at)
                dc_plain = decrypt(tenant_dc)
                # Directly configure the underlying CosiumClient for cookie mode
                from app.integrations.cosium.cosium_connector import CosiumConnector

                if isinstance(connector, CosiumConnector):
                    connector._client.base_url = base_url
                    connector._client.tenant = tenant.cosium_tenant or settings.cosium_tenant or ""
                    connector._client._authenticate_cookie(access_token=at_plain, device_credential=dc_plain)
                    logger.info("auth_via_tenant_cookies", tenant_id=tenant.id)
                    return
            except (ValueError, TypeError, OSError) as exc:
                logger.warning("tenant_cookie_decrypt_failed", tenant_id=tenant.id, error=str(exc))

        erp_tenant = tenant.cosium_tenant or settings.cosium_tenant or ""
        login = tenant.cosium_login or settings.cosium_login or ""
        raw_password = tenant.cosium_password_enc or settings.cosium_password or ""
        try:
            password = decrypt(raw_password) if raw_password else ""
        except Exception as exc:
            # En prod/staging, refuser : un secret stocke en clair doit etre
            # remediation explicite (re-chiffrement), pas une derive silencieuse.
            if settings.app_env in ("production", "staging"):
                logger.error(
                    "cosium_password_decrypt_failed",
                    tenant_id=tenant.id,
                    error=str(exc),
                )
                raise ValueError(
                    f"Cosium password for tenant {tenant.id} is not decryptable; "
                    "rechiffrer la valeur (cf. docs/COSIUM_AUTH.md)"
                ) from exc
            # En dev/test, fallback historique pour fixtures non chiffrees.
            logger.warning(
                "password_decrypt_fallback_dev",
                tenant_id=tenant.id,
                error=str(exc),
            )
            password = raw_password
    else:
        erp_config = tenant.erp_config or {}
        base_url = erp_config.get("base_url", "")
        erp_tenant = erp_config.get("tenant", "")
        login = erp_config.get("login", "")
        password = erp_config.get("password", "")

    if not erp_tenant or not login or not password:
        raise ValueError(f"Credentials ERP ({connector.erp_type}) non configurees pour le tenant {tenant.id}")

    connector.authenticate(base_url, erp_tenant, login, password)
