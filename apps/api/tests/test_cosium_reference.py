"""Tests for Cosium reference data: adapter mappings, models, and endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

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
from app.services.cosium_reference_query_service import (
    ilike_filter,
    list_all,
    multi_ilike_filter,
    paginated_query,
)
from app.services.cosium_reference_sync import _sync_entity, sync_all_reference


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


# ===========================================================================
# Helpers partagés pour les tests de service
# ===========================================================================

def _make_mock_client(items: list[dict]) -> MagicMock:
    """Retourne un CosiumClient mocke dont get_paginated renvoie items."""
    client = MagicMock()
    client.get_paginated.return_value = items
    return client


def _get_tenant_id(db: Session) -> int:
    from app.models import Tenant
    return db.query(Tenant).filter(Tenant.slug == "test-magasin").first().id


# ===========================================================================
# Tests : _sync_entity (helper generique de synchronisation)
# ===========================================================================

class TestSyncEntity:
    """Tests unitaires du helper generique _sync_entity."""

    def _mutuelle_raw(self, cosium_id: int, name: str = "OCAM") -> dict:
        return {
            "cosium_id": cosium_id, "name": name, "code": "X", "label": "",
            "phone": "", "email": "", "city": "", "hidden": False, "opto_amc": False,
            "coverage_request_phone": "", "coverage_request_email": "",
        }

    def test_creates_new_rows(self, db):
        """Des entites inexistantes sont inserees en base."""
        tenant_id = _get_tenant_id(db)
        client = _make_mock_client([
            self._mutuelle_raw(1, "OCAM Alpha"),
            self._mutuelle_raw(2, "OCAM Beta"),
        ])

        result = _sync_entity(
            db, tenant_id, 0, client,
            endpoint="/additional-health-cares",
            adapter_fn=lambda r: r,
            model_class=CosiumMutuelle,
            entity_name="mutuelles",
        )

        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["total_fetched"] == 2
        assert db.query(CosiumMutuelle).filter(CosiumMutuelle.tenant_id == tenant_id).count() == 2

    def test_updates_existing_rows(self, db):
        """Des entites deja presentes sont mises a jour (pas reinseres)."""
        tenant_id = _get_tenant_id(db)
        db.add(CosiumMutuelle(
            tenant_id=tenant_id, cosium_id=10, name="Old Name", code="X",
            label="", phone="", email="", city="", hidden=False, opto_amc=False,
            coverage_request_phone="", coverage_request_email="",
        ))
        db.commit()

        client = _make_mock_client([self._mutuelle_raw(10, "New Name")])

        result = _sync_entity(
            db, tenant_id, 0, client,
            endpoint="/additional-health-cares",
            adapter_fn=lambda r: r,
            model_class=CosiumMutuelle,
            entity_name="mutuelles",
        )

        assert result["created"] == 0
        assert result["updated"] == 1
        updated = db.query(CosiumMutuelle).filter(CosiumMutuelle.cosium_id == 10).first()
        assert updated.name == "New Name"

    def test_deduplicates_within_batch(self, db):
        """Des doublons dans la reponse Cosium ne sont inseres qu'une seule fois."""
        tenant_id = _get_tenant_id(db)
        client = _make_mock_client([
            self._mutuelle_raw(99, "Dup"),
            self._mutuelle_raw(99, "Dup again"),
        ])

        result = _sync_entity(
            db, tenant_id, 0, client,
            endpoint="/additional-health-cares",
            adapter_fn=lambda r: r,
            model_class=CosiumMutuelle,
            entity_name="mutuelles",
        )

        assert result["created"] == 1
        assert db.query(CosiumMutuelle).filter(CosiumMutuelle.tenant_id == tenant_id).count() == 1

    def test_skips_items_without_id(self, db):
        """Les items sans id_field sont ignores sans lever d'exception."""
        tenant_id = _get_tenant_id(db)
        client = _make_mock_client([{"name": "No ID"}])  # cosium_id absent

        result = _sync_entity(
            db, tenant_id, 0, client,
            endpoint="/additional-health-cares",
            adapter_fn=lambda r: r,
            model_class=CosiumMutuelle,
            entity_name="mutuelles",
        )

        assert result["created"] == 0
        assert result["total_fetched"] == 1

    def test_empty_cosium_response(self, db):
        """Une reponse vide de Cosium ne cree rien et ne plante pas."""
        tenant_id = _get_tenant_id(db)
        client = _make_mock_client([])

        result = _sync_entity(
            db, tenant_id, 0, client,
            endpoint="/additional-health-cares",
            adapter_fn=lambda r: r,
            model_class=CosiumMutuelle,
            entity_name="mutuelles",
        )

        assert result == {"entity": "mutuelles", "created": 0, "updated": 0, "total_fetched": 0}

    def test_custom_id_field_name(self, db):
        """id_field='name' fonctionne correctement (ex: brands)."""
        tenant_id = _get_tenant_id(db)
        client = _make_mock_client([{"name": "Essilor"}, {"name": "Zeiss"}])

        result = _sync_entity(
            db, tenant_id, 0, client,
            endpoint="/brands",
            adapter_fn=lambda r: r,
            model_class=CosiumBrand,
            entity_name="brands",
            id_field="name",
        )

        assert result["created"] == 2
        assert db.query(CosiumBrand).filter(CosiumBrand.tenant_id == tenant_id).count() == 2

    def test_tenant_isolation(self, db):
        """La sync d'un tenant ne touche pas les lignes d'un autre tenant."""
        from app.models import Organization, Tenant as TenantModel
        other_org = Organization(name="Org2", slug="org2", plan="solo")
        db.add(other_org)
        db.flush()
        other_tenant = TenantModel(
            organization_id=other_org.id, name="Shop2", slug="shop2",
            cosium_tenant="t2", cosium_login="l", cosium_password_enc="p",
        )
        db.add(other_tenant)
        db.flush()
        db.add(CosiumMutuelle(
            tenant_id=other_tenant.id, cosium_id=5, name="Other OCAM", code="O",
            label="", phone="", email="", city="", hidden=False, opto_amc=False,
            coverage_request_phone="", coverage_request_email="",
        ))
        db.commit()

        tenant_id = _get_tenant_id(db)
        client = _make_mock_client([self._mutuelle_raw(5, "My OCAM")])

        _sync_entity(
            db, tenant_id, 0, client,
            endpoint="/additional-health-cares",
            adapter_fn=lambda r: r,
            model_class=CosiumMutuelle,
            entity_name="mutuelles",
        )

        other_row = db.query(CosiumMutuelle).filter(
            CosiumMutuelle.tenant_id == other_tenant.id,
            CosiumMutuelle.cosium_id == 5,
        ).first()
        assert other_row is not None
        assert other_row.name == "Other OCAM"

    def test_audit_log_created_when_user_id_nonzero(self, db):
        """Un audit log est enregistre quand user_id != 0."""
        from app.models.audit import AuditLog
        tenant_id = _get_tenant_id(db)
        client = _make_mock_client([self._mutuelle_raw(1)])

        _sync_entity(
            db, tenant_id, user_id=42, client=client,
            endpoint="/additional-health-cares",
            adapter_fn=lambda r: r,
            model_class=CosiumMutuelle,
            entity_name="mutuelles",
        )

        log = db.query(AuditLog).filter(
            AuditLog.entity_type == "sync_mutuelles",
            AuditLog.user_id == 42,
        ).first()
        assert log is not None

    def test_no_audit_log_when_user_id_zero(self, db):
        """Aucun audit log quand user_id == 0 (taches automatiques)."""
        from app.models.audit import AuditLog
        tenant_id = _get_tenant_id(db)
        client = _make_mock_client([])

        _sync_entity(
            db, tenant_id, user_id=0, client=client,
            endpoint="/additional-health-cares",
            adapter_fn=lambda r: r,
            model_class=CosiumMutuelle,
            entity_name="mutuelles",
        )

        count = db.query(AuditLog).filter(AuditLog.entity_type == "sync_mutuelles").count()
        assert count == 0

    def test_adapter_fn_transforms_raw(self, db):
        """L'adapter_fn est appliquee avant l'upsert."""
        tenant_id = _get_tenant_id(db)
        # Raw item has uppercase name; adapter converts to lowercase
        client = _make_mock_client([{"cosium_id": 1, "name": "UPPERCASE"}])

        def lower_adapter(raw: dict) -> dict:
            return {**raw, "name": raw.get("name", "").lower()}

        _sync_entity(
            db, tenant_id, 0, client,
            endpoint="/additional-health-cares",
            adapter_fn=lower_adapter,
            model_class=CosiumMutuelle,
            entity_name="mutuelles",
            id_field="cosium_id",
        )

        row = db.query(CosiumMutuelle).filter(
            CosiumMutuelle.tenant_id == tenant_id
        ).first()
        assert row.name == "uppercase"


