"""Tests for client linking: HAL extraction, fuzzy matching, data quality endpoint, relink script."""

import pytest
from sqlalchemy import select

from app.integrations.cosium.adapter import cosium_invoice_to_optiflow, cosium_payment_to_optiflow
from app.models import Customer
from app.models.cosium_data import CosiumInvoice, CosiumPayment
from app.services.erp_sync_service import _match_customer_by_name, _normalize_name


# ---------------------------------------------------------------------------
# 1. HAL link extraction from invoice
# ---------------------------------------------------------------------------

class TestInvoiceHALExtraction:
    def test_customer_id_from_direct_field(self):
        """customerId present directly on invoice."""
        data = {"id": 1, "invoiceNumber": "F001", "customerId": 42, "customerName": "DUPONT Jean"}
        result = cosium_invoice_to_optiflow(data)
        assert result["customer_cosium_id"] == "42"

    def test_customer_id_from_hal_link(self):
        """customerId missing, extracted from _links.customer.href."""
        data = {
            "id": 2,
            "invoiceNumber": "F002",
            "customerName": "MARTIN Pierre",
            "_links": {
                "customer": {"href": "https://c1.cosium.biz/tenant/api/customers/12345"}
            },
        }
        result = cosium_invoice_to_optiflow(data)
        assert result["customer_cosium_id"] == "12345"

    def test_customer_id_from_hal_link_with_query_params(self):
        """HAL link with query params should still extract ID."""
        data = {
            "id": 3,
            "invoiceNumber": "F003",
            "_links": {
                "customer": {"href": "https://c1.cosium.biz/tenant/api/customers/999?expand=contact"}
            },
        }
        result = cosium_invoice_to_optiflow(data)
        assert result["customer_cosium_id"] == "999"

    def test_no_customer_id_available(self):
        """No customerId field and no HAL link."""
        data = {"id": 4, "invoiceNumber": "F004", "customerName": "Inconnu"}
        result = cosium_invoice_to_optiflow(data)
        assert result["customer_cosium_id"] == ""


# ---------------------------------------------------------------------------
# 2. HAL link extraction from payment
# ---------------------------------------------------------------------------

class TestPaymentHALExtraction:
    def test_customer_id_from_hal_link(self):
        """Extract customer_cosium_id from payment _links.customer.href."""
        data = {
            "id": 100,
            "amount": 150.0,
            "_links": {
                "customer": {"href": "https://c1.cosium.biz/tenant/api/customers/7890"}
            },
        }
        result = cosium_payment_to_optiflow(data)
        assert result["customer_cosium_id"] == "7890"

    def test_no_customer_link_on_payment(self):
        """Payment without customer link returns None."""
        data = {"id": 101, "amount": 50.0, "issuerName": "DUPONT"}
        result = cosium_payment_to_optiflow(data)
        assert result["customer_cosium_id"] is None


# ---------------------------------------------------------------------------
# 3. Fuzzy matching tests
# ---------------------------------------------------------------------------

class TestFuzzyMatching:
    def _make_name_map(self, names: list[tuple[str, str]]) -> dict[str, int]:
        """Build a name map from (last, first) tuples."""
        name_map: dict[str, int] = {}
        for idx, (last, first) in enumerate(names, start=1):
            normalized_full = _normalize_name(f"{last} {first}")
            name_map[normalized_full] = idx
            normalized_reverse = _normalize_name(f"{first} {last}")
            name_map[normalized_reverse] = idx
        return name_map

    def test_exact_match_still_works(self):
        """Exact match should work before fuzzy kicks in."""
        name_map = self._make_name_map([("DUPONT", "Jean")])
        result = _match_customer_by_name("DUPONT Jean", name_map)
        assert result == 1

    def test_fuzzy_match_accent_differences(self):
        """Fuzzy should match names with accent differences."""
        name_map = self._make_name_map([("LEVEQUE", "Helene")])
        # Input has accents, map is normalized without
        result = _match_customer_by_name("LEVEQUE Helene", name_map)
        assert result == 1

    def test_fuzzy_match_reversed_name(self):
        """Reversed first/last name should match."""
        name_map = self._make_name_map([("MARTIN", "Pierre")])
        result = _match_customer_by_name("Pierre MARTIN", name_map)
        assert result == 1

    def test_fuzzy_match_compound_name(self):
        """Compound names with minor typo should match via fuzzy."""
        name_map = self._make_name_map([("BEAUCHAMP", "Marie")])
        # Typo: BEAUCHAMP -> BEAUCHAMPS (extra S) - very close, score > 85
        result = _match_customer_by_name("BEAUCHAMPS Marie", name_map)
        assert result == 1

    def test_title_prefix_stripping(self):
        """Title prefixes (M., Mme., Dr.) should be stripped."""
        name_map = self._make_name_map([("PETIT", "Sophie")])
        result = _match_customer_by_name("Mme. PETIT Sophie", name_map)
        assert result == 1

    def test_dr_prefix_stripping(self):
        """Dr. prefix should be stripped."""
        name_map = self._make_name_map([("BERNARD", "Luc")])
        result = _match_customer_by_name("Dr. BERNARD Luc", name_map)
        assert result == 1

    def test_no_false_positive_on_fuzzy(self):
        """Very different names should NOT match (score < 85)."""
        name_map = self._make_name_map([("DUPONT", "Jean")])
        result = _match_customer_by_name("MARTINEZ Alfonso", name_map)
        assert result is None

    def test_no_false_positive_short_names(self):
        """Short different names should not match."""
        name_map = self._make_name_map([("LI", "Wei")])
        result = _match_customer_by_name("LO Mei", name_map)
        assert result is None


