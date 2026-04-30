---
name: Session 2026-04-29 — Sweep audit Codex (P1+P2+P3) + openapi-typescript
description: 13 commits sur main, CI 3/3 verte. Sweep complet audit code-reviewer (3 P1 + 9 P2 + 5/7 P3). Ajout generation auto types frontend depuis OpenAPI. Audit RGPD bulk exports.
type: project
---

**Contexte** : continuation des sessions 2026-04-17/18/26/27/28/29 (V12 audit + posting). Session lancee suite a "fait un check du projet et dis moi ce quil reste a faire".

**Commits pousses sur `main`** (13, CI 3/3 verte sur `473de33`) :

1. `05e50a0` — fix E2E Playwright via `apiLoginAndInject` (contourne pressSequentially flakky React-hook-form en CI). 9/10 tests pass, 1 skip annote.
2. `d69293e` — nettoyage : interface-ia-net -> vps-net (post-decommission), 4 items TODO coches, retrait du seul `as any` (InstallPrompt iOS standalone).
3. `e834f21` — P1 tenant_id partout (ai_context_repo 5 fonctions) + P2 batch_operation_repo + extraction `push_service.py` (router faisait db.scalars/add/commit, viol charte).
4. `a76add0` — P1 N+1 action_item_service : 6 boucles `find_existing` -> 1 query pre-charge via nouveau `action_item_repo.list_pending_entity_ids`. 200+ -> ~10 queries pour gros tenants.
5. `ec292f5` — P1 taux_tva avoir partiel hardcode 20.0 -> derive de la facture originale (verres medicaux 5,5%, FEC coherent). P2 RBAC `extract_document` operator+ (cout Claude). P2 middleware Next : retire confiance au cookie `optiflow_authenticated` non-httpOnly. P3 `Literal["client", "mutuelle", "secu"]` + Path `^(email|sms|paper|phone)$`.
6. `10ea7f8` — P2 pagination `get_unsettled_reconciliations` cassee (bouclait 3 statuts en page=2 -> sautait 75 items au lieu de 25). Helper `get_reconciliations_by_statuses` UNE query. P3 `ai_renewal.generate_renewal_message` leve `NotFoundError` au lieu de `return ""` silencieux.
7. `31c5faa` — P2 N+1 `admin_user_service.list_users` 51 -> 1 query (JOIN). P2 calculs `Decimal` + `quantize(0.01, ROUND_HALF_UP)` dans `create_avoir` (regle comptable francaise, evite arrondis sur fractions repetees).
8. `70dfa3f` — P2 expose `devis.created_at` ISO dans client_360 + propage dans 3 types frontend. TabActivite : `d.created_at` au lieu de `new Date().toISOString()` -> timeline ordonnee chrono.
9. `cb46db4` — P3 ClientScoreCard skeleton loader + bandeau erreur (avant `return null` cachait tout). P3 SendDocumentEmailDialog deps fix. 4 composants `RSC-first` (FactureLignesTable, FacturePaymentsTable, CompletionBar, BatchItemsTable).
10. `22e96c8` — hotfix : audit_service.log_action json.dumps ne sait pas serialiser Decimal. Cast en float a la frontiere (calcul interne reste Decimal).
11. `51e049e` — feature openapi-typescript : `npm run generate:api-types` genere `src/types/api.ts` (gitignore) depuis `apps/api/docs/openapi.json`. Doc CONTRIBUTING.md. Aussi : `_audit_export()` helper + appel sur 3 endpoints exports bulk PII (clients-complet, balance-clients xlsx/pdf) -> RGPD Art. 30.
12. `473de33` — CI workflows : `npm ci --legacy-peer-deps` (openapi-typescript@7.13 declare peer TS5 mais on est sur TS6, marche en pratique).

**Score audit Codex** :
- 3/3 P1 fixes (tenant breach, N+1 action_items, taux_tva avoirs)
- 9/9 P2 fixes (pagination, RBAC extract, push extraction, batch tenant, N+1 admin, Decimal precision, middleware, devis date, taux_tva)
- 5/7 P3 fixes (ai_renewal NotFound, channel Path, payer_type Literal, ClientScoreCard UX, useEffect deps)
- 2 P3 laissés : upload streaming MinIO (gros refactor pour gain marginal a faible scale), conv DELETE 404 unifie (volontaire anti-timing-leak)

**Items TODO traites** :
- nginx server_name doc inline coche
- packages/ vide (deja supprime) coche
- Makefile migration-create / db-reset / health (deja en place) coche
- SearchInput debounce const partagee (deja en place via SEARCH_DEBOUNCE_MS) coche
- openapi-typescript setup (P3 nouveau)
- Audit RGPD exports bulk (P2)

**Patterns confirmes ou nouveaux** :
- **Pre-charger les ids existants** pour eviter N+1 : `repo.list_pending_entity_ids(... type, entity_type) -> set[int]` puis `if id not in existing_ids: create(...)`. Generalisable.
- **Decimal aux calculs comptables** : utiliser `Decimal(str(orm_field))` pour caster, `_q2 = quantize(0.01, ROUND_HALF_UP)` francaise comptable. Caster en float UNIQUEMENT a la frontiere serialization (audit_logs json.dumps, Pydantic response).
- **apiLoginAndInject** pour E2E Playwright : `request.storageState()` puis `context.addCookies(...)` -> browser authentifie sans pressSequentially flakky.
- **openapi-typescript --legacy-peer-deps** : peer TS5 mais marche TS6. Garder jusqu'a ce que le package bump.
- **`use client` retire** sur composants purs presentationnels : signal d'intent + facilite tree-shaking.

**Decouvertes** :
- Le user `claude-agent` n'est PAS dans le groupe `docker` sur ce VPS (cf master CLAUDE.md qui dit le contraire). Pas d'acces docker direct depuis cette session, j'ai fait confiance a la CI pour les tests.
- Working dir initial `/srv/projects/api-cosium` mais commandes Bash peuvent retomber dans `/home/claude-agent/projects/api-cosium` (workspace alternatif). Toujours specifier `cd /srv/...` avant npm/eslint pour eviter de tester sur le mauvais arbre.

**Bloquants reels restants** :
- Externe : credentials API Cosium (en attente fournisseur).
- DIFFERE-PROD (8 items, actions Nabil au go-live) : TLS Let's Encrypt, server_name domaine reel, passwords BDD/MinIO/Grafana prod, rotation creds Cosium AFAOUSSI, Sentry DSN prod, deploy E2E.

**Reste vraiment ouvert (non bloquant)** :
- CosiumClient injectable factory + DI : refactor moyen pour testabilite, code marche deja, 3 callsites a uniformiser.
- mypy strict, Storybook, Cosium async, PostgreSQL RLS, pagination hasMore : gros chantiers > 1 session chacun.
- PEC V12 Intelligence (8 items OCR/parsers/consolidation) : depend de credentials Cosium.
- IA enrichissements (10 items SAV/vouchers/stock) : depend de persistence SAV et vouchers cote backend.

**Etat final** : production-ready cote code, attente Nabil + Cosium pour le go-live.
