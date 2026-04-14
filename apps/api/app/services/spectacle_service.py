"""Service pour les dossiers lunettes Cosium — LECTURE SEULE.

Orchestration des appels Cosium pour recuperer un dossier lunettes complet
(metadata + dioptries + selection) et la liste des dossiers d'un client.

Pas de persistance locale pour l'instant — lecture live via Cosium.
La persistance (sync incremental) viendra dans une etape ulterieure.
"""
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.integrations.cosium.adapter import (
    cosium_diopter_to_optiflow,
    cosium_spectacle_file_to_optiflow,
)
from app.integrations.cosium.cosium_connector import CosiumConnector

logger = get_logger("spectacle_service")


def get_spectacle_file_complete(connector: CosiumConnector, file_id: int) -> dict:
    """Recupere un dossier lunettes complet : metadata + dioptries + selection.

    Retourne :
    {
      "file": {"cosium_id": int, "has_diopters": bool, ...},
      "diopters": [{"sphere_right": float, ...}, ...],
      "selection": {...raw Cosium spectacles-selection...}
    }
    """
    try:
        raw_file = connector.get_spectacle_file(file_id)
    except Exception as e:
        logger.warning("spectacle_file_not_found", file_id=file_id, error=str(e))
        raise NotFoundError("Dossier lunettes", file_id)

    file_meta = cosium_spectacle_file_to_optiflow(raw_file)

    diopters: list[dict] = []
    if file_meta.get("has_diopters"):
        try:
            raw_diopters = connector.get_spectacle_diopters(file_id)
            diopters = [cosium_diopter_to_optiflow(d) for d in raw_diopters]
        except Exception as e:
            logger.warning("spectacle_diopters_fetch_failed", file_id=file_id, error=str(e))

    selection: dict = {}
    if file_meta.get("has_selection"):
        try:
            selection = connector.get_spectacle_selection(file_id)
        except Exception as e:
            logger.warning("spectacle_selection_fetch_failed", file_id=file_id, error=str(e))

    logger.info(
        "spectacle_file_fetched",
        file_id=file_id,
        diopters_count=len(diopters),
        has_selection=bool(selection),
    )
    return {"file": file_meta, "diopters": diopters, "selection": selection}


def list_spectacle_files_for_customer(connector: CosiumConnector, customer_cosium_id: int) -> list[dict]:
    """Liste les dossiers lunettes d'un client Cosium (metadata seulement)."""
    try:
        raw_list = connector.list_spectacle_files_for_customer(customer_cosium_id)
    except Exception as e:
        logger.warning(
            "spectacle_files_list_failed",
            customer_cosium_id=customer_cosium_id,
            error=str(e),
        )
        return []

    result = [cosium_spectacle_file_to_optiflow(item) for item in raw_list]
    logger.info(
        "spectacle_files_listed",
        customer_cosium_id=customer_cosium_id,
        total=len(result),
    )
    return result
