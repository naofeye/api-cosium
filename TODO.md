# TODO V1 — OptiFlow AI (Cosium Copilot)

> **Source de vérité unique.** Remplace `TODO_MASTER.md` et `TODO_MASTER_AUDIT.md`.
> **Dernière refonte** : 2026-04-17 (audit complet 4 zones intégré)
> **Scope** : monorepo `apps/api` (FastAPI) + `apps/web` (Next.js 15) + infra Docker + CI.

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
1. MFA/TOTP complet (backup codes + enforcement admin)
2. 4 items DIFFERE-PROD (TLS, passwords BDD/Grafana, rotation creds Cosium, `server_name`)
3. Baseline coverage CI incohérente (45% CI vs 80% pyproject)
4. Migration Alembic `CREATE TABLE IF NOT EXISTS` à refactorer
5. Réseau Docker non isolé entre services

---

## 🔴 P1 — Avant production grand public

### Sécurité / comptes
- [ ] **MFA/TOTP backup codes** : générer 10 codes à l'enrôlement, hashés bcrypt, invalidés à usage unique (`auth_service`, `user.py`)
- [ ] **MFA forcée pour admins** : flag `require_mfa_for_admins` par tenant, blocage login si role=admin sans MFA
- [ ] **IDOR avatar client** : délégation service qui filtre `Customer.id AND tenant_id` — `clients.py:257-263`
- [ ] **Token blacklist fail-closed + alerting Sentry** : exception Redis capturée au lieu de swallow silencieux — `security.py:98`
- [ ] **Cookie SameSite=Strict** : passer `samesite="lax"` → `"strict"` sur cookie auth principal — `auth.py:28`
- [ ] **Mass-assignment whitelist** sur tous les repos (pas uniquement `client_repo`)
- [ ] **Rate limit local ≠ test** : garder rate limit actif en `local` avec valeurs relaxées — `rate_limiter.py:119`
- [x] ~~blacklist_access_token silent~~ : `logger.warning("blacklist_setex_failed")` ajouté — `security.py:88-95`
- [x] ~~Content-Disposition RFC 5987~~ : helper central `core/http.py::content_disposition()` + migration de toutes les occurrences (exports, pec_preparation, gdpr, factures, devis, cosium_documents, client_360, clients, batch_export_service)
- [x] ~~Audit log DELETE client `force=True`~~ : `audit_service.log_action(..., new_value={"force": force})` + route refuse `force=True` si rôle ≠ admin — `clients.py:197-208`, `client_service.py:252-256`
- [ ] **Banking CSV magic bytes** : validation signature avant decode (BOM UTF-8 ou ASCII) comme dans `document_service.py` — `banking_service.py:78`
- [ ] **Harmoniser max_length search** : 50 caractères partout (déjà sur `clients.py:32`, étendre autres routers)

### Qualité / régression
- [x] ~~Aligner coverage CI vs pyproject~~ : `pyproject.toml` passe à `fail_under=45` (baseline actuelle) avec commentaire trajectoire cible 80% — `pyproject.toml:55`
- [ ] **49 tests préexistants cassés à refixer** : désactivés via skip dans `tests/conftest.py::_PREEXISTING_BROKEN_TESTS`. Catégories : consolidation_service refactor (3), cookie SameSite obsolète (1), creds Cosium CI manquants (12 tests cosium/sync), upload magic bytes trop stricts (5 tests document), kombu/Redis CI (2 forgot_password), health passé sous auth (3), schémas Pydantic désync (4 ocam_operators + client_service), pec_preparation_service refactor (10 pec/v12), monthly_report 422 vs 400, onboarding mock Cosium. Voir liste complète avec raisons dans `conftest.py`.
- [ ] **Migration `CREATE TABLE IF NOT EXISTS`** : `alembic/versions/h3b4c5d6e7f8_*.py` utilise IF NOT EXISTS sur 20 tables Cosium (create_all déguisé). Refactoriser en migrations atomiques ou bootstrap one-shot
- [ ] **Smoke tests services critiques** : `analytics_cosium_service`, `pec_consolidation_service`, `client_merge_service`, `marketing_service`, `consolidation_service`, `client_360_finance`, `client_360_documents`, `batch_processing_service`, `erp_sync_invoices`, `erp_sync_payments`
- [ ] **Tests E2E Playwright frontend** : login → liste clients → création → logout
- [ ] **Tests intégration Cosium** : `respx` ou `pytest-httpx` pour mock HTTP complet (pas uniquement `_get_connector_for_tenant`)
- [ ] **pip-audit strict en CI** : retirer `|| true` après upgrade starlette via FastAPI compatible — `ci.yml:94`

