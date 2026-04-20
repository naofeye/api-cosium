"""Factory pour les connecteurs ERP.

Retourne le bon connecteur en fonction du type d'ERP configure pour un tenant.
"""

from app.core.logging import get_logger
from app.integrations.erp_connector import ERPConnector

logger = get_logger("erp_factory")

# Types d'ERP supportes
SUPPORTED_ERP_TYPES = {"cosium"}

# Types planifies (non encore implementes)
PLANNED_ERP_TYPES = {"icanopee", "hexaoptic", "osmose"}


def get_connector(erp_type: str, client: object | None = None) -> ERPConnector:
    """Retourne une instance du connecteur ERP correspondant.

    Args:
        erp_type: identifiant du type d'ERP ("cosium", "icanopee", etc.)
        client: instance de client ERP optionnelle (injection de dependances)

    Returns:
        Instance du connecteur ERP

    Raises:
        ValueError: si le type d'ERP n'est pas supporte
    """
    erp_type = erp_type.lower().strip()

    if erp_type == "cosium":
        from app.integrations.cosium.cosium_connector import CosiumConnector

        return CosiumConnector(client=client)

    if erp_type in PLANNED_ERP_TYPES:
        raise ValueError(
            f"Le connecteur ERP '{erp_type}' est prevu mais pas encore implemente. "
            f"Contactez le support pour plus d'informations."
        )

    raise ValueError(
        f"Type d'ERP inconnu : '{erp_type}'. "
        f"Types supportes : {', '.join(sorted(SUPPORTED_ERP_TYPES))}. "
        f"Types prevus : {', '.join(sorted(PLANNED_ERP_TYPES))}."
    )


def list_erp_types() -> list[dict]:
    """Liste tous les types d'ERP avec leur statut."""
    result = []
    for t in sorted(SUPPORTED_ERP_TYPES):
        result.append({"type": t, "status": "supported", "label": t.capitalize()})
    for t in sorted(PLANNED_ERP_TYPES):
        result.append({"type": t, "status": "planned", "label": t.capitalize()})
    return result
