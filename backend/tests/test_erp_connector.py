"""Tests du connecteur ERP — CosiumConnector implemente toutes les methodes."""

from app.integrations.erp_connector import ERPConnector
from app.integrations.cosium.cosium_connector import CosiumConnector


def test_cosium_connector_is_erp_connector():
    """CosiumConnector est bien une sous-classe de ERPConnector."""
    assert issubclass(CosiumConnector, ERPConnector)


def test_cosium_connector_erp_type():
    """Le type d'ERP est 'cosium'."""
    connector = CosiumConnector()
    assert connector.erp_type == "cosium"


def test_cosium_connector_not_authenticated_by_default():
    """Le connecteur n'est pas authentifie par defaut."""
    connector = CosiumConnector()
    assert connector.is_authenticated is False


def test_cosium_connector_has_all_methods():
    """CosiumConnector implemente toutes les methodes abstraites."""
    connector = CosiumConnector()
    assert hasattr(connector, "authenticate")
    assert hasattr(connector, "get_customers")
    assert hasattr(connector, "get_invoices")
    assert hasattr(connector, "get_invoiced_items")
    assert hasattr(connector, "get_products")
    assert hasattr(connector, "get_product_stock")
    assert hasattr(connector, "get_payment_types")
    assert callable(connector.authenticate)
    assert callable(connector.get_customers)
    assert callable(connector.get_invoices)
    assert callable(connector.get_invoiced_items)
    assert callable(connector.get_products)
    assert callable(connector.get_product_stock)
    assert callable(connector.get_payment_types)


def test_cosium_connector_no_write_methods():
    """CosiumConnector ne doit PAS avoir de methodes d'ecriture."""
    connector = CosiumConnector()
    assert not hasattr(connector, "put")
    assert not hasattr(connector, "post")
    assert not hasattr(connector, "delete")
    assert not hasattr(connector, "patch")
    assert not hasattr(connector, "request")


def test_erp_connector_is_abstract():
    """ERPConnector ne peut pas etre instancie directement."""
    try:
        ERPConnector()  # type: ignore
        assert False, "ERPConnector should not be instantiable"
    except TypeError:
        pass