# ===========================================================================
# Tests : sync_all_reference (orchestrateur)
# ===========================================================================

_ALL_SYNC_FN_NAMES = [
    "sync_calendar_events", "sync_mutuelles", "sync_doctors",
    "sync_brands", "sync_suppliers", "sync_tags", "sync_sites",
    "sync_banks", "sync_companies", "sync_users", "sync_equipment_types",
    "sync_frame_materials", "sync_calendar_categories",
    "sync_lens_focus_types", "sync_lens_focus_categories", "sync_lens_materials",
]


def _patch_sync_fns(side_effects: dict[str, Exception | dict] | None = None):
    """Retourne un dict {name: patcher} avec des mocks ou des side_effects."""
    patchers = {}
    for name in _ALL_SYNC_FN_NAMES:
        effect = (side_effects or {}).get(name)
        if isinstance(effect, Exception):
            p = patch(
                f"app.services.cosium_reference_sync.{name}",
                side_effect=effect,
            )
        else:
            default = effect or {"entity": name, "created": 1, "updated": 0, "total_fetched": 1}
            p = patch(
                f"app.services.cosium_reference_sync.{name}",
                return_value=default,
            )
        patchers[name] = p
    return patchers


class TestSyncAllReference:
    """Tests de l'orchestrateur sync_all_reference."""

    def test_invokes_all_16_sync_functions(self, db):
        """sync_all_reference appelle les 16 fonctions individuelles."""
        tenant_id = _get_tenant_id(db)
        patchers = _patch_sync_fns()
        mocks = {name: p.start() for name, p in patchers.items()}

        try:
            result = sync_all_reference(db, tenant_id, user_id=0)
        finally:
            for p in patchers.values():
                p.stop()

        for name, mock in mocks.items():
            mock.assert_called_once_with(db, tenant_id, 0)
        assert len(result["results"]) == 16

    def test_aggregates_created_and_updated(self, db):
        """Les totaux created/updated sont additionnes sur toutes les entites."""
        tenant_id = _get_tenant_id(db)
        per_fn = {"entity": "x", "created": 2, "updated": 1, "total_fetched": 5}
        patchers = _patch_sync_fns({name: per_fn for name in _ALL_SYNC_FN_NAMES})
        for p in patchers.values():
            p.start()

        try:
            result = sync_all_reference(db, tenant_id)
        finally:
            for p in patchers.values():
                p.stop()

        assert result["total_created"] == 2 * 16
        assert result["total_updated"] == 1 * 16

    def test_continues_after_single_entity_failure(self, db):
        """Quand une entite echoue, les autres sont tout de meme synchronisees."""
        tenant_id = _get_tenant_id(db)
        patchers = _patch_sync_fns({"sync_mutuelles": ConnectionError("timeout")})
        for p in patchers.values():
            p.start()

        try:
            result = sync_all_reference(db, tenant_id)
        finally:
            for p in patchers.values():
                p.stop()

        assert len(result["results"]) == 16
        failed = next(r for r in result["results"] if "error" in r)
        assert "timeout" in failed["error"]
        assert failed["created"] == 0
        # Les 15 autres ont created=1 chacune
        assert result["total_created"] == 15

    def test_all_entities_fail_returns_zero_totals(self, db):
        """Si tout echoue, total_created == total_updated == 0."""
        tenant_id = _get_tenant_id(db)
        patchers = _patch_sync_fns({name: OSError("network down") for name in _ALL_SYNC_FN_NAMES})
        for p in patchers.values():
            p.start()

        try:
            result = sync_all_reference(db, tenant_id)
        finally:
            for p in patchers.values():
                p.stop()

        assert result["total_created"] == 0
        assert result["total_updated"] == 0
        assert all("error" in r for r in result["results"])

    def test_uncaught_exception_propagates(self, db):
        """Une RuntimeError (non geree) remonte sans etre avale silencieusement."""
        tenant_id = _get_tenant_id(db)
        patchers = _patch_sync_fns({"sync_calendar_events": RuntimeError("unexpected")})
        for p in patchers.values():
            p.start()

        try:
            with pytest.raises(RuntimeError, match="unexpected"):
                sync_all_reference(db, tenant_id)
        finally:
            for p in patchers.values():
                p.stop()

    def test_result_keys_present(self, db):
        """Le dict retourne contient toujours les cles results/total_created/total_updated."""
        tenant_id = _get_tenant_id(db)
        patchers = _patch_sync_fns(
            {name: {"entity": name, "created": 0, "updated": 0, "total_fetched": 0}
             for name in _ALL_SYNC_FN_NAMES}
        )
        for p in patchers.values():
            p.start()

        try:
            result = sync_all_reference(db, tenant_id)
        finally:
            for p in patchers.values():
                p.stop()

        assert set(result.keys()) >= {"results", "total_created", "total_updated"}
        assert isinstance(result["results"], list)

    def test_passes_user_id_to_each_function(self, db):
        """Le user_id fourni est transmis a chacune des fonctions de sync."""
        tenant_id = _get_tenant_id(db)
        patchers = _patch_sync_fns()
        mocks = {name: p.start() for name, p in patchers.items()}

        try:
            sync_all_reference(db, tenant_id, user_id=99)
        finally:
            for p in patchers.values():
                p.stop()

        for mock in mocks.values():
            args, _ = mock.call_args
            # Signature: sync_fn(db, tenant_id, user_id)
            assert args[2] == 99


