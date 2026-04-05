#!/usr/bin/env python3
"""Test de connexion Cosium standalone.
Usage: docker compose exec api python scripts/test_cosium.py
"""
import sys

sys.path.insert(0, "/app")

from app.core.config import settings
from app.integrations.cosium.client import CosiumClient


def main() -> None:
    print("=" * 50)
    print("  Test de connexion Cosium")
    print("=" * 50)

    print(f"\nServeur: {settings.cosium_base_url}")
    print(f"Tenant:  {settings.cosium_tenant}")
    print(f"Login:   {settings.cosium_login}")
    print(f"OIDC:    {'Oui' if settings.cosium_oidc_token_url else 'Non (basic)'}")

    client = CosiumClient()

    print("\n--- Authentification ---")
    try:
        token = client.authenticate()
        print(f"OK ! Token obtenu ({len(token)} chars)")
    except Exception as e:
        print(f"ECHEC : {e}")
        print("\nVerifiez vos credentials dans .env")
        return

    print("\n--- Clients ---")
    try:
        data = client.get("/customers", {"page_number": 0, "page_size": 5})
        page = data.get("page", {})
        total = page.get("totalElements", "?")
        print(f"Total: {total} clients")
        embedded = data.get("_embedded", data)
        for c in embedded.get("customers", [])[:5]:
            print(f"  {c.get('firstName', '')} {c.get('lastName', '')} (id={c.get('id')})")
    except Exception as e:
        print(f"Erreur: {e}")

    print("\n--- Factures ---")
    try:
        data = client.get("/invoices", {"page_number": 0, "page_size": 3})
        page = data.get("page", {})
        print(f"Total: {page.get('totalElements', '?')} factures")
    except Exception as e:
        print(f"Erreur: {e}")

    print("\n" + "=" * 50)
    print("  Test termine")
    print("=" * 50)


if __name__ == "__main__":
    main()