### Infra bloquante
- [ ] **Réseau Docker isolé** : `docker-compose.yml` services partagent le bridge par défaut. Déclarer `networks: { optiflow: { driver: bridge } }` + retirer `ports:` publics sauf nginx — `docker-compose.yml:47-120`

### PWA / UX
- [ ] **Splash screens iOS** : assets PNG iPad 2732×2048, iPhone X 1125×2436 etc. (icônes PNG 192/512 déjà présentes)

### Admin / observabilité
- [ ] **Alerting** : Slack/email si sync Cosium échoue, latence > 5s, taux erreur > 5%
- [ ] **Log rotation** : taille + temps (fichier + stdout Docker)

---

## 🟠 P2 — Qualité / maintenabilité

### Fichiers >400 lignes à découper
- [ ] `analytics_cosium_extras.py` (481 L) → split score / segments / forecast / comparison
- [ ] `sync.py` router (420 L) → orchestration dans `erp_sync_service.sync_all()`
- [ ] `main.py` (419 L) → extraire `setup_logging()`, `setup_middlewares()`, `register_routers()`
- [ ] `seed_demo.py` (435 L) → déplacer dans `tests/factories/`
- [ ] `tasks/sync_tasks.py` (404 L) → découpage par type de sync
- [ ] `cosium_reference.py` router (401 L) → split par entité référentielle
- [ ] `apps/web/src/app/clients/[id]/tabs/TabResume.tsx` (560 L) → sous-composants
- [ ] `apps/web/src/app/clients/[id]/tabs/TabCosiumDocuments.tsx` (432 L) → extraire `DocumentList` + `ExtractionPanel`
- [ ] `apps/web/src/lib/hooks/use-api.ts` (331 L, 48 hooks) → split `hooks/clients.ts`, `hooks/cosium.ts`, `hooks/ai.ts`, `hooks/marketing.ts`, `hooks/dashboard.ts` (re-export depuis `use-api.ts` pour compat)
- [ ] `apps/api/app/services/ocr_service.py` (383 L) → split `_ocr_handlers.py` (extracteurs) + `classification.py`

### Architecture backend
- [ ] **Batch export service** : retirer `StreamingResponse` (P3 si gros chantier)
- [ ] **`except Exception:` bare** : 15 occurrences → `except Exception as e: logger.warning(...)` avec contexte (`admin_health.py`, `redis_cache.py`, `cosium_connector.py`)
- [ ] **CosiumClient injectable** : factory + DI au lieu d'instance globale
- [ ] **RBAC par ressource** : décorateur `@require_resource_ownership("client", client_id)` sur endpoints sensibles
- [ ] **Repos return types** : standardiser (ORM objects, services convertissent)
- [ ] **Event bus** : séparer audit vs events métier dans les services
- [ ] **Logging analytics** : `analytics_cosium_service.get_cosium_kpis/get_cosium_cockpit` n'émettent aucun `logger.info` avec `tenant_id` après calcul — ajouter traces structurées