# ===========================================================================
# Tests : cosium_reference_query_service — paginated_query
# ===========================================================================

class TestPaginatedQuery:
    """Tests de la fonction generique paginated_query."""

    def _seed_mutuelles(self, db, tenant_id: int, count: int) -> None:
        for i in range(count):
            db.add(CosiumMutuelle(
                tenant_id=tenant_id, cosium_id=100 + i, name=f"OCAM {i:02d}",
                code=f"C{i}", label="", phone="", email="", city="",
                hidden=False, opto_amc=False,
                coverage_request_phone="", coverage_request_email="",
            ))
        db.commit()

    def test_first_page_returns_correct_slice(self, db):
        tenant_id = _get_tenant_id(db)
        self._seed_mutuelles(db, tenant_id, 10)

        result = paginated_query(db, CosiumMutuelle, tenant_id, page=1, page_size=5)

        assert result["total"] == 10
        assert result["page"] == 1
        assert result["page_size"] == 5
        assert len(result["items"]) == 5

    def test_second_page_returns_remaining(self, db):
        tenant_id = _get_tenant_id(db)
        self._seed_mutuelles(db, tenant_id, 7)

        result = paginated_query(db, CosiumMutuelle, tenant_id, page=2, page_size=5)

        assert result["total"] == 7
        assert len(result["items"]) == 2

    def test_empty_table_returns_zero_total(self, db):
        tenant_id = _get_tenant_id(db)

        result = paginated_query(db, CosiumMutuelle, tenant_id, page=1, page_size=10)

        assert result["total"] == 0
        assert result["items"] == []

    def test_filter_reduces_results(self, db):
        """Un filtre WHERE supplementaire ne renvoie que les lignes correspondantes."""
        tenant_id = _get_tenant_id(db)
        self._seed_mutuelles(db, tenant_id, 5)
        db.add(CosiumMutuelle(
            tenant_id=tenant_id, cosium_id=200, name="Hidden OCAM", code="H",
            label="", phone="", email="", city="", hidden=True, opto_amc=False,
            coverage_request_phone="", coverage_request_email="",
        ))
        db.commit()

        result = paginated_query(
            db, CosiumMutuelle, tenant_id, page=1, page_size=20,
            filters=[CosiumMutuelle.hidden == False],  # noqa: E712
        )

        assert result["total"] == 5
        assert all(not item.hidden for item in result["items"])

    def test_order_by_desc(self, db):
        """L'ORDER BY descendant est respecte."""
        tenant_id = _get_tenant_id(db)
        self._seed_mutuelles(db, tenant_id, 4)

        result = paginated_query(
            db, CosiumMutuelle, tenant_id, page=1, page_size=10,
            order_by=[CosiumMutuelle.name.desc()],
        )

        names = [item.name for item in result["items"]]
        assert names == sorted(names, reverse=True)

    def test_response_schema_validates_items(self, db):
        """Quand response_schema est fourni, les items sont des instances Pydantic."""
        from pydantic import BaseModel, ConfigDict

        class Out(BaseModel):
            model_config = ConfigDict(from_attributes=True)
            id: int
            name: str

        tenant_id = _get_tenant_id(db)
        self._seed_mutuelles(db, tenant_id, 3)

        result = paginated_query(
            db, CosiumMutuelle, tenant_id, page=1, page_size=10,
            response_schema=Out,
        )

        assert all(isinstance(item, Out) for item in result["items"])

    def test_tenant_isolation(self, db):
        """paginated_query ne retourne que les donnees du tenant demande."""
        from app.models import Organization, Tenant as TenantModel
        other_org = Organization(name="Org PQ", slug="org-pq", plan="solo")
        db.add(other_org)
        db.flush()
        other = TenantModel(
            organization_id=other_org.id, name="Shop PQ", slug="shop-pq",
            cosium_tenant="pq", cosium_login="l", cosium_password_enc="p",
        )
        db.add(other)
        db.flush()
        db.add(CosiumMutuelle(
            tenant_id=other.id, cosium_id=999, name="Other OCAM", code="O",
            label="", phone="", email="", city="", hidden=False, opto_amc=False,
            coverage_request_phone="", coverage_request_email="",
        ))
        db.commit()

        tenant_id = _get_tenant_id(db)
        self._seed_mutuelles(db, tenant_id, 2)

        result = paginated_query(db, CosiumMutuelle, tenant_id, page=1, page_size=20)

        assert result["total"] == 2
        assert all(item.tenant_id == tenant_id for item in result["items"])


