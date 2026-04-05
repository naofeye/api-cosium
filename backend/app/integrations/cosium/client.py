"""
CosiumClient — LECTURE SEULE.

REGLES DE SECURITE ABSOLUES :
- Seul POST autorise : /authenticate/basic (obtenir un token)
- Seules requetes de lecture : GET
- INTERDIT : put(), post() (sauf auth), delete(), patch()
- INTERDIT : toute methode generique avec methode HTTP variable
- La synchronisation est UNIDIRECTIONNELLE : Cosium -> OptiFlow
"""

import time

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("cosium_client")

MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # seconds


class CosiumClient:
    """Client API Cosium — LECTURE SEULE.

    Ce client n'expose que deux methodes :
    - authenticate() : POST /authenticate/basic (seul POST autorise)
    - get() : GET generique pour la lecture de donnees

    Aucune methode put/post/delete/patch n'existe ni ne sera ajoutee.
    """

    def __init__(self) -> None:
        self.base_url = settings.cosium_base_url
        self.tenant = settings.cosium_tenant
        self.token: str | None = None
        self._token_type: str = "AccessToken"
        self._authenticated_at: float | None = None
        self._auth_tenant: str | None = None
        self._auth_login: str | None = None
        self._auth_password: str | None = None
        self._client = httpx.Client(timeout=30.0)

    def _ensure_token_valid(self) -> None:
        """Re-authenticate if token is older than 25 minutes."""
        if self._authenticated_at and (time.time() - self._authenticated_at > 25 * 60):
            logger.info("cosium_token_refresh", reason="expired")
            self.authenticate(
                tenant=self._auth_tenant,
                login=self._auth_login,
                password=self._auth_password,
            )

    def authenticate(self, tenant: str | None = None, login: str | None = None, password: str | None = None) -> str:
        """Authenticate to Cosium via OIDC or basic, depending on config."""
        t = tenant or self.tenant
        l = login or settings.cosium_login
        p = password or settings.cosium_password

        if not t or not l or not p:
            raise ValueError("Cosium credentials not configured (COSIUM_TENANT, COSIUM_LOGIN, COSIUM_PASSWORD)")

        # Store credentials for token refresh
        self._auth_tenant = t
        self._auth_login = l
        self._auth_password = p

        if settings.cosium_oidc_token_url:
            return self._authenticate_oidc(l, p)
        return self._authenticate_basic(t, l, p)

    def _authenticate_oidc(self, login: str, password: str) -> str:
        """OIDC password grant via Keycloak."""
        url = settings.cosium_oidc_token_url

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.post(
                    url,
                    data={
                        "grant_type": "password",
                        "client_id": settings.cosium_oidc_client_id,
                        "username": login,
                        "password": password,
                    },
                )
                response.raise_for_status()
                data = response.json()
                self.token = data["access_token"]
                self._token_type = "Bearer"
                self._authenticated_at = time.time()
                logger.info("cosium_oidc_authenticated")
                return self.token
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning("cosium_oidc_retry", attempt=attempt + 1, delay=delay, error=str(e))
                    time.sleep(delay)
                else:
                    logger.error("cosium_oidc_failed", attempts=MAX_RETRIES, error=str(e))
                    raise

        raise RuntimeError("OIDC auth failed after retries")

    def _authenticate_basic(self, tenant: str, login: str, password: str) -> str:
        """Legacy /authenticate/basic endpoint — SEUL POST autorise vers Cosium."""
        url = f"{self.base_url}/{tenant}/api/authenticate/basic"

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.post(
                    url,
                    json={"login": login, "password": password, "site": tenant},
                    headers={"Accept": "application/json", "Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                self.token = data.get("token") or data.get("access_token") or data.get("accessToken", "")
                self._token_type = "AccessToken"
                self.tenant = tenant
                self._authenticated_at = time.time()
                logger.info("cosium_authenticated", tenant=tenant)
                return self.token
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning("cosium_auth_retry", attempt=attempt + 1, delay=delay, error=str(e))
                    time.sleep(delay)
                else:
                    logger.error("cosium_auth_failed", attempts=MAX_RETRIES, error=str(e))
                    raise

        raise RuntimeError("Authentication failed after retries")

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        """GET generique — SEULE methode de lecture vers Cosium.

        Args:
            endpoint: chemin relatif (ex: "/customers", "/invoices")
            params: parametres de requete (pagination, filtres)

        Returns:
            Reponse JSON (format HAL)
        """
        if not self.token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        self._ensure_token_valid()

        url = f"{self.base_url}/{self.tenant}/api{endpoint}"
        headers = {
            "Authorization": f"{self._token_type} {self.token}",
            "Accept": "application/hal+json",
        }

        for attempt in range(2):
            try:
                response = self._client.get(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == 0:
                    logger.warning("cosium_get_retry", endpoint=endpoint, error=str(e))
                    time.sleep(1)
                else:
                    logger.error("cosium_get_failed", endpoint=endpoint, error=str(e))
                    raise

        # Unreachable, but satisfies type checker
        raise RuntimeError("GET request failed after retries")

    def get_paginated(
        self, endpoint: str, params: dict | None = None, page_size: int = 100, max_pages: int = 50
    ) -> list[dict]:
        """GET avec pagination automatique. Retourne tous les items."""
        all_items: list[dict] = []
        p = dict(params or {})
        p["page_size"] = page_size

        for page in range(max_pages):
            p["page_number"] = page
            data = self.get(endpoint, p)

            # HAL format: items can be in _embedded or directly
            embedded = data.get("_embedded", data)
            if isinstance(embedded, dict):
                # Try common HAL collection keys
                for key in ("customers", "invoices", "invoicedItems", "products", "paymentTypes", "items", "content"):
                    if key in embedded:
                        items = embedded[key]
                        all_items.extend(items if isinstance(items, list) else [items])
                        break
                else:
                    all_items.append(data)
                    break
            elif isinstance(embedded, list):
                all_items.extend(embedded)

            # Check if there are more pages
            page_info = data.get("page", {})
            total_pages = page_info.get("totalPages", 1)
            if page + 1 >= total_pages:
                break

        return all_items

    # ⛔ INTERDIT : Aucune methode ci-dessous ne sera implementee
    # def put(...) -> INTERDIT
    # def post(...) -> INTERDIT (sauf authenticate ci-dessus)
    # def delete(...) -> INTERDIT
    # def patch(...) -> INTERDIT
    # def request(...) -> INTERDIT (methode generique)


cosium_client = CosiumClient()
