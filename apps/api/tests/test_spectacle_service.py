"""Tests unitaires pour spectacle_service.

Couvre :
- list_spectacle_files_for_customer : cas nominal, liste vide, erreur connecteur
- get_spectacle_file_complete : cas nominal, dossier introuvable, echec dioptries/selection,
  dossier sans dioptries ni selection
"""
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.services.spectacle_service import (
    get_spectacle_file_complete,
    list_spectacle_files_for_customer,
)


# ---------------------------------------------------------------------------
# Helpers — RAW Cosium shapes
# ---------------------------------------------------------------------------

def _raw_spectacle_file(file_id: int, *, has_diopters: bool = True, has_selection: bool = True) -> dict:
    """Produit un dict brut Cosium qui ressemble a un spectacles-file HAL."""
    links: dict = {
        "self": {"href": f"/tenant/api/v1/end-consumer/spectacles-files/{file_id}"},
    }
    if has_diopters:
        links["diopters"] = {"href": f"/tenant/api/v1/end-consumer/spectacles-files/{file_id}/diopters"}
    if has_selection:
        links["spectacles-selection"] = {
            "href": f"/tenant/api/v1/end-consumer/spectacles-files/{file_id}/spectacles-selection"
        }
    return {"_links": links, "creationDate": "2025-03-15"}


def _raw_diopter(sphere_right: float = -125) -> dict:
    """Produit un dict brut Cosium de dioptries.

    Les valeurs spheriques sont en centièmes de dioptrie (ex: -125 = -1.25 D).
    """
    return {
        "sphere100Right": sphere_right,
        "cylinder100Right": -50,
        "axisRight": 90,
        "addition100Right": None,
        "prism100Right": None,
        "sphere100Left": -100,
        "cylinder100Left": -25,
        "axisLeft": 85,
        "addition100Left": None,
        "prism100Left": None,
        "visionType": "VL",
    }


def _mock_connector(
    file_id: int = 42,
    *,
    has_diopters: bool = True,
    has_selection: bool = True,
    diopters: list[dict] | None = None,
    selection: dict | None = None,
) -> MagicMock:
    connector = MagicMock()
    connector.get_spectacle_file.return_value = _raw_spectacle_file(
        file_id, has_diopters=has_diopters, has_selection=has_selection
    )
    connector.get_spectacle_diopters.return_value = diopters if diopters is not None else [_raw_diopter()]
    connector.get_spectacle_selection.return_value = selection if selection is not None else {"brand": "ACME"}
    return connector


# ---------------------------------------------------------------------------
# list_spectacle_files_for_customer
# ---------------------------------------------------------------------------

class TestListSpectacleFilesForCustomer:
    def test_returns_mapped_files(self) -> None:
        """Retourne une liste de dossiers mappes depuis la reponse Cosium."""
        connector = MagicMock()
        connector.list_spectacle_files_for_customer.return_value = [
            _raw_spectacle_file(1),
            _raw_spectacle_file(2, has_diopters=False),
        ]

        result = list_spectacle_files_for_customer(connector, customer_cosium_id=999)

        connector.list_spectacle_files_for_customer.assert_called_once_with(999)
        assert len(result) == 2
        assert result[0]["cosium_id"] == 1
        assert result[0]["has_diopters"] is True
        assert result[1]["cosium_id"] == 2
        assert result[1]["has_diopters"] is False

    def test_returns_empty_list_when_cosium_returns_empty(self) -> None:
        """Retourne une liste vide si Cosium n'a aucun dossier pour ce client."""
        connector = MagicMock()
        connector.list_spectacle_files_for_customer.return_value = []

        result = list_spectacle_files_for_customer(connector, customer_cosium_id=999)

        assert result == []

    def test_returns_empty_list_on_connector_error(self) -> None:
        """Absorbe les exceptions du connecteur et retourne une liste vide."""
        connector = MagicMock()
        connector.list_spectacle_files_for_customer.side_effect = ConnectionError("timeout")

        result = list_spectacle_files_for_customer(connector, customer_cosium_id=999)

        assert result == []

    def test_returns_empty_list_on_http_error(self) -> None:
        """Absorbe une erreur HTTP generique du connecteur."""
        connector = MagicMock()
        connector.list_spectacle_files_for_customer.side_effect = Exception("404 Not Found")

        result = list_spectacle_files_for_customer(connector, customer_cosium_id=999)

        assert result == []

    def test_creation_date_is_mapped(self) -> None:
        """La date de creation du dossier est bien transmise."""
        raw = _raw_spectacle_file(7)
        raw["creationDate"] = "2024-11-20"
        connector = MagicMock()
        connector.list_spectacle_files_for_customer.return_value = [raw]

        result = list_spectacle_files_for_customer(connector, customer_cosium_id=10)

        assert result[0]["creation_date"] == "2024-11-20"


