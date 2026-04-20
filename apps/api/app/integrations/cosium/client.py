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

    Supporte 3 modes d'authentification :
    1. Cookie mode : access_token + device-credential cookies (navigateur)
    2. OIDC mode : Keycloak password grant → Bearer token
    3. Basic mode : POST /authenticate/basic → AccessToken header

    Aucune methode put/post/delete/patch n'existe ni ne sera ajoutee.
    """

    def __init__(self) -> None:
        self.base_url = settings.cosium_base_url
        self.tenant = settings.cosium_tenant
        self.token: str | None = None
        self._token_type: str = "AccessToken"
        self._auth_mode: str = "none"  # "cookie", "oidc", "basic"
        self._cookies: dict[str, str] = {}
        self._authenticated_at: float | None = None
        self._auth_tenant: str | None = None
        self._auth_login: str | None = None
        self._auth_password: str | None = None
        self._client = httpx.Client(timeout=60.0)

    def _ensure_token_valid(self) -> None:
        """Re-authenticate if token is older than 25 minutes (not for cookie mode)."""
        if self._auth_mode == "cookie":
            return  # Cookie tokens are long-lived
        if self._authenticated_at and (time.time() - self._authenticated_at > 25 * 60):
            logger.info("cosium_token_refresh", reason="expired")
            self.authenticate(
                tenant=self._auth_tenant,
                login=self._auth_login,
                password=self._auth_password,
            )

    def authenticate(self, tenant: str | None = None, login: str | None = None, password: str | None = None) -> str:
        """Authenticate to Cosium. Auto-detects the best mode."""
        t = tenant or self.tenant
        l = login or settings.cosium_login
        p = password or settings.cosium_password

        # Store credentials for token refresh
        self._auth_tenant = t
        self._auth_login = l
        self._auth_password = p

        # Mode 1: Cookie-based auth (device-credential + access_token from .env)
        if settings.cosium_access_token and settings.cosium_device_credential:
            return self._authenticate_cookie()

        if not t or not l or not p:
            raise ValueError("Cosium credentials not configured (COSIUM_TENANT, COSIUM_LOGIN, COSIUM_PASSWORD)")

        # Mode 2: OIDC (Keycloak)
        if settings.cosium_oidc_token_url:
            return self._authenticate_oidc(l, p)

        # Mode 3: Basic auth (legacy)
        return self._authenticate_basic(t, l, p)

    def _authenticate_cookie(self, access_token: str | None = None, device_credential: str | None = None) -> str:
        """Cookie-based auth using device-credential + access_token.

        Accepts explicit values (from tenant DB) or falls back to settings.
        """
        at = access_token or settings.cosium_access_token
        dc = device_credential or settings.cosium_device_credential
        self.token = at
        self._cookies = {
            "access_token": at,
            "device-credential": dc,
        }
        self._auth_mode = "cookie"
        self._authenticated_at = time.time()
        logger.info("cosium_cookie_authenticated", tenant=self.tenant)
        return self.token

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
                self._auth_mode = "oidc"
                self._authenticated_at = time.time()
                logger.info("cosium_oidc_authenticated")
                return self.token
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning("cosium_oidc_retry", attempt=attempt + 1, delay=delay, error=str(e), error_type=type(e).__name__)
                    time.sleep(delay)
                else:
                    logger.error("cosium_oidc_failed", attempts=MAX_RETRIES, error=str(e), error_type=type(e).__name__)
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
                self._auth_mode = "basic"
                self.tenant = tenant
                self._authenticated_at = time.time()
                logger.info("cosium_authenticated", tenant=tenant)
                return self.token
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.warning("cosium_auth_retry", attempt=attempt + 1, delay=delay, error=str(e), error_type=type(e).__name__)
                    time.sleep(delay)
                else:
                    logger.error("cosium_auth_failed", attempts=MAX_RETRIES, error=str(e), error_type=type(e).__name__)
                    raise
        raise RuntimeError("Authentication failed after retries")

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        """GET generique — SEULE methode de lecture vers Cosium."""
        if not self.token and self._auth_mode != "cookie":
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        self._ensure_token_valid()

        url = f"{self.base_url}/{self.tenant}/api{endpoint}"

        # Build headers based on auth mode
        headers: dict[str, str] = {"Accept": "application/hal+json"}
        cookies: dict[str, str] = {}

        if self._auth_mode == "cookie":
            cookies = self._cookies.copy()
        else:
            headers["Authorization"] = f"{self._token_type} {self.token}"

        for attempt in range(2):
            try:
                response = self._client.get(url, params=params, headers=headers, cookies=cookies, timeout=30)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == 0:
                    logger.warning("cosium_get_retry", endpoint=endpoint, error=str(e), error_type=type(e).__name__)
                    time.sleep(1)
                else:
                    logger.error("cosium_get_failed", endpoint=endpoint, error=str(e), error_type=type(e).__name__)
                    raise

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

            # Extract items — handles both HAL and Spring Data formats:
            # HAL: { "_embedded": { "customers": [...] } }
            # Spring+HAL: { "_embedded": { "content": [...] } }
            # Spring: { "content": [...] }
            items: list[dict] = []
            embedded = data.get("_embedded", {})
            if isinstance(embedded, dict):
                # Try _embedded.content first (Spring Data + HAL)
                if "content" in embedded:
                    items = embedded["content"]
                else:
                    # Try specific collection keys (pure HAL)
                    for key in ("customers", "invoices", "invoicedItems", "products", "paymentTypes", "items"):
                        if key in embedded:
                            raw = embedded[key]
                            items = raw if isinstance(raw, list) else [raw]
                            break
            # Fallback: top-level content (Spring Data without HAL)
            if not items and "content" in data:
                items = data["content"]

            if not items:
                break

            all_items.extend(items)

            # Check pagination — supports both formats:
            # HAL/customers: { "page": { "totalPages": N } }
            # Spring/invoices: { "totalPages": N } (top-level)
            page_info = data.get("page", {})
            total_pages = page_info.get("totalPages") or data.get("totalPages", 1)
            if page + 1 >= total_pages:
                break

            logger.debug(
                "cosium_paginate", endpoint=endpoint, page=page + 1, total_pages=total_pages, fetched=len(all_items)
            )

            # Rate limit: pause between pages to avoid Cosium throttling
            # Only sleep when fetching multiple pages (single-page requests skip the delay)
            if max_pages > 1:
                time.sleep(0.1)

        return all_items

    def get_raw(self, endpoint: str, params: dict | None = None) -> bytes:
        """GET qui retourne le contenu brut (bytes) — pour telechargement de documents."""
        if not self.token and self._auth_mode != "cookie":
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        self._ensure_token_valid()

        url = f"{self.base_url}/{self.tenant}/api{endpoint}"

        headers: dict[str, str] = {"Accept": "*/*"}
        cookies: dict[str, str] = {}

        if self._auth_mode == "cookie":
            cookies = self._cookies.copy()
        else:
            headers["Authorization"] = f"{self._token_type} {self.token}"

        for attempt in range(2):
            try:
                response = self._client.get(url, params=params, headers=headers, cookies=cookies, timeout=60)
                response.raise_for_status()
                return response.content
            except Exception as e:
                if attempt == 0:
                    logger.warning("cosium_get_raw_retry", endpoint=endpoint, error=str(e), error_type=type(e).__name__)
                    time.sleep(1)
                else:
                    logger.error("cosium_get_raw_failed", endpoint=endpoint, error=str(e), error_type=type(e).__name__)
                    raise

        raise RuntimeError("GET raw request failed after retries")

    # ⛔ INTERDIT : Aucune methode ci-dessous ne sera implementee
    # def put(...) -> INTERDIT
    # def post(...) -> INTERDIT (sauf authenticate ci-dessus)
    # def delete(...) -> INTERDIT
    # def patch(...) -> INTERDIT
    # def request(...) -> INTERDIT (methode generique)
