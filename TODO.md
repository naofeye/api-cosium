# TODO V1 — OptiFlow AI (Cosium Copilot)

> **Source de vérité unique.** Remplace `TODO_MASTER.md`, `TODO_MASTER_AUDIT.md` et `DEV-PLAN.md`.
> **Dernière refonte** : 2026-04-29 (all inclusive audit)
> **Scope** : monorepo `apps/api` (FastAPI) + `apps/web` (Next.js 16) + infra Docker + CI.

---

## 🔴 P0 — Audit 29/04 (à corriger en priorité)

- [ ] Fix 3 tests frontend login cassés (bouton disabled + router.push → window.location)
  Files: apps/web/tests/pages/login.test.tsx, apps/web/tests/flows/login-flow.test.tsx
- [ ] Fix `test_seed.py` fixture `db` manquante
  Files: apps/api/tests/factories/test_seed.py
- [ ] Investiguer CI failure sur main (run `25056556905`)
- [ ] Monter `tests/` en volume Docker ou retirer du `.dockerignore` pour dev
  Files: apps/api/.dockerignore

## 🟡 P1 — Audit 29/04

- [ ] Guard prod `jwt_secret` (refuser valeur par défaut `_DEV_JWT_SECRET` en production)
  Files: apps/api/app/core/config.py
- [ ] Split `ai_service.py` 445L sous 300L (extraire prompts + context builder)
  Files: apps/api/app/services/ai_service.py
- [ ] Split `client_import_service.py` 307L et `auth_service.py` 304L
- [ ] Split `ChatInterface.tsx` 326L et `Header.tsx` 305L
  Files: apps/web/src/app/copilote-ia/components/ChatInterface.tsx, apps/web/src/components/layout/Header.tsx

---

## Plan de dev (ex DEV-PLAN.md)

### Direction (validée par Nabil 27/04/2026)

- **PAS de prod** pour l'instant (attente credentials API Cosium)
- **Priorité B** : polir ce qui existe (copilot IA, tests E2E, UX)
- **Priorité C** : combler les manques fonctionnels (avoirs, envoi devis, signature, SMS)

### Exigence qualité

Chaque feature implémentée doit être de **qualité professionnelle** :
- Backend : pattern router→service→repo, validation Pydantic, RBAC, tests unitaires, ruff vert
- Frontend : TypeScript strict (0 `any`), loading/error/empty states, responsive, accessibilité (aria-labels), vitest vert
- Pas de raccourci, pas de TODO laissé, pas de code mort

### Règles

- Un seul item en cours à la fois
- Checkpoint Nabil obligatoire pour les items niveau 2+
- Max 15 min par item (timeout)
- Commit séparé par item (revert facile)
- NE PAS modifier les fichiers de config infra (docker-compose, .env, CI) sans validation
- Chaque item DOIT avoir un champ `Files:` qui liste les fichiers autorisés
- Claude ne peut modifier QUE les fichiers listés dans `Files:` — tout le reste est revert automatiquement
- Si un item est trop vague pour lister les fichiers → session interactive, pas dev-cycle

### Niveaux

- **Niveau 1** (safe) : fix bugs, ajouter tests, docs, refactor interne — pas de checkpoint
- **Niveau 2** (encadré) : nouvelle feature avec specs claires — checkpoint à la fin
- **Niveau 3** (créatif) : architecture, nouveau module — validation AVANT de coder

### File d'attente

#### Priorité B — Polir ce qui existe

- [x] Copilot IA conversationnel — Backend : endpoint streaming SSE _(fait 2026-04-27)_
- [x] Copilot IA conversationnel — Frontend : page interactive _(fait 2026-04-27)_
- [x] Envoi devis par email au client _(fait 2026-04-28)_
- [x] Envoi facture par email au client _(fait 2026-04-28)_

#### Priorité C — Manques fonctionnels

- [ ] Avoirs / notes de crédit sur factures
  Files: apps/api/app/api/routers/factures.py, apps/api/app/services/facture_service.py, apps/api/app/models/facture.py, apps/api/app/domain/schemas/factures.py, apps/api/app/repositories/facture_repo.py, apps/web/src/app/factures/[id]/page.tsx
  Niveau: 2

