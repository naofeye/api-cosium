# ADR-0008 — PEC orphan invoice reconciliation strategy

**Status** : Accepted (2026-05-02)
**Context** : V12 PEC backlog item #1 — Liaison 100% factures via
`_links.customer.href`

## Contexte

Le sync ERP Cosium peut laisser des factures sans `customer_id` dans la
table `cosium_invoices` :
- Sync incremental : la facture est creee avant que le client ne soit
  importe (race condition entre sync customers et sync invoices)
- Customer Cosium absent au moment du sync (createur freelance)
- `customerName` ne match pas notre `Customer` en BDD via fuzzy name

Sans liaison, les factures orphelines sont :
- Invisibles dans les vues client (Client 360, factures du dossier)
- Manquees par les relances automatiques
- Comptees correctement dans les totaux financiers (analytics tenant)
  mais pas attribuables a un client donne pour les actions metier

Ratio observe sur tenants demo : 5-15% d'orphelines apres premiere sync,
puis converge vers 1-2% avec re-runs.

## Decision

**Strategie en 2 temps** :

### 1. Match au sync (existant)

L'adapter Cosium extrait `customer_cosium_id` depuis `_links.customer.href`
(adapter.py:78-86) en fallback de `customerId` direct. Le service
`erp_sync_invoices` matche ensuite via :
1. `customer_cosium_id_map[cosium_id]` (lookup direct)
2. `_match_customer_by_name(customer_name, name_map)` (fuzzy)

### 2. Reconciliation periodique (nouveau)

Service `orphan_invoice_service.reconcile_orphan_invoices(db, tenant_id)`
**rejoue le matching** pour les factures `customer_id IS NULL`, en
beneficiant des nouveaux clients importes entre-temps.

Strategie identique au sync : cosium_id direct -> name fuzzy.

Trigger :
- **Celery beat** quotidien 4h15 UTC (`reconcile-orphan-invoices`),
  avant la sync 6h UTC : matche les orphelines sur les clients
  importes lors de la sync precedente.
- **Endpoint admin** `POST /api/v1/admin/cosium/reconcile-orphans` :
  trigger manuel, limite 5000 factures par appel synchrone (UI).
- **Stats endpoint** `GET /api/v1/admin/cosium/orphan-invoices` :
  total / orphelines / pourcentage lie.

## Alternatives envisagees

**A. Forcer la sync customer avant chaque sync invoice**
- Pro : simple, plus de race
- Contra : double duree de sync (les customers peuvent etre 100k+),
  pas resilient aux echecs partiels

**B. Stocker l'orphelinage et alerter**
- Pro : visibilite immediate
- Contra : ne resout pas le probleme, reporte aux opticiens manuellement

**C. Bulk re-sync nocturne**
- Pro : pas de logique speciale
- Contra : trop intrusif (sync complete x2), penalise sur grosses bases

**Choisi : C en mode incremental ciblé (B+C combine)**, optimise pour ne
toucher que les orphelines.

## Implementation

- `services/orphan_invoice_service.py` : `count_orphan_invoices` +
  `reconcile_orphan_invoices(limit=...)`
- `tasks/orphan_invoice_task.py` : Celery `reconcile_all_tenants_orphans`
  cross-tenant, retries=2, time_limit=1800s
- `routers/admin_cosium.py` : 2 endpoints admin
- `tests/test_orphan_invoice.py` : 5 tests (count, match-cosium-id,
  match-name, no-op, isolation tenant, limit)

## Consequences

**Positives** :
- Liaison customer_id converge vers 100% sur 1-2 jours apres premier import
- Observable via `/admin/cosium/orphan-invoices` et dashboard Grafana
- Pas de duplication de logique : reuse `_match_customer_by_name` existant
- Sans charge additionnelle sur Cosium (matching purement local)

**Negatives** :
- Latence : factures orphelines visibles sans client_id pendant 24h max
- Si fuzzy match faux-positif au sync, le fix manuel necessite encore
  un PATCH `cosium_invoices.customer_id = NULL` pour rejouer
- Cron 4h15 UTC : si pause maintenance, accumulation jusqu'au lendemain

## Suivi

- **Metrique** : ratio orphelines a surveiller dans Grafana business.json
  (a ajouter, item futur)
- **Alerte** : si > 10% orphelines apres reconcile, investiguer
  `customerName` patterns inhabituels Cosium

## References

- TODO.md PEC V12 Intelligence
- `apps/api/app/services/orphan_invoice_service.py`
- `apps/api/app/tasks/orphan_invoice_task.py`
- Beat schedule : `apps/api/app/tasks/__init__.py`
- Tests : `apps/api/tests/test_orphan_invoice.py`
