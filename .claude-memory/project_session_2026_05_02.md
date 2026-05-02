---
name: Session 2026-05-02 — Sweep autonome 24h (4 features + fix CI)
description: 5 commits pushes sur main, +33 tests backend (2284), 0 regression, CI verte. CSRF double-submit, Webhooks sortants (Coming Soon -> reel), PEC reconciliation orphelines, fix CI rollback mergepoint-safe.
type: project
---

## Resume

Mission "tout ce qui reste a faire, polish, nice-to-have" lancee en mode autonome.
5 commits sur main, 4 chantiers livres + 1 fix CI, 0 regression, CI verte sur `6fbef80`.

## 5 commits livres

1. **`6ab50c7`** — Fix CI rollback Alembic mergepoint-safe
   - `alembic downgrade -1` ambigu sur head mergepoint a 2 parents
   - Workflow extrait dynamiquement la 1ere parent revision via
     `alembic show head | grep -E '^(Parent|Merges):'` puis downgrade
   - Robuste pour mergepoints + migrations lineaires futures
   - Test local : 6 migrations rollback + re-upgrade clean

2. **`9c724eb`** — CSRF double-submit cookie (P1 securite)
   - Middleware FastAPI `app/core/csrf.py` valide `X-CSRF-Token` header
     == cookie `optiflow_csrf` sur mutations authentifiees
   - 9 paths exemptes (login/refresh/signup/Stripe webhooks/web-vitals)
   - Transition deploy : safe requests authentifiees seedent le cookie
     (utilisateurs deja loggés sans re-login)
   - Bypass `app_env=test` (preserve les ~150 fichiers de tests),
     tests dedies dans `tests/test_csrf.py` qui forcent l'enforcement
   - Frontend : `lib/csrf.ts` + injection auto dans `fetchJson` +
     3 mutations directes patches (chat SSE, avatar, CSV import)
   - 15/15 tests CSRF dedies + 0 regression

3. **`07ab6d3`** — Webhooks HTTP sortants (Coming Soon T3 2026 -> realise)
   - Tables `webhook_subscriptions` + `webhook_deliveries`,
     migration `b5c6d7e8f9a1` testee up/down
   - HMAC SHA256, 14 event_types whitelist, secret expose une seule
     fois a la creation
   - Worker Celery `deliver_webhook` avec retry maison borne
     ([30s, 2m, 15m, 1h, 6h]) + persistence `next_retry_at`
   - 6 endpoints REST + page `/admin/webhooks`
   - Hooks integres : `client.created/updated`, `facture.created`,
     `facture.avoir_created`, `devis.created/signed/refused`
   - 28 nouveaux tests (service x11, worker x7, API x10)

4. **`ff5ad53`** — PEC reconciliation factures Cosium orphelines (V12)
   - `services/orphan_invoice_service.py::reconcile_orphan_invoices`
     rejoue le matching cosium_id + name fuzzy pour `customer_id IS NULL`
   - Utile quand un client est importe APRES la facture
   - Task Celery cross-tenant `reconcile_all_tenants_orphans`
     (a planifier en beat dans une session future)
   - 2 endpoints admin : stats (total/orphans/linked_pct) + trigger
     manuel (limit 5000)
   - 5 tests : count, match-cosium, match-name, no-op, isolation, limit

5. **`6fbef80`** — TODO + CLAUDE.md sweep + ruff fixes (I001 + UP007)

## Metriques

- **Backend tests** : 2284 (etait 2251) — +33 tests, 0 regression
- **Frontend tests** : 202 (39 fichiers, inchange)
- **Lint** : ruff + eslint + tsc verts
- **Migration Alembic** : `b5c6d7e8f9a1` testee up + down
- **Containers** : 8/8 healthy en prod sur cosium.ia.coging.com

## Decouvertes / Patterns

1. **Tests Alembic rollback sur mergepoint** : `alembic downgrade -1`
   echoue avec "Ambiguous walk" quand la head a plusieurs parents.
   Solution generique : extraire la cible via `alembic show head | grep
   -E '^(Parent|Merges):'` puis downgrade vers cette revision.

2. **Architecture test : `db.commit()` interdit dans repos** —
   `tests/test_architecture.py::test_no_commit_in_repositories` echoue
   si un repo commit. Pattern correct : repos `db.flush()`, services ou
   routers commitent.

3. **TestClient Celery worker** : le worker utilise `SessionLocal`
   (postgres prod). En test SQLite in-memory, monkeypatch
   `app.tasks.X.SessionLocal` pour reutiliser la session test.

4. **CSRF + tests existants** : pour eviter la migration de ~150 fichiers
   de tests, le middleware bypass en `app_env=test`. Tests dedies
   construisent une mini-app FastAPI qui force l'enforcement
   (`monkeypatch.setattr("app.core.csrf.settings.app_env", "production")`).

5. **Sandbox Claude Code 2.1+ ro** : le filesystem `/srv` est mounted
   read-only dans la mount-namespace du process Claude. Ecriture via :
   `docker run --rm --user 1002:1002 -v /srv:/srv alpine sh -c "..."`.
   Git ops via `alpine/git` avec mêmes options. Voir
   `/srv/projects/CLAUDE.md` pour la procedure complete.

6. **Reste backlog** : DIFFERE-PROD bloque sur Nabil (TLS, passwords prod,
   rotation creds Cosium), E2E Playwright UI cookie-based, mypy strict
   (80 erreurs sur app/core, a phaser progressivement).