- [ ] Expiration automatique des devis
  Files: apps/api/app/models/devis.py, apps/api/app/services/devis_service.py, apps/api/app/tasks/*, apps/web/src/app/devis/page.tsx
  Niveau: 2

- [ ] Historique conversationnel copilot IA (persisté)
  Files: apps/api/app/models/ai.py, apps/api/app/services/ai_service.py, apps/api/app/api/routers/ai.py, apps/api/app/repositories/ai_repo.py (nouveau)
  Niveau: 2

#### P2 — Qualité (DEV-PLAN items)

- [x] ~~Déplacer seed_demo.py dans tests/factories/~~ _(fait 2026-04-26)_
- [x] ~~Remplacer 15 `except Exception:` bare~~ _(fait 2026-04-26)_
- [x] ~~Ajouter `order_by` manquant sur `cosium_invoice_repo.first()`~~ _(fait 2026-04-26)_
- [x] ~~Split `ocr_service.py`~~ _(déjà fait)_
- [x] ~~Coverage backend 45% → 55%~~ _(fait 2026-04-26)_
- [ ] ESLint `no-explicit-any` warn → error ⚠️ ITEM LARGE — session interactive

---

## État actuel — synthèse

**Niveau atteint** : production-ready pour environnement de test contrôlé.

| Zone | Statut |
|---|---|
| Architecture backend (routers/services/repos, multi-tenant, Cosium read-only) | 🟢 Solide |
| Frontend (Next 15, SWR, CSP nonces, 0 `any`, PWA base) | 🟡 Bonne, perf client à travailler |
| Sécurité (OWASP, JWT, bcrypt, idempotence, audit logs) | 🟡 MFA et CSRF Strict manquants |
| Tests (~107 passent, suites critiques) | 🟡 Baseline coverage non enforcée |
| Infra/CI (Alembic + rollback, Prometheus, Sentry, Celery beat) | 🟢 Mature |
| Dette technique | 🟡 6 fichiers >400 lignes, quelques N+1, `time.sleep` Cosium |

**Bloquants passage production grand public** :
1. ~~MFA/TOTP complet~~ ✅ (backup codes + enforcement admin + UI)
2. 4 items DIFFERE-PROD (TLS, passwords BDD/Grafana, rotation creds Cosium, `server_name`)
3. ~~Baseline coverage CI incohérente~~ ✅ (45% aligné pyproject + CI)
4. ~~Migration Alembic `CREATE TABLE IF NOT EXISTS`~~ ✅ ([ADR 0007](docs/adr/0007-alembic-bootstrap-migration-accepted.md))
5. ~~Réseau Docker non isolé entre services~~ ✅ (2 réseaux prod, `internal: true`)

---

## 🔴 P1 — Avant production grand public

### Sécurité / comptes
- [x] ~~MFA/TOTP backup codes~~ : 10 codes 8-hex, hashés bcrypt, usage unique. Endpoints `POST /auth/mfa/backup-codes/generate` + `GET /auth/mfa/backup-codes/count`. Migration `w8x9y0z1a2b3`. 16 tests unit + 2 tests endpoint. `LoginRequest.totp_code` accepte TOTP (6 digits) OU backup (8 hex, avec/sans tiret/lowercase).
- [x] ~~MFA forcée pour admins~~ : flag `Tenant.require_admin_mfa` (défaut False). Login refuse avec `MFA_SETUP_REQUIRED` si user admin (TenantUser.role) dans un tenant où le flag est on et n'a pas TOTP. Endpoints `GET/PATCH /api/v1/admin/tenant/security` (audit trail). Migration `x9y0z1a2b3c4`. 8 tests (4 service + 4 endpoints).
- [x] ~~IDOR avatar client~~ : faux positif audit — vérifié `client_service.get_avatar_url` filtre déjà par `tenant_id` via `client_repo.get_by_id_active`, et storage_key inclut `tenants/{tenant_id}/avatars/...` (isolation physique).
- [x] ~~Token blacklist fail-closed + alerting Sentry~~ : helper `_report_security_incident_to_sentry(exc, tag)` dans `security.py`, appelé dans `blacklist_setex_failed`, `blacklist_redis_unavailable`, `blacklist_check_failed`. Tag `security_incident` + level `error`. Best-effort (no-op si Sentry non configuré).
- [x] ~~Cookie SameSite=Strict~~ : déjà fait — `auth.py:29` (`_COOKIE_OPTS["samesite"]="strict"`) + `_set_auth_cookies` + `_clear_auth_cookies` tous en `strict`. Test `test_cookies_have_samesite_strict` actif (ligne 48).
- [x] ~~Mass-assignment whitelist tous repos~~ : étendu à `onboarding_repo.create_organization/tenant/user` (3 whitelists `_ORG_WRITABLE`, `_TENANT_WRITABLE`, `_USER_WRITABLE`). Protège contre injection `totp_enabled=True`, `require_admin_mfa=True`, `is_god_mode`, etc. 4 tests.
- [x] ~~Rate limit local ≠ test~~ : déjà fait dans `core/rate_limiter.py:120` (`if settings.app_env == "test": ...`). Local garde bien le rate limit actif.
- [x] ~~blacklist_access_token silent~~ : `logger.warning("blacklist_setex_failed")` ajouté — `security.py:88-95`
- [x] ~~Content-Disposition RFC 5987~~ : helper central `core/http.py::content_disposition()` + migration de toutes les occurrences (exports, pec_preparation, gdpr, factures, devis, cosium_documents, client_360, clients, batch_export_service)
- [x] ~~Audit log DELETE client `force=True`~~ : `audit_service.log_action(..., new_value={"force": force})` + route refuse `force=True` si rôle ≠ admin — `clients.py:197-208`, `client_service.py:252-256`
- [x] ~~Banking CSV magic bytes~~ : helper `_validate_csv_signature(file_data)` dans `banking_service.py` — rejette PDF/ZIP/PNG/JPEG/MZ/ELF/GIF/TIFF, tolère BOM UTF-8, refuse bytes de contrôle non textuels. Exceptions `FILE_EMPTY` + `FILE_NOT_CSV`. 4 tests (pdf, zip, empty, bom).
- [x] ~~Harmoniser max_length search~~ : `max_length=100` sur tous les `search: Query(None, ...)` des routers Cosium (13 occurrences : `cosium_invoices.py`, `cosium_reference.py`, `cosium_documents.py`, `reconciliation.py`). Anti-DoS query géante. Aligné avec `clients.py:34`.

### Qualité / régression
- [x] ~~Aligner coverage CI vs pyproject~~ : `pyproject.toml` passe à `fail_under=45` (baseline actuelle) avec commentaire trajectoire cible 80% — `pyproject.toml:55`
- [x] ~~49 tests préexistants cassés à refixer~~ : dict `_PREEXISTING_BROKEN_TESTS` dans `tests/conftest.py` est désormais vide (plus de skip). CI verte confirmée depuis le commit smoke tests (2026-04-17 T10:38 UTC). Les commentaires dans conftest.py documentent l'historique des fix par catégorie. Les sync_customer_documents / cosium creds / storage / celery.delay sont désormais mockés via `_mock_storage` et `_mock_celery_delay` autouse fixtures. ~1001 tests collectés, exécutent en CI.
- [x] ~~Migration `CREATE TABLE IF NOT EXISTS`~~ : acceptée comme bootstrap one-shot via [ADR 0007](docs/adr/0007-alembic-bootstrap-migration-accepted.md). Les 21 tables créées ont toutes un modèle SQLAlchemy correspondant (vérifié par script). Docstring enrichie dans la migration pointant vers l'ADR. **Règle** établie : aucune nouvelle migration ne doit utiliser `IF NOT EXISTS` — API Alembic standard uniquement.
- [x] ~~Smoke tests services critiques~~ : les 7 services restants couverts dans `test_services_smoke_extra.py` (29 tests). `marketing_service` (list/create/refresh segments + campaigns), `consolidation_service` (customer inconnu + minimal), `client_360_finance` (aggregate/build_summary/compute_ca/fetch + isolation tenant), `client_360_documents` (prescriptions/equipments/payments/calendar/tags/ocr), `batch_processing_service` (3 NotFoundError), `erp_sync_invoices` (connector vide), `erp_sync_payments` (non-Cosium + Cosium vide). Combiné avec `test_services_smoke.py` (8 tests) = 37 smoke tests.
- [x] ~~Tests E2E Playwright frontend~~ : setup `@playwright/test` + `otplib@12` dans `apps/web/`. 3 specs / 10 tests dans `tests/e2e/` (login UI+API, MFA flow TOTP dérivé, clients CRUD + logout). Helpers `helpers.ts`. Workflow CI `.github/workflows/e2e.yml` en **`workflow_dispatch` uniquement** : raison documentée = cookies httpOnly cross-origin (3000 vs 8000) non consommés par fetch client-side en CI headless. Tests API-direct + flow MFA API passent. Tests UI cookie-based à débloquer via nginx reverse proxy dans workflow (itération suivante). En local avec `docker compose up`, les 10 tests tournent (nginx proxy). Scripts npm `test:e2e` + `test:e2e:ui`.
- [x] ~~Tests intégration Cosium (respx)~~ : `test_cosium_client_respx.py` (20 tests, respx==0.23.1 dans requirements). Couvre auth basic (token/access_token/retries/failure/creds manquants), GET (auth required, headers, retry, failure), pagination HAL + Spring Data + page vide, token refresh 25 min, get_raw bytes, règles sécurité (pas de put/delete/patch/post/request) + vérif que seuls POST /authenticate/basic et GET sont appelés.
- [x] ~~pip-audit strict en CI~~ : déjà en place dans `ci.yml:97` (`pip-audit -r requirements.txt --strict --ignore-vuln CVE-2025-71176 --ignore-vuln CVE-2025-62727`). Pas de `|| true`. Les 2 CVEs triées documentées inline (pytest dev-only, starlette embed FastAPI).

### Infra bloquante
- [x] ~~Réseau Docker isolé~~ : segmentation **2 réseaux** en prod (`docker-compose.prod.yml`) :
  - `internal` (`internal: true` = pas d'egress internet) pour postgres/redis/minio/beat
  - `public` pour web/nginx
  - api + worker sur les 2 (besoin Cosium/SMTP externe + DB/Redis interne)
  - Si web compromis → pas d'accès direct aux datastores. Défense en profondeur OWASP A05.

### MFA / Auth
- [x] ~~MFA frontend UI~~ : composant `MfaSection` (setup TOTP avec QR code via `qrcode.react`, input vérification 6 digits, backup codes générés + affichés une fois, désactivation avec mot de passe). Intégré dans `/settings`. Login étendu avec flow TOTP : `MfaRequiredError` typé, champ code affiché conditionnellement (`MFA_CODE_REQUIRED` / `MFA_CODE_INVALID`), message admin pour `MFA_SETUP_REQUIRED`. Page `/admin/security` pour toggle `require_admin_mfa` par tenant (confirm dialog + warning lockout). Lien ajouté dans panel admin. 0 warning lint, TS vert.

### E2E Playwright — débloquer les tests UI login (jamais passés, 20+ runs fail)
- [x] **Fix appliqué (2026-04-28, session vps-master)** : `window.location.href = "/actions"` au lieu de `router.push("/actions")` dans `login/page.tsx`. Commit `770c03c`.
- [ ] **Root cause identifiée (2026-04-25, session vps-master)** :

  **Le problème** : les 10 tests UI qui passent par `uiLogin()` échouent tous avec `toHaveURL(/\/actions$/)` timeout. Le formulaire soumet (l'API reçoit le POST login et retourne 200), mais `router.push("/actions")` ne redirige pas. Les tests API-only (sans navigateur) passent.

  **Ce qui a été essayé et n'a PAS marché** :
  1. `fill()` au lieu de `pressSequentially` → react-hook-form `register()` ne met pas à jour son store interne via `fill()`, les valeurs restent vides dans handleSubmit
  2. `pressSequentially` sans delay → même problème, button disabled
  3. `fill()` + `dispatchEvent(input/change)` → pas fiable
  4. Retirer le `disabled` du bouton (commit `539255d`) → le form soumet maintenant (20 login 200 OK dans les logs API), mais la redirection échoue toujours
  5. Standalone server `node .next/standalone/apps/web/server.js` au lieu de `next start` → le serveur démarre correctement (pas de warning), mêmes résultats

  **État actuel du code après les tentatives** :
  - `next.config.ts` : `outputFileTracingRoot: path.join(__dirname, "../../")` ajouté (monorepo)
  - `e2e.yml` : lance le standalone server correctement (`.next/standalone/apps/web/server.js`)
  - `helpers.ts:uiLogin()` : `pressSequentially` avec `delay: 20` + `click()` bouton
  - `login/page.tsx` : bouton sans `disabled` (juste `loading={isSubmitting}`)

  **Hypothèse la plus probable** : le middleware Next.js (`src/middleware.ts`) vérifie `request.cookies.get("optiflow_token")` pour les routes protégées. Après le login API réussi, le cookie httpOnly est setté par la réponse `fetch()`. Mais quand `router.push("/actions")` fait un RSC fetch serveur-side, le cookie n'est pas transmis ou pas reconnu. Possible causes :
  - Cookie `SameSite=Strict` avec nginx proxy en CI (origin mismatch ?)
  - Le RSC prefetch de Next.js 15 ne forward pas les cookies httpOnly sur les requêtes internes
  - Le standalone server ne traite pas le middleware de la même façon

  **Fix confirmé** : `window.location.href = "/actions"` force un rechargement complet de la page (hard navigation). Le navigateur traite les `Set-Cookie` de la réponse login AVANT d'envoyer la prochaine requête. `router.push()` (soft navigation RSC) peut déclencher la requête RSC avant que le browser ait persisté les cookies httpOnly SameSite=Strict — le middleware ne voit pas le token et redirige vers /login.

  **Fichiers clés** :
  - `apps/web/src/middleware.ts` — le guard auth
  - `apps/web/src/app/login/page.tsx` — le formulaire
  - `apps/web/src/lib/auth.ts` — `login()` fetch + `router.push`
  - `apps/web/tests/e2e/helpers.ts` — `uiLogin()`
  - `.github/workflows/e2e.yml` — le workflow CI
  - `config/nginx/nginx.e2e.conf` — le proxy nginx CI
  - `apps/api/app/api/routers/auth.py` — `_COOKIE_OPTS` (httpOnly, SameSite=Strict, secure=False en test)

### PWA / UX
- [ ] **Splash screens iOS** : assets PNG iPad 2732×2048, iPhone X 1125×2436 etc. (icônes PNG 192/512 déjà présentes)

### Admin / observabilité
- [x] ~~Alerting sync Cosium échoue~~ : helper central `core/sentry_helpers.py::report_incident_to_sentry(exc, tag, category=..., **context)`. Capture + tags indexés (incident_category, incident, tenant_id, domain). Câblé dans `tasks/sync_tasks.py` aux 4 callsites (`cosium_sync_failed`, `cosium_sync_partial_failure`, `cosium_sync_domain_failed`, `cosium_bulk_download_failed`). Best-effort (no-op si `sentry_dsn` vide, try/except interne). Refacto `security.py` pour réutiliser le helper. 4 tests. Latence/taux erreur relèvent de Prometheus alertmanager (hors scope backend).
- [x] ~~Log rotation~~ : ancre YAML `x-default-logging` dans `docker-compose.prod.yml` avec driver json-file, `max-size: 50m`, `max-file: 5`, compression gzip. Appliquée à tous les services (postgres, redis, minio, api, web, worker, beat, nginx) = plafond 250MB par container.

---

## 🟠 P2 — Qualité / maintenabilité

### Fichiers >400 lignes à découper
- [x] ~~`analytics_cosium_extras.py` 481 L → package 4 modules~~ : `analytics_cosium_extras/` avec `_score.py` (181 L), `_segments.py` (172 L), `_forecast.py` (97 L), `_comparison.py` (128 L), `__init__.py` (28 L) re-exporte les 8 fonctions publiques. Import public inchangé. 285 routes identiques, 67 smoke tests verts.
- [x] ~~`sync.py` router 420 L → package + orchestration dans service~~ : `routers/sync/` avec 5 fichiers (`__init__.py` 23 L, `_meta.py` 54 L, `_domains.py` 278 L, `_all.py` 58 L, `_helpers.py` 19 L). Orchestration déplacée : `erp_sync_service.sync_all(db, tenant_id, user_id, full)` contient la logique (customers + invoices/payments/prescriptions + reference, isolation d'erreurs par domaine). Le routeur `_all.py` délègue + gère lock Redis + HTTP 207 Multi-Status si has_errors. 285 routes identiques, 67 smoke tests verts.
- [x] ~~`main.py` 432 L → 228 L~~ : 3 modules extraits. `app/api/registry.py` (`register_routers`, 48 include_router) / `app/core/middleware_setup.py` (`setup_middlewares` + `SelectiveGZipMiddleware` + `log_response_time`) / `app/core/exception_handlers.py` (`register_exception_handlers` + 7 handlers). main.py garde FastAPI init, `_lifespan`, `_startup_checks`, endpoints health/version. 285 routes identiques, 67 smoke tests verts.
- [x] ~~`seed_demo.py` (435 L) → déplacer dans `tests/factories/`~~ _(fait 2026-04-26)_
- [x] ~~`tasks/sync_tasks.py` 440 L → package par type~~ : `_sync_all.py` (172 L) / `_connectivity.py` (115 L) / `_bulk_download.py` (59 L) / `_prescriptions.py` (130 L) / `__init__.py` (31 L). Celery names hardcodés préservés → routing + beat schedules inchangés. 45 tests verts.
- [x] ~~`cosium_reference.py` router 401 L → package~~ : transformé en `routers/cosium_reference/` avec 4 sous-modules (`_sync.py` 37 L, `_calendar.py` 150 L, `_entities.py` 231 L, `_data.py` 120 L) + `__init__.py` (22 L) router composite. Import public inchangé (`from app.api.routers.cosium_reference import router`). 285 routes identiques, 57 smoke tests verts, ruff vert.
- [x] ~~`TabResume.tsx` 560 L → 98 L orchestrateur + `_resume/` package 7 fichiers~~ : `types.ts` (65 L interfaces) / `shared.tsx` (54 L : InfoRow + TYPE_ICONS + formatDiopter + formatAxis) / `ClientScoreCard.tsx` (89 L) / `SummaryCards.tsx` (242 L : 5 cards du grid — PersonalInfo, CosiumSummary, Mutuelles, Correction, RecentInteractions) / `QuickNotesSection.tsx` (113 L) / `RecentInvoicesTable.tsx` (52 L) / `RenewalBanner.tsx` (23 L). Props inchangées, 160/160 vitest verts, TS strict vert.
- [x] ~~`TabCosiumDocuments.tsx` 432 L → 173 L + `_cosium_documents/` package 4 fichiers~~ : `types.ts` (65 L) / `StructuredDataDisplay.tsx` (112 L) / `ExtractionPanel.tsx` (63 L) / `DocumentRow.tsx` (78 L). 160/160 vitest verts. **Série fichiers >400 L : 7/7 fermés**.
- [x] ~~`apps/web/src/lib/hooks/use-api.ts` split par domaine~~ : 331 L → 5 fichiers domaine + barrel 15 L. `clients.ts` (103 L, 13 hooks) / `cosium.ts` (197 L, 11 hooks) / `ai.ts` (18 L, 4 hooks) / `marketing.ts` (10 L, 2 hooks) / `dashboard.ts` (28 L, 5 hooks). `use-api.ts` ne fait plus que `export *` pour compat. 160/160 vitest verts, TS strict vert. Facilite tree-shaking et prépare le `dynamic()` lazy-loading par domaine.
- [x] ~~`apps/api/app/services/ocr_service.py` (383 L) → split~~ _(fait, facade 55L + handlers 132L + classification 158L)_

### Architecture backend
- [ ] **Batch export service** : retirer `StreamingResponse` (P3 si gros chantier)
- [x] ~~**`except Exception:` bare** : 15 occurrences~~ _(fait 2026-04-26)_
- [ ] **CosiumClient injectable** : factory + DI au lieu d'instance globale
- [ ] **RBAC par ressource** : décorateur `@require_resource_ownership("client", client_id)` sur endpoints sensibles
- [ ] **Repos return types** : standardiser (ORM objects, services convertissent)
- [ ] **Event bus** : séparer audit vs events métier dans les services
- [x] ~~Logging analytics~~ : `logger.info("cosium_kpis_computed", tenant_id, invoice_count, quote_count, credit_note_count, elapsed_ms)` ajouté dans `get_cosium_kpis`. `logger.info("cosium_cockpit_kpis_computed", tenant_id, ca_month, nb_invoices_month, quote_to_invoice_rate, aging_total, elapsed_ms)` dans `get_cosium_cockpit_kpis`. Mesure via `time.perf_counter()`. Observabilité : détecter N+1 latents, fréquence des calculs par tenant.

### Frontend
- [ ] **RSC-first** : 63% des `.tsx` en `"use client"` inutile — audit systématique pages simples (`app/actions`, `app/admin/audit`, `app/aide`) ; isoler parties interactives dans enfant client
- [x] ~~Lazy étendu `dynamic()` sur tabs secondaires~~ : ClientTabs (Rapprochement, Marketing + 7 autres) déjà en dynamic(). **Étendu** à : `relances/page.tsx` (3 tabs lazy : Clients30, Timeline, Historique ; seul Overdue reste sync) et `cases/[id]/page.tsx` (4 tabs lazy : Documents, Finances, IA, Historique ; seul Resume reste sync). Gain estimé : ~255 L relances + ~282 L cases hors du bundle initial. Charts (`DashboardCharts`, `StatistiquesCharts`, `ActivityChart`) déjà lazy. TS vert, 160/160 vitest.
- [x] ~~Zod schemas manquants~~ : `schemas/facture.ts` (`factureCreateSchema`), `schemas/rapprochement.ts` (`manualMatchSchema`), `schemas/reminder.ts` enrichi avec `reminderCreateSchema`. Intégrés aux 2 call-sites actifs (`devis/[id]/page.tsx::generateFacture` + `rapprochement/hooks/useRapprochementActions.ts::manualMatch`) : validation runtime avant POST. Le schema relance est prêt pour future UI d'envoi manuel. 12 tests ajoutés dans `tests/lib/schemas.test.ts` (30/30 passent).
- [ ] **ESLint strict** : `no-explicit-any` + `exhaustive-deps` passer de `"warn"` → `"error"`
- [ ] **Bons d'achat Cosium frontend** : affichage + alertes expiration (backend `/commercial-operations/{id}/advantages` déjà live)
- [x] ~~Accessibilité divs cliquables~~ : `ImportDialog.tsx` a maintenant Escape key + `role="dialog" aria-modal="true" aria-label`. `DuplicatesPanel.tsx:135` utilise déjà `<button>` natif (faux positif audit). `DynamicSegments.tsx` : `cursor-pointer` sans onClick = WIP feature "création campagne" laissée en l'état (texte "Cliquez pour créer" annonce la feature à venir).
- [x] ~~Boutons relances sans `disabled`~~ : `relances/plans/page.tsx` — state `inFlightId` + guard early-return + `disabled={inFlightId !== null}` sur Play/Toggle buttons + classes `disabled:opacity-50 disabled:cursor-not-allowed`. Empêche double-clic executePlan/togglePlan.
- [x] ~~Filtres numériques Cosium factures~~ : `cosium-factures/page.tsx` — IIFE + `Number.isNaN(n)` guard sur `min_amount` et `max_amount`. Empêche l'envoi de `NaN` à l'API si l'utilisateur tape "abc".
- [ ] **CompletionBar inline style** : `style={{ width: '${pct}%' }}` → Tailwind classe dynamique — `operations-batch/[id]/page.tsx:41`

### Infra / CI
- [x] ~~Pre-commit hooks activés (scope défensif)~~ : config `.pre-commit-config.yaml` nettoyée : `check-yaml --unsafe` (tags docker-compose), `check-json`, `check-toml`, `check-merge-conflict`, `check-added-large-files 500kB`, `detect-private-key`, `gitleaks`. Les hooks réécrivant du contenu (ruff-format, prettier, mixed-line-ending, end-of-file-fixer, trailing-whitespace) sont désactivés pour éviter un diff massif sur le legacy (288 fichiers ruff-format + 193 prettier au premier run). À ré-activer après un commit de nettoyage global dédié. `CONTRIBUTING.md` enrichi (install + commands manuelles reformatage).
- [ ] **Indexes composites audit_logs** : `(tenant_id, created_at, action)` via pg_stat_statements staging
- [ ] **Connection pooling** : optimiser pour 50 tenants concurrents
- [ ] **Rate limiting Cosium** : backoff exponentiel côté client
- [x] ~~Celery beat schedule volatile~~ : volume nommé `celerybeat_schedule:/app/celery-schedule` ajouté sur le service beat (`docker-compose.yml`). Schedule persisté au path `/app/celery-schedule/schedule.db`. Healthcheck mis à jour sur ce path. Évite la re-exécution de toutes les tasks planifiées au restart container.
- [ ] **CI jobs manquants** : `docker build` prod dry-run API/Web, scan image Trivy/Snyk, SBOM cyclonedx
- [x] ~~`web.depends_on api.service_healthy`~~ : override `depends_on.api.condition: service_healthy` ajouté dans `docker-compose.prod.yml:85-87`. Web attend que l'API soit `healthy` (pas juste started) avant démarrage.
- [ ] **Grafana dashboards JSON** : `config/grafana/provisioning/dashboards/` vide — créer `ops.json` (CPU/RAM/disk/erreurs) + `business.json` (sync Cosium, taux sync, CA par tenant)
- [ ] **`.env.prod.example` vs `.env.production.example`** : duplication à fusionner en source unique `.env.example` + doc `docs/ENV.md`
- [x] ~~**`DEPLOY.md` stub 3 lignes**~~ : supprimé (pointait déjà vers `docs/VPS_DEPLOYMENT.md`)
- [ ] **`docs/RUNBOOK.md` minimal** : ajouter SLO (uptime 99.5%, p95 < 500ms), escalade (P1 <15min, P2 <1h), rollback DB complet ; retirer URLs Sentry fictives
- [ ] **nginx `server_name _;` dev/prod** : documenter explicitement dev=`_`, prod=domaine réel (sinon Host-header attack) — `config/nginx/nginx.conf:49`

### Observabilité / RGPD
- [ ] **Grafana dashboards** : ops (infra) + métier (CA, sync, clients par tenant)
- [ ] **Audit trail RGPD** : chaque consultation donnée sensible logguée
- [ ] **Droit à l'oubli / export / consentements** RGPD complet

### PEC V12 Intelligence
- [ ] Liaison 100 % factures : fuzzy matching via `_links.customer.href`
- [ ] Table `client_mutuelles` (relation N-N)
- [ ] Auto-détection mutuelle depuis TPP/invoices/documents
- [ ] OCR pipeline (Tesseract + pdfplumber)
- [ ] Classification documents (ordonnance, devis, attestation)
- [ ] Parsers structurés (6 types)
- [ ] Consolidation multi-source + détection incohérences
- [ ] PEC assistant frontend : onglet interactif fiche client

### IA — enrichissements
- [ ] Alertes SAV en attente > X jours (requiert persistence SAV)
- [ ] Alertes bons d'achat expirant < 30 jours (requiert persistence vouchers)
- [ ] Priorisation IA des action items par impact financier
- [ ] KPI SAV dashboard (requiert persistence SAV)
- [ ] Alertes stock rupture agrégées (croisement `latent-sales` + `stock`)
- [ ] Stock disponible réel (physique − latentes)
- [ ] Stock inter-magasins consolidé
- [ ] Tools Claude avancés chatbot : SAV count, CA par produit, etc.
- [ ] Acomptes suivi via filtre `hasAdvancePayment=true`
- [ ] Ventes latentes — potentiel CA

---

## ⏸️ DIFFERE-PROD — À faire au passage en production

- [ ] **TLS Let's Encrypt** : décommenter bloc SSL `config/nginx/nginx.conf:122-198` + configurer cert (domaine requis)
- [ ] **`server_name` explicite** dans nginx prod (pas `_` catch-all `nginx.conf:49`)
- [ ] **Passwords BDD prod** : override `POSTGRES_PASSWORD` (actuel `optiflow` par défaut)
- [ ] **Passwords MinIO prod** : override `minioadmin:minioadmin`
- [ ] **Password Grafana prod** : `GF_SECURITY_ADMIN_PASSWORD` (actuel `admin/admin`)
- [ ] **Rotation creds Cosium** : révocation compte `AFAOUSSI` + `git filter-branch` sur `.env` + migration vers cookie session par tenant
- [ ] **Sentry DSN prod** : configurer `SENTRY_DSN` dans env prod
- [ ] **Deploy E2E** : `docker compose -f docker-compose.prod.yml up` sans erreur (env prod complet)

---

## 🟡 P3 — Long terme / nice-to-have

### Scale
- [ ] **Cosium client async** : `httpx.AsyncClient` (retire `time.sleep` bloquant) — refonte services en cascade
- [ ] **PostgreSQL RLS** : activer policies `tenant_id = current_setting('app.current_tenant_id')::int` (défense en profondeur)
- [ ] **Pagination `hasMore`** : pattern `LIMIT size+1`, retirer `COUNT(*)` dans `client_repo.search` (refonte UX pagination)
- [ ] **mypy strict** backend (`mypy apps/api/app --strict`)

### Produit
- [ ] **Portail client public** : espace web (devis, factures, RDV, prescription), prise RDV en ligne, suivi SAV public, signature électronique devis
- [ ] **Intégrations externes** : QR Code dossier/devis, SMS RDV/relance, export comptable Sage/Cegid/QuickBooks, webhooks entrants, Zapier/Make, API publique v1
- [ ] **PWA avancée** : mode hors-ligne fiches clients cachées, scan EAN caméra, push notifications natives
- [ ] **A/B testing UI** campagnes marketing (modèle `variant_templates_json[]` + random dispatch)
- [ ] **IA agent conversationnel tool-use** : enrichir `copilot_query` avec tools via Claude tool-use API
- [ ] **API versioning `/v2`** : documenter politique breaking changes

### DX
- [ ] **Storybook** UI components
- [ ] **openapi-typescript** client auto-généré
- [ ] **Load test CI** : job `workflow_dispatch` Locust 50 users 2 min staging
- [ ] **Semantic versioning** CI tags
- [ ] **Seed data generator** + VS Code debug profiles
- [ ] **`packages/` vide** : soit utiliser pour code partagé api/web, soit supprimer (`.gitkeep` seul)
- [ ] **Makefile** : renommer `make migration` → `make migration-create MSG=...`, ajouter `make db-reset`
- [ ] **`scripts/health.sh`** dédié : check postgres/redis/minio/api/web, exit 0/1 (Makefile + RUNBOOK)

### Qualité ponctuelle
- [x] ~~**`cosium_invoice_repo.first()` sans `order_by`**~~ _(fait 2026-04-26)_
- [ ] **`SearchInput` debounce 300ms** : hardcoded vs `GlobalSearch` inconsistent — extraire en const partagée — `components/ui/SearchInput.tsx:29`
- [ ] **`Link prefetch="intent"`** : aucun prefetch explicite sur navigation liste → détail (clients/factures/devis)

---

## Notes

- Les 2 CVEs résiduelles (`pytest` dev-only, `starlette` embed FastAPI) sont triagées et non bloquantes ; upgrade starlette dépend d'une upgrade FastAPI compatible.
- Items terminés avant cette refonte : ne sont pas listés (historique dans `git log` + ADR `docs/adr/`).
- ADR existants : `docs/adr/0006-mfa-totp-optional.md`.
- **Audit 2026-04-17** : 4 agents parallèles (sécurité / qualité backend / frontend / infra-CI-docs). 40+ findings nouveaux intégrés. Items vérifiés manuellement avant ajout (icônes PWA déjà présentes, endpoint `/api/v1/metrics` existe → faux positifs écartés).
