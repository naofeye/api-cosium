"""Strategie de recuperation exhaustive des clients Cosium.

Cosium impose une limite d'offset ~50. On contourne par filtrage loose_last_name
lettre par lettre, puis prefixes non-alpha, puis tri, puis include_hidden.
"""
from __future__ import annotations

import string
from typing import Any, Protocol

from app.core.logging import get_logger
from app.integrations.cosium.adapter import cosium_customer_to_optiflow
from app.integrations.erp_models import ERPCustomer

logger = get_logger("cosium.customer_fetcher")

_NON_ALPHA_PREFIXES = (
    list("0123456789") + ["-", "'", ".", " "] + list("ÀÂÄÉÈÊËÏÎÔÙÛÜÇŒÆ") + list("àâäéèêëïîôùûüçœæ")
)


class _CosiumHTTP(Protocol):
    def get(self, endpoint: str, params: dict | None = None) -> dict: ...
    def get_paginated(
        self, endpoint: str, params: dict | None = None, page_size: int = 100, max_pages: int = 50
    ) -> list[dict]: ...


def _absorb(batch: list[dict], seen: set[str], items: list[dict]) -> None:
    for raw in batch:
        cid = str(raw.get("id", ""))
        if cid and cid not in seen:
            seen.add(cid)
            items.append(raw)


def _fetch_by_prefix(client: _CosiumHTTP, prefix: str, seen: set[str], items: list[dict]) -> None:
    data = client.get("/customers", {"loose_last_name": prefix, "page_number": 0, "page_size": 1})
    total = data.get("page", {}).get("totalElements", 0)
    if total == 0:
        return
    if total <= 50:
        batch = client.get_paginated(
            "/customers", params={"loose_last_name": prefix}, page_size=50, max_pages=1
        )
    else:
        batch = []
        for second in string.ascii_uppercase:
            sub = client.get_paginated(
                "/customers", params={"loose_last_name": f"{prefix}{second}"}, page_size=50, max_pages=1
            )
            batch.extend(sub)
    _absorb(batch, seen, items)


def fetch_all_customers(client: _CosiumHTTP) -> list[ERPCustomer]:
    """Parcours exhaustif Cosium → liste ERPCustomer mappee."""
    seen_ids: set[str] = set()
    items: list[dict[str, Any]] = []

    # 1. Sans filtre (50 premiers)
    _absorb(client.get_paginated("/customers", page_size=50, max_pages=1), seen_ids, items)

    # 2. Lettre par lettre A-Z
    for letter in string.ascii_uppercase:
        _fetch_by_prefix(client, letter, seen_ids, items)

    # 3. Prefixes non-alpha (chiffres, ponctuation, accents)
    for prefix in _NON_ALPHA_PREFIXES:
        try:
            _fetch_by_prefix(client, prefix, seen_ids, items)
        except Exception as exc:
            logger.warning("cosium_customer_prefix_failed", prefix=prefix, error=str(exc))

    # 4. Plusieurs tris pour rattraper
    for sort_param in ("lastName", "firstName", "id"):
        try:
            batch = client.get_paginated(
                "/customers", params={"sort": sort_param}, page_size=50, max_pages=5
            )
            _absorb(batch, seen_ids, items)
        except Exception as exc:
            logger.warning("cosium_customer_sort_failed", sort=sort_param, error=str(exc))

    # 5. Include hidden (clients inactifs)
    try:
        batch = client.get_paginated(
            "/customers", params={"include_hidden": "true"}, page_size=50, max_pages=5
        )
        _absorb(batch, seen_ids, items)
    except Exception as exc:
        logger.warning("cosium_customer_hidden_failed", error=str(exc))

    logger.info("cosium_customers_fetched", total_unique=len(items))

    customers: list[ERPCustomer] = []
    for raw in items:
        mapped = cosium_customer_to_optiflow(raw)
        if not mapped.get("last_name"):
            continue
        customers.append(
            ERPCustomer(
                erp_id=mapped.get("cosium_id", ""),
                first_name=mapped.get("first_name", ""),
                last_name=mapped.get("last_name", ""),
                birth_date=mapped.get("birth_date"),
                phone=mapped.get("phone"),
                email=mapped.get("email"),
                address=mapped.get("address"),
                city=mapped.get("city"),
                postal_code=mapped.get("postal_code"),
                social_security_number=mapped.get("social_security_number"),
                customer_number=mapped.get("customer_number"),
                street_number=mapped.get("street_number"),
                street_name=mapped.get("street_name"),
                mobile_phone_country=mapped.get("mobile_phone_country"),
                site_id=mapped.get("site_id"),
            )
        )
    return customers
