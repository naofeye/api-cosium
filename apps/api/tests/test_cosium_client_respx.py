"""Tests d'intégration Cosium via respx — mock HTTP complet.

Objectif : valider le CosiumClient contre des réponses HTTP mockées au niveau
transport httpx (respx intercepte), sans dépendre de credentials Cosium réels.

Couvre :
- Authentification basic (POST /authenticate/basic)
- GET lecture simple
- Pagination HAL multi-pages
- Pagination Spring Data
- Retry sur échec transitoire
- Token refresh après 25 min (mode basic)
- Règle sécurité : seuls POST /authenticate/basic + GET sont autorisés
"""

import time

import httpx
import pytest
import respx

from app.integrations.cosium.client import CosiumClient

BASE = "https://c1.cosium.biz"
TENANT = "test-tenant"
LOGIN = "test-login"
PASSWORD = "test-password"


@pytest.fixture(name="client")
def _client_fixture(monkeypatch) -> CosiumClient:
    # Désactive les delays de retry pour garder les tests rapides
    monkeypatch.setattr("app.integrations.cosium.client.RETRY_DELAYS", [0, 0, 0])
    monkeypatch.setattr("app.integrations.cosium.client.time.sleep", lambda *_: None)
    c = CosiumClient()
    c.base_url = BASE
    c.tenant = TENANT
    return c


class TestAuthenticate:
    @respx.mock
    def test_basic_auth_returns_token(self, client: CosiumClient):
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "tok-123"}),
        )

        token = client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)

        assert token == "tok-123"
        assert client.token == "tok-123"
        assert client._auth_mode == "basic"

    @respx.mock
    def test_basic_auth_accepts_access_token_field(self, client: CosiumClient):
        """L'API peut renvoyer `access_token` ou `accessToken` au lieu de `token`."""
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"accessToken": "alt-token"}),
        )
        token = client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        assert token == "alt-token"

    @respx.mock
    def test_basic_auth_retries_on_server_error(self, client: CosiumClient):
        """3 tentatives : 2 erreurs puis succès."""
        route = respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            side_effect=[
                httpx.Response(500),
                httpx.Response(502),
                httpx.Response(200, json={"token": "ok"}),
            ],
        )

        token = client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)

        assert token == "ok"
        assert route.call_count == 3

    @respx.mock
    def test_basic_auth_raises_after_max_retries(self, client: CosiumClient):
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(500),
        )
        with pytest.raises(httpx.HTTPStatusError):
            client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)

    def test_authenticate_requires_credentials(self, client: CosiumClient, monkeypatch):
        """Sans tenant/login/password ni cookie mode ni OIDC → ValueError."""
        monkeypatch.setattr("app.integrations.cosium.client.settings.cosium_access_token", "")
        monkeypatch.setattr("app.integrations.cosium.client.settings.cosium_device_credential", "")
        monkeypatch.setattr("app.integrations.cosium.client.settings.cosium_oidc_token_url", "")
        with pytest.raises(ValueError, match="credentials not configured"):
            client.authenticate(tenant="", login="", password="")


class TestGet:
    @respx.mock
    def test_get_requires_authentication(self, client: CosiumClient):
        with pytest.raises(RuntimeError, match="Not authenticated"):
            client.get("/customers")

    @respx.mock
    def test_get_sends_authorization_header(self, client: CosiumClient):
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "tok-abc"}),
        )
        route = respx.get(f"{BASE}/{TENANT}/api/customers").mock(
            return_value=httpx.Response(200, json={"_embedded": {"customers": []}}),
        )

        client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        client.get("/customers")

        sent = route.calls.last.request
        assert sent.headers["Authorization"] == "AccessToken tok-abc"
        assert sent.headers["Accept"] == "application/hal+json"

    @respx.mock
    def test_get_retries_once_on_error(self, client: CosiumClient):
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "t"}),
        )
        route = respx.get(f"{BASE}/{TENANT}/api/customers").mock(
            side_effect=[
                httpx.Response(503),
                httpx.Response(200, json={"ok": True}),
            ],
        )

        client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        data = client.get("/customers")

        assert data == {"ok": True}
        assert route.call_count == 2

    @respx.mock
    def test_get_raises_after_retry_exhausted(self, client: CosiumClient):
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "t"}),
        )
        respx.get(f"{BASE}/{TENANT}/api/customers").mock(
            return_value=httpx.Response(500),
        )

        client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        with pytest.raises(httpx.HTTPStatusError):
            client.get("/customers")


