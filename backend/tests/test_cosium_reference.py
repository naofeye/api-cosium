"""Tests for Cosium reference data: adapter mappings, models, and endpoints."""

import pytest

from app.integrations.cosium.adapter_reference import (
    _extract_id_from_href,
    _extract_str_id_from_href,
    _parse_datetime,
    adapt_brand,
    adapt_calendar_event,
    adapt_doctor,
    adapt_mutuelle,
    adapt_site,
    adapt_supplier,
    adapt_tag,
)
from app.models.cosium_reference import (
    CosiumBrand,
    CosiumCalendarEvent,
    CosiumDoctor,
    CosiumMutuelle,
    CosiumSite,
    CosiumSupplier,
    CosiumTag,
)


# --- ID extraction from HAL links ---


class TestExtractIdFromHref:
    def test_numeric_id(self):
        item = {"_links": {"self": {"href": "https://c1.cosium.biz/tenant/api/calendar-events/3"}}}
        assert _extract_id_from_href(item) == 3

    def test_large_id(self):
        item = {"_links": {"self": {"href": "https://c1.cosium.biz/t/api/invoices/12345"}}}
        assert _extract_id_from_href(item) == 12345

    def test_no_links(self):
        assert _extract_id_from_href({}) is None

    def test_uuid_returns_none(self):
        item = {"_links": {"self": {"href": "https://c1.cosium.biz/t/api/doctors/a1b2c3-uuid"}}}
        assert _extract_id_from_href(item) is None

    def test_trailing_slash(self):
        item = {"_links": {"self": {"href": "https://c1.cosium.biz/t/api/tags/42/"}}}
        assert _extract_id_from_href(item) == 42


class TestExtractStrIdFromHref:
    def test_uuid(self):
        item = {"_links": {"self": {"href": "https://c1.cosium.biz/t/api/doctors/abc-123-uuid"}}}
        assert _extract_str_id_from_href(item) == "abc-123-uuid"

    def test_empty(self):
        assert _extract_str_id_from_href({}) == ""


class TestParseDatetime:
    def test_iso_with_z(self):
        dt = _parse_datetime("2026-03-20T10:30:00.000Z")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 20

    def test_none(self):
        assert _parse_datetime(None) is None

    def test_invalid(self):
        assert _parse_datetime("not-a-date") is None


# --- Adapter mappings ---


class TestAdaptCalendarEvent:
    def test_basic_mapping(self):
        raw = {
            "_links": {"self": {"href": "https://c1.cosium.biz/t/api/calendar-events/99"}},
            "startDate": "2026-04-01T09:00:00.000Z",
            "endDate": "2026-04-01T10:00:00.000Z",
            "subject": "Consultation",
            "customerFullname": "DUPONT Jean",
            "customerNumber": "12345",
            "categoryName": "RDV Opticien",
            "categoryColor": "#FF0000",
            "categoryFamilyName": "OPTIC",
            "status": "CONFIRMED",
            "canceled": False,
            "missed": False,
            "customerArrived": True,
            "observation": "Patient regulier",
            "siteName": "Paris 1er",
            "modificationDate": "2026-04-01T08:00:00.000Z",
        }
        result = adapt_calendar_event(raw)
        assert result["cosium_id"] == 99
        assert result["subject"] == "Consultation"
        assert result["customer_fullname"] == "DUPONT Jean"
        assert result["status"] == "CONFIRMED"
        assert result["customer_arrived"] is True
        assert result["start_date"] is not None

    def test_missing_fields_default(self):
        raw = {"_links": {"self": {"href": "https://x/api/calendar-events/1"}}}
        result = adapt_calendar_event(raw)
        assert result["cosium_id"] == 1
        assert result["subject"] == ""
        assert result["canceled"] is False


class TestAdaptMutuelle:
    def test_basic_mapping(self):
        raw = {
            "_links": {"self": {"href": "https://x/api/additional-health-cares/42"}},
            "name": "MGEN",
            "code": "MGN",
            "label": "MGEN Mutuelle Generale",
            "phoneNumber": "0140404040",
            "email": "contact@mgen.fr",
            "city": "Paris",
            "hidden": False,
            "optoAmc": True,
            "coverageRequestPhone": "0140404041",
            "coverageRequestEmail": "pec@mgen.fr",
        }
        result = adapt_mutuelle(raw)
        assert result["cosium_id"] == 42
        assert result["name"] == "MGEN"
        assert result["phone"] == "0140404040"
        assert result["opto_amc"] is True