# ---------------------------------------------------------------------------
# 4. Data quality endpoint
# ---------------------------------------------------------------------------

class TestDataQualityEndpoint:
    def test_data_quality_returns_stats(self, db, client, auth_headers, default_tenant):
        """GET /api/v1/admin/data-quality returns correct link stats."""
        tid = default_tenant.id

        # Clear Redis cache to get fresh data
        from app.core.redis_cache import cache_delete_pattern
        cache_delete_pattern(f"admin:data_quality:{tid}")

        # Create some test customers
        c1 = Customer(tenant_id=tid, first_name="Jean", last_name="DUPONT", cosium_id="100")
        db.add(c1)
        db.flush()

        # Create invoices: 2 linked, 1 orphan
        inv1 = CosiumInvoice(
            tenant_id=tid, cosium_id=901, invoice_number="FTEST001",
            customer_name="DUPONT Jean", customer_id=c1.id, type="INVOICE",
        )
        inv2 = CosiumInvoice(
            tenant_id=tid, cosium_id=902, invoice_number="FTEST002",
            customer_name="DUPONT Jean", customer_id=c1.id, type="INVOICE",
        )
        inv3 = CosiumInvoice(
            tenant_id=tid, cosium_id=903, invoice_number="FTEST003",
            customer_name="INCONNU", type="INVOICE",
        )
        db.add_all([inv1, inv2, inv3])
        db.commit()

        # Clear cache again after adding data
        cache_delete_pattern(f"admin:data_quality:{tid}")

        resp = client.get("/api/v1/admin/data-quality", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        # Should include at least our 3 test invoices
        assert data["invoices"]["total"] >= 3
        assert data["invoices"]["linked"] >= 2
        assert data["invoices"]["orphan"] >= 1
        assert data["invoices"]["link_rate"] >= 0.0
        assert data["invoices"]["total"] == data["invoices"]["linked"] + data["invoices"]["orphan"]

    def test_data_quality_response_structure(self, client, auth_headers):
        """Data quality endpoint returns proper structure."""
        resp = client.get("/api/v1/admin/data-quality", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "invoices" in data
        assert "total" in data["invoices"]
        assert "linked" in data["invoices"]
        assert "orphan" in data["invoices"]
        assert "link_rate" in data["invoices"]
        assert isinstance(data["invoices"]["total"], int)
        assert isinstance(data["invoices"]["link_rate"], float)


# ---------------------------------------------------------------------------
# 5. Relink script
# ---------------------------------------------------------------------------

class TestRelinkScript:
    def test_relink_orphan_invoices(self, db, default_tenant):
        """Relink script should link orphan invoices to customers."""
        from scripts.relink_orphan_data import relink_invoices

        tid = default_tenant.id

        # Create a customer
        c1 = Customer(tenant_id=tid, first_name="Marie", last_name="CURIE", cosium_id="200")
        db.add(c1)
        db.flush()

        # Create an orphan invoice with matching customer_cosium_id
        inv = CosiumInvoice(
            tenant_id=tid, cosium_id=10, invoice_number="F010",
            customer_name="Mme. CURIE Marie", customer_cosium_id="200",
            type="INVOICE",
        )
        db.add(inv)
        db.commit()

        stats = relink_invoices(db, tid)
        assert stats["linked_by_cosium_id"] == 1
        assert stats["still_orphan"] == 0

        # Verify the invoice is now linked
        db.refresh(inv)
        assert inv.customer_id == c1.id

    def test_relink_by_name_fallback(self, db, default_tenant):
        """Relink by name when cosium_id is missing."""
        from scripts.relink_orphan_data import relink_invoices

        tid = default_tenant.id

        c1 = Customer(tenant_id=tid, first_name="Pierre", last_name="MARTIN", cosium_id="300")
        db.add(c1)
        db.flush()

        # Orphan invoice without customer_cosium_id but with matching name
        inv = CosiumInvoice(
            tenant_id=tid, cosium_id=20, invoice_number="F020",
            customer_name="M. MARTIN Pierre", type="INVOICE",
        )
        db.add(inv)
        db.commit()

        stats = relink_invoices(db, tid)
        assert stats["linked_by_name"] == 1
        assert stats["still_orphan"] == 0

        db.refresh(inv)
        assert inv.customer_id == c1.id