# ===========================================================================
# Tests : cosium_reference_query_service — list_all
# ===========================================================================

class TestListAll:
    """Tests de la fonction list_all (sans pagination)."""

    def _seed_doctors(self, db, tenant_id: int, count: int) -> None:
        for i in range(count):
            db.add(CosiumDoctor(
                tenant_id=tenant_id, cosium_id=str(i + 1),
                firstname=f"Prenom{i}", lastname=f"Nom{i}",
                civility="Dr", specialty="ophtalmo",
                optic_prescriber=True, audio_prescriber=False, hidden=False,
            ))
        db.commit()

    def test_returns_all_rows(self, db):
        tenant_id = _get_tenant_id(db)
        self._seed_doctors(db, tenant_id, 5)

        items = list_all(db, CosiumDoctor, tenant_id)

        assert len(items) == 5

    def test_empty_returns_empty_list(self, db):
        tenant_id = _get_tenant_id(db)
        items = list_all(db, CosiumDoctor, tenant_id)
        assert list(items) == []

    def test_order_by_respected(self, db):
        tenant_id = _get_tenant_id(db)
        self._seed_doctors(db, tenant_id, 4)

        items = list_all(db, CosiumDoctor, tenant_id, order_by=[CosiumDoctor.lastname.asc()])

        lastnames = [item.lastname for item in items]
        assert lastnames == sorted(lastnames)

    def test_schema_validation(self, db):
        from pydantic import BaseModel, ConfigDict

        class DoctorOut(BaseModel):
            model_config = ConfigDict(from_attributes=True)
            id: int
            firstname: str
            lastname: str

        tenant_id = _get_tenant_id(db)
        self._seed_doctors(db, tenant_id, 2)

        items = list_all(db, CosiumDoctor, tenant_id, response_schema=DoctorOut)

        assert len(items) == 2
        assert all(isinstance(item, DoctorOut) for item in items)

    def test_tenant_isolation(self, db):
        from app.models import Organization, Tenant as TenantModel
        other_org = Organization(name="Org LA", slug="org-la", plan="solo")
        db.add(other_org)
        db.flush()
        other = TenantModel(
            organization_id=other_org.id, name="Shop LA", slug="shop-la",
            cosium_tenant="la", cosium_login="l", cosium_password_enc="p",
        )
        db.add(other)
        db.flush()
        db.add(CosiumDoctor(
            tenant_id=other.id, cosium_id="X99", firstname="Other",
            lastname="Doctor", civility="Dr", specialty="", optic_prescriber=False,
            audio_prescriber=False, hidden=False,
        ))
        db.commit()

        tenant_id = _get_tenant_id(db)
        self._seed_doctors(db, tenant_id, 3)

        items = list_all(db, CosiumDoctor, tenant_id)

        assert len(items) == 3
        assert all(item.tenant_id == tenant_id for item in items)


