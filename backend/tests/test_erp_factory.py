"""Tests de la factory ERP."""

import pytest

from app.integrations.erp_factory import get_connector, list_erp_types, SUPPORTED_ERP_TYPES, PLANNED_ERP_TYPES
from app.integrations.erp_connector import ERPConnector
from app.integrations.cosium.cosium_connector import CosiumConnector


def test_get_cosium_connector():
    """La factory retourne un CosiumConnector pour 'cosium'."""
    connector = get_connector("cosium")
    assert isinstance(connector, CosiumConnector)
    assert isinstance(connector, ERPConnector)


def test_get_cosium_case_insensitive():
    """Le type d'ERP est case-insensitive."""
    connector = get_connector("Cosium")
    assert isinstance(connector, CosiumConnector)


def test_get_cosium_with_spaces():
    """Les espaces sont ignores."""
    connector = get_connector("  cosium  ")
    assert isinstance(connector, CosiumConnector)


def test_get_unknown_erp_raises():
    """Un type d'ERP inconnu leve une ValueError."""
    with pytest.raises(ValueError, match="inconnu"):
        get_connector("erp_inexistant")


def test_get_planned_erp_raises_with_message():
    """Un type d'ERP planifie leve une ValueError avec message explicatif."""
    with pytest.raises(ValueError, match="pas encore implemente"):
        get_connector("icanopee")


def test_list_erp_types_returns_all():
    """list_erp_types retourne les types supportes ET planifies."""
    types = list_erp_types()
    type_names = {t["type"] for t in types}
    assert "cosium" in type_names
    assert "icanopee" in type_names
    assert "hexaoptic" in type_names


def test_list_erp_types_status():
    """Chaque type a le bon statut."""
    types = list_erp_types()
    for t in types:
        if t["type"] in SUPPORTED_ERP_TYPES:
            assert t["status"] == "supported"
        elif t["type"] in PLANNED_ERP_TYPES:
            assert t["status"] == "planned"


def test_list_erp_types_has_label():
    """Chaque type a un label."""
    types = list_erp_types()
    for t in types:
        assert t["label"]
        assert isinstance(t["label"], str)
