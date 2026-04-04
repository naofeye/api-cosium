# Audit Securite Cosium — OptiFlow AI

**Date** : 2026-04-04
**Auditeur** : Claude Code (automatise)
**Resultat** : CONFORME

## Regle

> OptiFlow ne doit JAMAIS modifier, creer ou supprimer quoi que ce soit dans Cosium.
> La synchronisation est UNIDIRECTIONNELLE : Cosium → OptiFlow uniquement.

## Fichiers audites

| Fichier | Resultat |
|---------|----------|
| `integrations/cosium/client.py` | CONFORME |
| `integrations/cosium/cosium_connector.py` | CONFORME |
| `integrations/cosium/adapter.py` | CONFORME (mapping pur, pas d'appel HTTP) |
| `services/erp_sync_service.py` | CONFORME (lecture seule) |
| `services/sync_service.py` | CONFORME (lecture seule) |

## Methodes HTTP vers Cosium

| Methode | Presente | Autorisee | Detail |
|---------|----------|-----------|--------|
| POST `/authenticate/basic` | OUI | OUI | Seul POST, dans `CosiumClient.authenticate()` |
| GET `/*` | OUI | OUI | `CosiumClient.get()` et `get_paginated()` |
| PUT | NON | NON | Aucune methode `put()` |
| POST (hors auth) | NON | NON | Aucune methode `post()` generique |
| DELETE | NON | NON | Aucune methode `delete()` |
| PATCH | NON | NON | Aucune methode `patch()` |
| `request()` generique | NON | NON | Aucune methode generique |
| `send()` generique | NON | NON | Aucune methode generique |

## Methodes publiques du CosiumClient

- `authenticate(tenant, login, password) -> str` — seul POST autorise
- `get(endpoint, params) -> dict` — GET uniquement
- `get_paginated(endpoint, params, max_pages) -> list` — GET avec pagination

**Aucune autre methode publique.**

## Methodes du CosiumConnector

- `authenticate(base_url, tenant, login, password) -> str`
- `get_customers(page, page_size) -> list[ERPCustomer]`
- `get_invoices(page, page_size) -> list[ERPInvoice]`
- `get_invoiced_items(invoice_erp_id) -> list[dict]`
- `get_products(page, page_size) -> list[ERPProduct]`
- `get_product_stock(product_erp_id) -> list[ERPStock]`
- `get_payment_types() -> list[ERPPaymentType]`

**Toutes en lecture seule (GET).**

## Tests de securite automatises (10 tests)

Fichier: `tests/test_cosium.py`

1. `test_cosium_client_has_no_put_method` — pas de `put()`
2. `test_cosium_client_has_no_delete_method` — pas de `delete()`
3. `test_cosium_client_has_no_patch_method` — pas de `patch()`
4. `test_cosium_client_has_no_generic_post` — pas de `post()` generique
5. `test_cosium_client_has_no_request_method` — pas de `request()`
6. `test_cosium_client_has_no_send_method` — pas de `send()`
7. `test_cosium_client_only_allowed_methods` — seules `authenticate`, `get`, `get_paginated`
8. `test_cosium_client_authenticate_uses_only_post` — source code inspection
9. `test_cosium_client_get_uses_only_get` — source code inspection
10. Scan grep sur tout le dossier `integrations/cosium/` — zero PUT/POST(hors auth)/DELETE/PATCH

## Conclusion

Le code OptiFlow respecte strictement la regle de lecture seule vers Cosium.
Aucune ecriture n'est possible vers l'API Cosium depuis le code applicatif.