class TestPagination:
    @respx.mock
    def test_paginate_hal_multi_pages(self, client: CosiumClient):
        """Format HAL : _embedded.customers[] + page.totalPages."""
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "t"}),
        )
        respx.get(f"{BASE}/{TENANT}/api/customers", params={"page_number": 0, "page_size": 2}).mock(
            return_value=httpx.Response(200, json={
                "_embedded": {"customers": [{"id": 1}, {"id": 2}]},
                "page": {"totalPages": 2},
            }),
        )
        respx.get(f"{BASE}/{TENANT}/api/customers", params={"page_number": 1, "page_size": 2}).mock(
            return_value=httpx.Response(200, json={
                "_embedded": {"customers": [{"id": 3}]},
                "page": {"totalPages": 2},
            }),
        )

        client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        items = client.get_paginated("/customers", page_size=2, max_pages=5)

        assert len(items) == 3
        assert [i["id"] for i in items] == [1, 2, 3]

    @respx.mock
    def test_paginate_spring_data_format(self, client: CosiumClient):
        """Format Spring Data : content[] + totalPages top-level."""
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "t"}),
        )
        respx.get(f"{BASE}/{TENANT}/api/invoices").mock(
            return_value=httpx.Response(200, json={
                "content": [{"id": "INV1"}, {"id": "INV2"}],
                "totalPages": 1,
            }),
        )

        client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        items = client.get_paginated("/invoices", page_size=50, max_pages=5)

        assert len(items) == 2
        assert items[0]["id"] == "INV1"

    @respx.mock
    def test_paginate_stops_on_empty_page(self, client: CosiumClient):
        """Une page vide stoppe la boucle, même sans totalPages."""
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "t"}),
        )
        respx.get(f"{BASE}/{TENANT}/api/products").mock(
            return_value=httpx.Response(200, json={"_embedded": {}}),
        )

        client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        items = client.get_paginated("/products", max_pages=10)

        assert items == []


class TestTokenRefresh:
    @respx.mock
    def test_token_refresh_after_expiry(self, client: CosiumClient):
        """Au-delà de 25 min, le client re-auth avant le prochain GET."""
        auth_route = respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "new-tok"}),
        )
        respx.get(f"{BASE}/{TENANT}/api/customers").mock(
            return_value=httpx.Response(200, json={"ok": True}),
        )

        client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        # Simule un token de 30 min (au-delà des 25 min)
        client._authenticated_at = time.time() - (30 * 60)

        client.get("/customers")

        # Authentification appelée 2 fois : initial + refresh
        assert auth_route.call_count == 2


class TestGetRaw:
    @respx.mock
    def test_get_raw_returns_bytes(self, client: CosiumClient):
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "t"}),
        )
        pdf_bytes = b"%PDF-1.7\nfake content"
        respx.get(f"{BASE}/{TENANT}/api/documents/42/download").mock(
            return_value=httpx.Response(200, content=pdf_bytes),
        )

        client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        content = client.get_raw("/documents/42/download")

        assert content == pdf_bytes


class TestSecurityRules:
    """CosiumClient ne doit JAMAIS exposer put/delete/patch et post sauf auth."""

    def test_no_put_method(self, client: CosiumClient):
        assert not hasattr(client, "put")

    def test_no_delete_method(self, client: CosiumClient):
        assert not hasattr(client, "delete")

    def test_no_patch_method(self, client: CosiumClient):
        assert not hasattr(client, "patch")

    def test_no_generic_request_method(self, client: CosiumClient):
        """Pas de `request()` générique qui accepterait n'importe quelle méthode."""
        assert not hasattr(client, "request")

    def test_no_post_method_beyond_authenticate(self, client: CosiumClient):
        """`post()` public n'existe pas — seul `authenticate()` fait un POST interne."""
        assert not hasattr(client, "post")

    @respx.mock
    def test_only_get_and_auth_endpoints_called(self, client: CosiumClient):
        """Vérifie qu'aucune méthode du client n'émet PUT/DELETE/PATCH."""
        respx.post(f"{BASE}/{TENANT}/api/authenticate/basic").mock(
            return_value=httpx.Response(200, json={"token": "t"}),
        )
        respx.get(f"{BASE}/{TENANT}/api/customers").mock(
            return_value=httpx.Response(200, json={"_embedded": {"customers": []}}),
        )

        client.authenticate(tenant=TENANT, login=LOGIN, password=PASSWORD)
        client.get("/customers")

        methods_called = [call.request.method for call in respx.calls]
        assert set(methods_called) <= {"POST", "GET"}
        # Le seul POST doit être auth
        for call in respx.calls:
            if call.request.method == "POST":
                assert "authenticate/basic" in str(call.request.url)