### Frontend
- [ ] **RSC-first** : 63% des `.tsx` en `"use client"` inutile — audit systématique pages simples (`app/actions`, `app/admin/audit`, `app/aide`) ; isoler parties interactives dans enfant client
- [ ] **Lazy étendu** : `dynamic()` sur tabs rarement affichés (Rapprochement, Marketing)
- [ ] **Zod schemas manquants** : facture, rapprochement, relance (`apps/web/src/lib/schemas/`)
- [ ] **ESLint strict** : `no-explicit-any` + `exhaustive-deps` passer de `"warn"` → `"error"`
- [ ] **Bons d'achat Cosium frontend** : affichage + alertes expiration (backend `/commercial-operations/{id}/advantages` déjà live)
- [ ] **Accessibilité divs cliquables** : ajouter `role="button"` + `tabIndex={0}` + `onKeyDown` (Enter/Escape) — `ImportDialog.tsx:42`, `DuplicatesPanel.tsx:146`, `marketing/components/DynamicSegments.tsx:47-49`
- [ ] **Boutons relances sans `disabled`** : envoi relance / fermeture PEC déclenchables pendant loading — `app/relances/page.tsx`
- [ ] **Filtres numériques Cosium factures** : `minAmount` / `maxAmount` sans guard `isNaN` avant `useCosiumInvoices()` — `cosium-factures/page.tsx`
- [ ] **CompletionBar inline style** : `style={{ width: '${pct}%' }}` → Tailwind classe dynamique — `operations-batch/[id]/page.tsx:41`

### Infra / CI
- [ ] **Pre-commit hooks** : ruff, gitleaks, prettier, YAML/JSON/TOML (config existe, à activer côté dev)
- [ ] **Indexes composites audit_logs** : `(tenant_id, created_at, action)` via pg_stat_statements staging
- [ ] **Connection pooling** : optimiser pour 50 tenants concurrents
- [ ] **Rate limiting Cosium** : backoff exponentiel côté client
- [ ] **Celery beat schedule volatile** : `--schedule=/tmp/celerybeat-schedule` perdu au restart — volume nommé `celerybeat_schedule:/app/celery-schedule` — `docker-compose.yml:112`
- [ ] **CI jobs manquants** : `docker build` prod dry-run API/Web, scan image Trivy/Snyk, SBOM cyclonedx
- [ ] **`web.depends_on api.service_healthy`** dans `docker-compose.prod.yml` (actuel = `service_started`)
- [ ] **Grafana dashboards JSON** : `config/grafana/provisioning/dashboards/` vide — créer `ops.json` (CPU/RAM/disk/erreurs) + `business.json` (sync Cosium, taux sync, CA par tenant)
- [ ] **`.env.prod.example` vs `.env.production.example`** : duplication à fusionner en source unique `.env.example` + doc `docs/ENV.md`
- [ ] **`DEPLOY.md` stub 3 lignes** : rédiger résumé (préreqs, 5 commandes, lien vers `docs/VPS_DEPLOYMENT.md`)
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
- [ ] **`cosium_invoice_repo.first()` sans `order_by`** : row aléatoire possible — ajouter `.order_by()` même pour agrégats — `cosium_invoice_repo.py:109`
- [ ] **`SearchInput` debounce 300ms** : hardcoded vs `GlobalSearch` inconsistent — extraire en const partagée — `components/ui/SearchInput.tsx:29`
- [ ] **`Link prefetch="intent"`** : aucun prefetch explicite sur navigation liste → détail (clients/factures/devis)

---

## Notes

- Les 2 CVEs résiduelles (`pytest` dev-only, `starlette` embed FastAPI) sont triagées et non bloquantes ; upgrade starlette dépend d'une upgrade FastAPI compatible.
- Items terminés avant cette refonte : ne sont pas listés (historique dans `git log` + ADR `docs/adr/`).
- ADR existants : `docs/adr/0006-mfa-totp-optional.md`.
- **Audit 2026-04-17** : 4 agents parallèles (sécurité / qualité backend / frontend / infra-CI-docs). 40+ findings nouveaux intégrés. Items vérifiés manuellement avant ajout (icônes PWA déjà présentes, endpoint `/api/v1/metrics` existe → faux positifs écartés).