# ===========================================================================
# Tests : ilike_filter / multi_ilike_filter
# ===========================================================================

class TestFilterHelpers:
    """Tests des helpers de filtrage ilike et multi_ilike."""

    def _seed_brands(self, db, tenant_id: int) -> None:
        for name in ["Essilor", "Zeiss", "Rodenstock", "Varilux"]:
            db.add(CosiumBrand(tenant_id=tenant_id, name=name))
        db.commit()

    def test_ilike_case_insensitive_match(self, db):
        tenant_id = _get_tenant_id(db)
        self._seed_brands(db, tenant_id)

        result = paginated_query(
            db, CosiumBrand, tenant_id, page=1, page_size=20,
            filters=[ilike_filter(CosiumBrand.name, "essilor")],
        )

        assert result["total"] == 1
        assert result["items"][0].name == "Essilor"

    def test_ilike_partial_match(self, db):
        tenant_id = _get_tenant_id(db)
        self._seed_brands(db, tenant_id)

        result = paginated_query(
            db, CosiumBrand, tenant_id, page=1, page_size=20,
            filters=[ilike_filter(CosiumBrand.name, "oden")],
        )

        assert result["total"] == 1
        assert result["items"][0].name == "Rodenstock"

    def test_ilike_no_match(self, db):
        tenant_id = _get_tenant_id(db)
        self._seed_brands(db, tenant_id)

        result = paginated_query(
            db, CosiumBrand, tenant_id, page=1, page_size=20,
            filters=[ilike_filter(CosiumBrand.name, "Luxottica")],
        )

        assert result["total"] == 0

    def test_multi_ilike_matches_any_column(self, db):
        """multi_ilike_filter cherche en OR sur plusieurs colonnes."""
        tenant_id = _get_tenant_id(db)
        for fn, ln in [("Alice", "Martin"), ("Bob", "Alice"), ("Charlie", "Dupont")]:
            db.add(CosiumDoctor(
                tenant_id=tenant_id, cosium_id=f"D{fn}", firstname=fn, lastname=ln,
                civility="Dr", specialty="", optic_prescriber=False,
                audio_prescriber=False, hidden=False,
            ))
        db.commit()

        result = paginated_query(
            db, CosiumDoctor, tenant_id, page=1, page_size=20,
            filters=[multi_ilike_filter(
                [CosiumDoctor.firstname, CosiumDoctor.lastname], "alice"
            )],
        )

        # "alice" correspond au firstname de la 1ere ligne ET au lastname de la 2eme
        assert result["total"] == 2

    def test_multi_ilike_no_match(self, db):
        tenant_id = _get_tenant_id(db)
        db.add(CosiumDoctor(
            tenant_id=tenant_id, cosium_id="D1", firstname="Henri", lastname="Bernard",
            civility="Dr", specialty="", optic_prescriber=False,
            audio_prescriber=False, hidden=False,
        ))
        db.commit()

        result = paginated_query(
            db, CosiumDoctor, tenant_id, page=1, page_size=20,
            filters=[multi_ilike_filter(
                [CosiumDoctor.firstname, CosiumDoctor.lastname], "zzz"
            )],
        )

        assert result["total"] == 0