class TestAdaptDoctor:
    def test_basic_mapping(self):
        raw = {
            "cosiumId": "abc-123-uuid",
            "firstname": "Marie",
            "lastname": "MARTIN",
            "civility": "DR",
            "email": "m.martin@cabinet.fr",
            "mobilePhoneNumber": "0612345678",
            "rppsNumber": "10101010101",
            "specialityName": "Ophtalmologie",
            "opticPrescriber": True,
            "audioPrescriber": False,
            "hidden": False,
        }
        result = adapt_doctor(raw)
        assert result["cosium_id"] == "abc-123-uuid"
        assert result["firstname"] == "Marie"
        assert result["phone"] == "0612345678"
        assert result["optic_prescriber"] is True

    def test_fallback_to_href(self):
        raw = {
            "_links": {"self": {"href": "https://x/api/doctors/fallback-uuid"}},
            "firstname": "Test",
            "lastname": "Doctor",
        }
        result = adapt_doctor(raw)
        assert result["cosium_id"] == "fallback-uuid"


class TestAdaptBrand:
    def test_name(self):
        assert adapt_brand({"name": "Ray-Ban"}) == {"name": "Ray-Ban"}

    def test_empty(self):
        result = adapt_brand({})
        assert result["name"] == ""


class TestAdaptSupplier:
    def test_name(self):
        assert adapt_supplier({"name": "Essilor"}) == {"name": "Essilor"}


class TestAdaptTag:
    def test_basic(self):
        raw = {
            "_links": {"self": {"href": "https://x/api/tags/7"}},
            "code": "VIP",
            "description": "Client VIP",
            "hidden": False,
        }
        result = adapt_tag(raw)
        assert result["cosium_id"] == 7
        assert result["code"] == "VIP"


class TestAdaptSite:
    def test_basic(self):
        raw = {
            "_links": {"self": {"href": "https://x/api/sites/1"}},
            "name": "Magasin Paris",
            "code": "PAR01",
            "longLabel": "Magasin Paris Centre",
            "address": "10 rue de la Paix",
            "postcode": "75002",
            "city": "Paris",
            "country": "France",
            "phone": "0142424242",
        }
        result = adapt_site(raw)
        assert result["cosium_id"] == 1
        assert result["name"] == "Magasin Paris"
        assert result["postcode"] == "75002"


# --- Endpoint auth requirements ---


class TestEndpointsRequireAuth:
    """Verify that all cosium-reference endpoints require authentication."""

    ENDPOINTS = [
        ("GET", "/api/v1/cosium/calendar-events"),
        ("GET", "/api/v1/cosium/mutuelles"),
        ("GET", "/api/v1/cosium/doctors"),
        ("GET", "/api/v1/cosium/brands"),
        ("GET", "/api/v1/cosium/suppliers"),
        ("GET", "/api/v1/cosium/tags"),
        ("GET", "/api/v1/cosium/sites"),
        ("POST", "/api/v1/cosium/sync-reference"),
    ]

    @pytest.mark.parametrize("method,url", ENDPOINTS)
    def test_unauthenticated_returns_401(self, client, method, url):
        if method == "GET":
            resp = client.get(url)
        else:
            resp = client.post(url)
        assert resp.status_code == 401


class TestEndpointsWithAuth:
    """Verify that authenticated GET endpoints return 200 with empty data."""

    GET_ENDPOINTS = [
        "/api/v1/cosium/calendar-events",
        "/api/v1/cosium/mutuelles",
        "/api/v1/cosium/doctors",
        "/api/v1/cosium/brands",
        "/api/v1/cosium/suppliers",
        "/api/v1/cosium/tags",
        "/api/v1/cosium/sites",
    ]

    @pytest.mark.parametrize("url", GET_ENDPOINTS)
    def test_authenticated_get_returns_200(self, client, auth_headers, url):
        resp = client.get(url, headers=auth_headers)
        assert resp.status_code == 200
