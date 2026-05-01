"""Factory pour obtenir un CosiumClient authentifie pour un tenant donne.

Centralise la logique : resolution credentials (cookie/basic/OIDC), creation
client, authentification. Avant : duplique entre `cosium_reference_sync`,
`admin_cosium`, et chaque service qui en avait besoin.

Ne touche pas Cosium en ecriture (Cosium read-only absolu, cf charte).
"""

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError
from app.integrations.cosium.client import CosiumClient
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant


def get_cosium_client_for_tenant(db: Session, tenant_id: int) -> CosiumClient:
    """Retourne un `CosiumClient` authentifie pour le tenant donne.

    Reutilise la chaine `_get_connector_for_tenant` + `_authenticate_connector`
    deja eprouvee pour la sync ERP, garantissant un seul flow d'auth.

    Raises:
        ValueError : tenant introuvable, credentials manquants, decryption echec.
        BusinessError : tenant configure pour un ERP autre que Cosium.
    """
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    _authenticate_connector(connector, tenant)
    if not isinstance(connector, CosiumConnector):
        raise BusinessError(
            f"Tenant {tenant_id} n'est pas configure pour Cosium "
            f"(erp_type={tenant.erp_type})"
        )
    return connector._client