# ---------------------------------------------------------------------------
# get_spectacle_file_complete
# ---------------------------------------------------------------------------

class TestGetSpectacleFileComplete:
    def test_returns_complete_dossier(self) -> None:
        """Cas nominal : retourne file + diopters + selection."""
        connector = _mock_connector(file_id=42)

        result = get_spectacle_file_complete(connector, file_id=42)

        assert result["file"]["cosium_id"] == 42
        assert result["file"]["has_diopters"] is True
        assert result["file"]["has_selection"] is True
        assert len(result["diopters"]) == 1
        assert result["selection"] == {"brand": "ACME"}

    def test_raises_not_found_when_cosium_raises(self) -> None:
        """Leve NotFoundError quand Cosium leve une exception sur le fichier principal."""
        connector = MagicMock()
        connector.get_spectacle_file.side_effect = Exception("404 from Cosium")

        with pytest.raises(NotFoundError) as exc_info:
            get_spectacle_file_complete(connector, file_id=99)

        error = exc_info.value
        assert error.entity == "Dossier lunettes"
        assert error.entity_id == 99

    def test_diopters_skipped_when_has_diopters_false(self) -> None:
        """Si le dossier n'a pas de dioptries (has_diopters=False), le connecteur n'est pas appele."""
        connector = _mock_connector(file_id=10, has_diopters=False, has_selection=False)

        result = get_spectacle_file_complete(connector, file_id=10)

        connector.get_spectacle_diopters.assert_not_called()
        assert result["diopters"] == []

    def test_selection_skipped_when_has_selection_false(self) -> None:
        """Si le dossier n'a pas de selection (has_selection=False), le connecteur n'est pas appele."""
        connector = _mock_connector(file_id=10, has_diopters=False, has_selection=False)

        result = get_spectacle_file_complete(connector, file_id=10)

        connector.get_spectacle_selection.assert_not_called()
        assert result["selection"] == {}

    def test_diopters_error_is_swallowed(self) -> None:
        """Une erreur lors de la recuperation des dioptries ne fait pas planter le service."""
        connector = _mock_connector(file_id=42)
        connector.get_spectacle_diopters.side_effect = Exception("diopters endpoint error")

        result = get_spectacle_file_complete(connector, file_id=42)

        # Le dossier principal et la selection sont toujours retournes
        assert result["file"]["cosium_id"] == 42
        assert result["diopters"] == []
        assert result["selection"] == {"brand": "ACME"}

    def test_selection_error_is_swallowed(self) -> None:
        """Une erreur lors de la recuperation de la selection ne fait pas planter le service."""
        connector = _mock_connector(file_id=42)
        connector.get_spectacle_selection.side_effect = RuntimeError("selection endpoint 500")

        result = get_spectacle_file_complete(connector, file_id=42)

        assert result["file"]["cosium_id"] == 42
        assert len(result["diopters"]) == 1
        assert result["selection"] == {}

    def test_multiple_diopters_are_all_mapped(self) -> None:
        """Plusieurs dioptries sont toutes mappees."""
        diopters = [_raw_diopter(-125), _raw_diopter(-200), _raw_diopter(-50)]
        connector = _mock_connector(file_id=5, diopters=diopters)

        result = get_spectacle_file_complete(connector, file_id=5)

        assert len(result["diopters"]) == 3

    def test_has_doctor_address_is_mapped(self) -> None:
        """has_doctor_address est bien reporte dans file_meta."""
        raw = _raw_spectacle_file(77, has_diopters=True, has_selection=False)
        raw["_links"]["doctor-address"] = {"href": ".../doctor-address"}
        connector = MagicMock()
        connector.get_spectacle_file.return_value = raw
        connector.get_spectacle_diopters.return_value = [_raw_diopter()]

        result = get_spectacle_file_complete(connector, file_id=77)

        assert result["file"]["has_doctor_address"] is True
