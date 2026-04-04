"""Tests Cosium en conditions réelles.

Ces tests nécessitent des credentials Cosium valides.
Ils sont skippés par défaut. Lancer avec : pytest -m cosium_live
"""

import pytest
from unittest.mock import patch, MagicMock

from app.integrations.cosium.client import CosiumClient
from app.integrations.cosium.adapter import (
    cosium_customer_to_optiflow,
    cosium_invoice_to_optiflow,
    cosium_product_to_optiflow,
)


# === Adapter tests (always run — no Cosium connection needed) ===

def test_customer_adapter_full() -> None:
    raw = {
        "id": 42,
        "firstName": "Jean",
        "lastName": "Dupont",
        "birthDate": "1985-03-15",
        "socialSecurityNumber": "185031512345678",
        "contact": {"email": "jean@test.com", "mobilePhoneNumber": "0612345678", "phoneNumber": "0112345678"},
        "address": {"street": "12 rue des Lilas", "city": "Paris", "zipCode": "75001"},
    }
    result = cosium_customer_to_optiflow(raw)
    assert result["first_name"] == "Jean"
    assert result["last_name"] == "Dupont"
    assert result["email"] == "jean@test.com"
    assert result["phone"] == "0612345678"
    assert result["birth_date"] == "1985-03-15"
    assert result["city"] == "Paris"
    assert result["postal_code"] == "75001"
    assert result["social_security_number"] == "185031512345678"
    assert result["cosium_id"] == "42"


def test_customer_adapter_missing_fields() -> None:
    raw = {"id": 1, "firstName": "", "lastName": "Solo"}
    result = cosium_customer_to_optiflow(raw)
    assert result["last_name"] == "Solo"
    assert result["email"] is None
    assert result["phone"] is None


def test_invoice_adapter() -> None:
    raw = {
        "id": 100, "type": "INVOICE", "number": "F-2026-001",
        "date": "2026-01-15", "totalAmountTaxIncluded": 456.00,
        "totalAmountTaxExcluded": 380.00, "totalTaxAmount": 76.00,
        "settled": True, "customerId": 42,
    }
    result = cosium_invoice_to_optiflow(raw)
    assert result["numero"] == "F-2026-001"
    assert result["montant_ttc"] == 456.00
    assert result["montant_ht"] == 380.00
    assert result["settled"] is True


def test_product_adapter() -> None:
    raw = {
        "id": 200, "code": "MON-001", "eanCode": "3401234567890",
        "gtinCode": "03401234567890", "label": "Monture Ray-Ban",
        "familyType": "FRAME", "sellingPriceTaxIncluded": 150.00,
    }
    result = cosium_product_to_optiflow(raw)
    assert result["code"] == "MON-001"
    assert result["ean"] == "3401234567890"
    assert result["label"] == "Monture Ray-Ban"
    assert result["price"] == 150.00


def test_client_get_paginated_mock() -> None:
    client = CosiumClient()
    client.token = "fake-token"
    client.tenant = "test"

    with patch.object(client, "get") as mock_get:
        mock_get.return_value = {
            "_embedded": {"customers": [{"id": 1}, {"id": 2}]},
            "page": {"totalPages": 1},
        }
        items = client.get_paginated("/customers", page_size=10, max_pages=1)
        assert len(items) == 2


def test_client_get_paginated_multi_page() -> None:
    client = CosiumClient()
    client.token = "fake-token"
    client.tenant = "test"

    call_count = 0
    def mock_get(endpoint, params=None):
        nonlocal call_count
        page = params.get("page_number", 0)
        call_count += 1
        if page == 0:
            return {"_embedded": {"customers": [{"id": 1}, {"id": 2}]}, "page": {"totalPages": 2}}
        return {"_embedded": {"customers": [{"id": 3}]}, "page": {"totalPages": 2}}

    with patch.object(client, "get", side_effect=mock_get):
        items = client.get_paginated("/customers", page_size=2, max_pages=5)
        assert len(items) == 3
        assert call_count == 2


# === Live tests (skip by default) ===

@pytest.mark.cosium_live
def test_cosium_authenticate_real() -> None:
    """Test real Cosium authentication. Requires COSIUM_* env vars."""
    from app.core.config import settings
    if not settings.cosium_tenant:
        pytest.skip("COSIUM_TENANT not configured")
    client = CosiumClient()
    token = client.authenticate()
    assert token
    assert len(token) > 10


@pytest.mark.cosium_live
def test_cosium_get_customers_real() -> None:
    """Test real Cosium customer retrieval."""
    from app.core.config import settings
    if not settings.cosium_tenant:
        pytest.skip("COSIUM_TENANT not configured")
    client = CosiumClient()
    client.authenticate()
    data = client.get("/customers", {"page_size": 5})
    assert isinstance(data, dict)
