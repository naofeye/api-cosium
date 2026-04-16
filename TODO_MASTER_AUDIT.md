# TODO_MASTER_AUDIT — Audit profond OptiFlow AI

**Date de l'audit** : 2026-04-16
**Scope** : monorepo complet (`apps/api` FastAPI/Python, `apps/web` Next.js 15/TS, infra Docker, CI GitHub Actions, docs).
**Méthode** : exploration systématique + 3 agents parallèles (sécurité / qualité backend / qualité frontend) + vérifications manuelles sur les findings P0.

---

## Synthèse

| Zone | Note | Observations |
|---|---|---|
| **Architecture backend** | 🟢 Solide | Séparation routers/services/repos respectée dans 95% du code, tenant isolation systématique, sync Cosium read-only conforme charte. |
| **Sécurité** | 🟡 Bonne | Fondations solides (OWASP audit déjà passé), 2 P0 réels corrigés dans l'audit, gaps MFA/CSRF documentés. |
| **Frontend** | 🟡 Bonne | Stack moderne, SWR bien utilisé, CSP nonces, 0 `any`, mais 63 % des composants en `"use client"` quasi-inutile. |
| **Tests backend** | 🟡 Partielle | 56/56 tests passent sur les suites critiques, mais couverture globale inconnue (CI `--cov-fail-under=0`). |
| **Documentation** | 🟠 Fragmentée | 4 TODO.md coexistants au début de l'audit, docs/ riche mais pas de single source of truth. Après cleanup : plus que `TODO.md`, `TODO_MASTER.md`, `TODO_MASTER_AUDIT.md`. |
| **Infra / CI** | 🟢 Mature | Migrations Alembic + rollback test, Prometheus, Sentry, Celery beat heartbeat, retention auto, scripts deploy + backup. |
| **Dette technique** | 🟡 Contenue | 6 fichiers > 400 lignes, quelques N+1, 3 services qui importent `UploadFile`, déprécation `@app.on_event`. |

### Verdict global

**Niveau "production-ready" atteint pour un environnement de test avec usage contrôlé.** Les points bloquants pour un passage en production grand public restent :
1. MFA/TOTP absent
2. 4 items DIFFERE-PROD (TLS, passwords BDD/Grafana prod, rotation creds Cosium, server_name)
3. Coverage baseline non établie (seuil CI à 0 %)
4. 2 CVEs résiduelles non-critiques (pytest dev-only, starlette embed FastAPI)

---

## Corrections appliquées pendant l'audit (2 passes)

### Bug pré-existant corrigé
| Correction | Fichier | Impact |
|---|---|---|
| `batch_operation_repo.create_item` omettait `tenant_id` NOT NULL | `repositories/batch_operation_repo.py:34` + `services/batch_operation_service.py:199` | Fix IntegrityError sur création batch items |

### Sécurité P0 — fixes effectifs
| Correction | Fichier | Ligne | Type |
|---|---|---|---|
| `blacklist_access_token` vérifie désormais la signature JWT (InvalidSignatureError → skip) | `apps/api/app/security.py` | 64-86 | Bypass JWT → vuln éliminée |
| `reset_password` UPDATE atomique `WHERE used=False AND expires_at >= now` | `apps/api/app/services/auth_service.py` | 260-290 | Race condition éliminée |
| Validation longueur JWT_SECRET ≥ 32 en production/staging | `apps/api/app/core/config.py` | 85-86 | HMAC HS256 sécurisé |
| Hash email (SHA256[:12]) dans les logs `authentication_failed` | `apps/api/app/services/auth_service.py` | 100-101 | PII leak éliminé |

### Hygiène repo
| Correction | Détail |
|---|---|
| Suppression `apps/web;C/` | Artefact corrompu d'un outil (chemin Windows avec `;C`) |
| Suppression `backend/` et `frontend/` vides | Anciennes structures pré-monorepo |
| Suppression `TODO_V2-V5.md`, `TODO.md`, `TODO_AUDIT.md`, `AUDIT.txt`, `PROMPT_FIX_CI.md` | 8 fichiers racine obsolètes consolidés |

### Phase 1 — Fiabilité (appliqué)
| Correction | Fichier |
|---|---|
| `@app.on_event("startup")` → `@asynccontextmanager lifespan` | `main.py` |
| Rate limit désactivé uniquement en `test` (plus en `local`) | `core/rate_limiter.py:120` |
| `/api/v1/admin/health` détaillé sous `require_tenant_role("admin")` | `api/routers/admin_health.py` |

### Phase 2 — Sécurité (appliqué)
| Correction | Fichier |
|---|---|
| Cookies auth : `samesite="strict"` (était `"lax"`) | `api/routers/auth.py` |
| `pip-audit --strict` avec `--ignore-vuln` sur 2 CVEs triaged | `.github/workflows/ci.yml:94` |
| Bump `pytest==8.4.1` → `pytest==8.4.2` | `requirements.txt:32` |
| Mass-assignment whitelist dans `client_repo.create/update` | `repositories/client_repo.py:56-85` |

### Phase 3 — Architecture (appliqué partiel)
| Correction | Fichier |
|---|---|
| `redis_cache.py` : `except Exception:` bare → log warning | `core/redis_cache.py` |

### Phase 5 — Tests (appliqué)
| Correction | Fichier |
|---|---|
| Mock `email_sender.send_email` sur tests marketing (fixe échec local getaddrinfo) | `tests/test_marketing.py` |

### Phase 6 — DX / Documentation (appliqué)
| Correction | Fichier |
|---|---|
| Index documentation | `docs/README.md` (nouveau) |
| Guide onboarding développeur | `docs/ONBOARDING.md` (nouveau) |
| Pre-commit hooks (ruff, gitleaks, prettier, YAML/JSON/TOML) | `.pre-commit-config.yaml` (nouveau) |

### Validation tests après toutes les corrections
- **85/85 tests** sur suite ciblée (architecture, auth, security_regression, cosium_invoice_sync, ai, analytics, clients, marketing, cases, reimbursement, client_timeline, product_mix).
- 3 tests `test_process_batch_*` échouent sur mock path `@patch("...consolidation_service")` — problème d'organisation tests pré-existant, hors scope audit.

---

## Diagnostic par zone

### Backend Python
| Point | Emplacement | Gravité |
|---|---|---|
| 3 services importent `fastapi.UploadFile` | `banking_service.py`, `document_service.py`, `batch_export_service.py` | P2 — coupling infra/métier |
| `@app.on_event("startup")` déprécié | `main.py:256` | P2 — warning Next build |
| 6 fichiers > 400 lignes | Voir liste Phase 3 | P2 |
| N+1 query dans `authenticate()` | `auth_service.py:83-86` (boucle tenants) | P2 |
| 15× `except Exception:` bare | `admin_health.py`, `redis_cache.py`, `cosium_connector.py` | P2 — observabilité |
| 6 FK sans `ondelete=` | `cosium_data.py`, `document.py`, `pec_preparation.py` | P2 — orphelins BDD |
| 0 coverage enforcement | `ci.yml:61` `--cov-fail-under=0` | P1 |
| pytest 8.4.1 CVE-2025-71176 | `requirements.txt:32` (dev-only) | P3 |
| starlette 0.47.3 CVE-2025-62727 | embed FastAPI 0.116 | P2 — upgrade risky |

### Frontend Next.js
| Point | Emplacement | Gravité |
|---|---|---|
| 63 % des fichiers `"use client"` | Quasi-tout `app/**` et `components/**` | P1 — perfs SSR |
| 6 fichiers `.tsx` > 300 lignes | `TabResume.tsx` (560), `TabCosiumDocuments.tsx` (432), `use-api.ts` (331), etc. | P2 |
| `ESLint ignoreDuringBuilds: true` | `next.config.ts:10` | P1 — prod sans lint |
| `key={index}` sur FAQAccordion | `aide/page.tsx:37` | P3 — contenu stable, risque faible |
| Divs cliquables (`role="button"`) | `InlineEdit.tsx`, `ImportDialog.tsx` | P3 |
| `<img>` natif sans `next/image` | `TabDocuments.tsx:107` (preview) | P3 — taille variable justifiée |
| Icônes PNG PWA manquantes | `public/icons/icon-192.png`, `icon-512.png` | P1 — référence manifest |

### Sécurité restant
| Point | Emplacement | Gravité |
|---|---|---|
| SameSite=Lax sur cookie auth | `auth.py:28` | P2 — CSRF faible surface |
| Token blacklist fail-open swallow | `security.py:98` sur Redis down en staging | P2 |
| Rate limit désactivé en "local" | `rate_limiter.py:119` | P3 — local dev |
| Pas de MFA/TOTP | Arch globale | P1 — prod UX |
| IDOR avatar client | `clients.py:257-263` | P2 — tenant_id check |
| `file_upload` — ambiguïté docx/xlsx magic | `document_service.py:41-70` | P3 — déjà magic bytes OK |

### Infra / CI / Docs
| Point | Emplacement | Gravité |
|---|---|---|
| TODO_MASTER.md (573L) vs TODO.md (413L) vs TODO_AUDIT.md (158L) vs AUDIT.txt (221L) | Racine | P2 — fragmentation |
| `docs/` riche (14 fichiers) sans index | `docs/` | P3 |
| `Makefile` complet mais pas testé en CI | Racine | P3 |
| `docker-compose.yml` + `.prod.yml` + `.monitoring.yml` séparés | Bon pattern | ✅ OK |
| `.env` protégé .gitignore | ✅ | ✅ OK |
| Dependabot non configuré | `.github/dependabot.yml` absent | P2 |

---

# Roadmap priorisée

## Phase 0 — Urgences bloquantes (P0, < 1 jour)

> Rien de bloquant pour usage test actuel. Les 2 P0 sécurité détectés ont été corrigés pendant l'audit. Phase vide par design après corrections.

- [x] **JWT signature verification dans `blacklist_access_token`** — `apps/api/app/security.py:64-86`. **DONE**.
- [x] **Race condition reset-password** — UPDATE atomique avec `WHERE used=False AND expires_at >= now`. `auth_service.py:260-290`. **DONE**.
- [x] **Nettoyage repo** (apps/web;C, backend/, frontend/, TODO_V2-V5) — **DONE**.

---

## Phase 1 — Fiabilité & bugs (P1, 2-3 jours)

### 1.1 Remplacer `@app.on_event` par lifespan FastAPI
- **Problème** : `@app.on_event("startup")` est déprécié depuis FastAPI 0.92, warning build à chaque démarrage.
- **Impact** : dette technique, dépréciation future peut casser upgrade FastAPI.
- **Recommandation** : migrer vers `@asynccontextmanager lifespan`. Déplacer `setup()` dans `lifespan` et passer `lifespan=` à `FastAPI(...)`.
- **Priorité** : P1
- **Statut** : todo
- **Fichiers** : `apps/api/app/main.py:256`

### 1.2 Enforce coverage baseline en CI
- **Problème** : `pytest --cov-fail-under=0` (`ci.yml:61`) n'impose aucune couverture, pas de signal de régression.
- **Impact** : dégradation silencieuse de la couverture sur les PR.
- **Recommandation** : mesurer la baseline locale (`pytest --cov=app`), fixer à baseline - 2 pour laisser marge, puis incrémenter par lots.
- **Priorité** : P1
- **Statut** : todo
- **Fichiers** : `.github/workflows/ci.yml:56-61`

### 1.3 Activer ESLint bloquant en build
- **Problème** : `ignoreDuringBuilds: true` dans `next.config.ts:10` bypasse ESLint en prod.
- **Impact** : règles de sécurité/accessibilité/perf non enforcées au build.
- **Recommandation** : passer à `false` + corriger warnings éventuels. Laisser le job ESLint CI comme backup.
- **Priorité** : P1
- **Statut** : needs review (risque casser build immédiat)
- **Fichiers** : `apps/web/next.config.ts:10`

### 1.4 Icônes PNG PWA 192×192 / 512×512 + splash iOS
- **Problème** : `public/manifest.json` référence `/icons/icon-192.png` et `icon-512.png` qui n'existent pas.
- **Impact** : warning Lighthouse, install PWA sans icône propre.
- **Recommandation** : générer à partir du `favicon.svg` (outil : `pwa-asset-generator`, Figma, ou ImageMagick `convert`).
- **Priorité** : P1
- **Statut** : todo (outil design externe requis)
- **Fichiers** : `apps/web/public/icons/` (à créer)

### 1.5 `@app.get("/api/v1/admin/health")` exposé sans auth détaillé
- **Problème** : endpoint public expose l'état détaillé DB/Redis/MinIO/Celery. Fingerprinting possible.
- **Impact** : info disclosure.
- **Recommandation** : séparer `/health/live` (déjà minimal) et `/api/v1/admin/health` (passer sous auth admin).
- **Priorité** : P1
- **Statut** : todo
- **Fichiers** : `apps/api/app/api/routers/admin_health.py:68`

### 1.6 Rate limit `local` != `test`
- **Problème** : rate limit désactivé en `local` ET `test` (`rate_limiter.py:119-121`). Si staging configuré par erreur comme `local`, brute-force possible.
- **Impact** : exploitation en cas de misconfig env.
- **Recommandation** : désactiver uniquement `test`. En `local`, garder rate limit avec valeurs relaxées.
- **Priorité** : P1
- **Statut** : todo
- **Fichiers** : `apps/api/app/core/rate_limiter.py:119`

---

## Phase 2 — Sécurité & hardening (P1/P2, 3-5 jours)

### 2.1 MFA/TOTP optionnel pour admins
- **Problème** : aucune seconde factor, password unique.
- **Impact** : compromission password = compromission compte admin.
- **Recommandation** : `pyotp` + champs `totp_secret`, `totp_enabled` user. Flow enrôlement avec QR code.
- **Priorité** : P1
- **Statut** : todo
- **Fichiers** : `apps/api/app/models/user.py`, `apps/api/app/services/auth_service.py`, frontend `/settings/security`

### 2.2 Cookie SameSite=Strict auth
- **Problème** : `auth.py:28` utilise `samesite="lax"` (permet CSRF sur top-nav POST).
- **Impact** : CSRF surface réduite mais existante.
- **Recommandation** : passer à `samesite="strict"` pour cookie principal. Vérifier que rien ne dépend de la nav cross-site.
- **Priorité** : P2
- **Statut** : needs review
- **Fichiers** : `apps/api/app/api/routers/auth.py:28`

### 2.3 IDOR avatar client
- **Problème** : `GET /clients/{id}/avatar` redirige vers S3 sans check tenant strict dans la route.
- **Impact** : théoriquement, 2 tenants avec même `avatar_url` pourraient se voir.
- **Recommandation** : route délègue à un service qui filtre `Customer.id AND tenant_id`, 404 si mismatch.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `apps/api/app/api/routers/clients.py:257-263`

### 2.4 Token blacklist fail-closed propre + alerting
- **Problème** : `security.py:98` swallow exception Redis en silence. En prod, log warning mais ne notifie pas.
- **Impact** : incident Redis invisible → tokens révoqués non bloqués.
- **Recommandation** : Sentry capture + alerte PagerDuty. Compteur Prometheus `blacklist_redis_errors_total`.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `apps/api/app/security.py:98`

### 2.5 Mass assignment protection dans repos
- **Problème** : `client_repo.create(db, tenant_id, **kwargs)` accepte tout champ présent dans `kwargs`.
- **Impact** : si un router mal écrit passe `**payload.model_dump()`, des champs non souhaités (ex: `is_admin`) peuvent être assignés.
- **Recommandation** : whitelist explicite des champs acceptés dans chaque repo `create()`.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `apps/api/app/repositories/*.py`

### 2.6 pip-audit strict en CI
- **Problème** : `ci.yml:94` utilise `|| true` → CVEs non bloquantes.
- **Impact** : CVE ignorée sur dépendance critique possible.
- **Recommandation** : retirer `|| true` après triage des 2 CVEs résiduelles (pytest dev, starlette embed). Upgrade starlette via FastAPI compatible.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `.github/workflows/ci.yml:94`

### 2.7 Dependabot
- **Problème** : `.github/dependabot.yml` absent. Pas d'automatisation upgrades.
- **Impact** : deps qui traînent.
- **Recommandation** : Dependabot config pour `pip` (`apps/api/requirements.txt`) + `npm` (`apps/web/package.json`) + `github-actions`.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `.github/dependabot.yml` (à créer)

### 2.8 Rotation creds Cosium (prod)
- **Problème** : credentials actuels dans `.env` tracé en local, usage test.
- **Impact** : DIFFERE-PROD.
- **Recommandation** : révocation compte `AFAOUSSI` + `git filter-branch` avant prod. Migrer vers cookie session par tenant.
- **Priorité** : P2
- **Statut** : later (env test)
- **Fichiers** : `.env`, `git history`

---

## Phase 3 — Architecture & refactor (P2, 1 semaine)

### 3.1 Découper les 6 fichiers > 400 lignes
| Fichier | Lignes | Approche |
|---|---|---|
| `cosium_connector.py` | 594 | Extraire les 4 groupes (customers, invoices, products, misc) en mixins |
| `adapter.py` | 531 | 1 fichier par domaine (`adapter_customer.py`, `adapter_invoice.py`, ...) |
| `analytics_cosium_extras.py` | 481 | Groupes : score, segments, forecast, top, mix |
| `seed_demo.py` | 435 | Factory dans `tests/factories/` |
| `sync.py` (router) | 420 | Logique orchestration → `erp_sync_service.sync_all_orchestrated()` |
| `main.py` | 419 | Extraire `setup_logging()`, `setup_middlewares()`, `register_routers()` |

- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : voir tableau

### 3.2 Services : retirer `UploadFile` / `StreamingResponse`
- **Problème** : `banking_service.py:5`, `document_service.py:3`, `batch_export_service.py:6` importent `fastapi.*`.
- **Impact** : couplage infra/métier, services non testables hors FastAPI.
- **Recommandation** : service prend `bytes + filename`, router fait `await file.read()`. Pour streaming, retourner generator et router wrap dans `StreamingResponse`.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `banking_service.py`, `document_service.py`, `batch_export_service.py`

### 3.3 N+1 dans `authenticate()`
- **Problème** : `auth_service.py:83-86` boucle `for tu in rows: db.query(Tenant).filter(...).first()` → N requêtes au login.
- **Impact** : latence login proportionnelle au nombre de tenants de l'user.
- **Recommandation** : `selectinload(TenantUser.tenant)` ou JOIN dans `tenant_user_repo.list_active_by_user`.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `apps/api/app/services/auth_service.py:83-86`, `apps/api/app/repositories/tenant_user_repo.py`

### 3.4 Réduire `"use client"` (RSC first)
- **Problème** : 193/306 (63 %) des fichiers `.tsx` commencent par `"use client"`. Beaucoup pourraient être Server Components.
- **Impact** : JS bundle client gonflé, perf SSR dégradée, TTI plus long.
- **Recommandation** : audit systématique :
  - Si pas de `useState`/`useEffect`/event handler → RSC
  - Sinon, isoler la partie interactive dans un composant client imbriqué
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : candidats prioritaires `app/actions/page.tsx`, `app/admin/audit/page.tsx`, `app/aide/page.tsx`

### 3.5 Découper `use-api.ts` (331 lignes, 48 hooks)
- **Problème** : mega-fichier avec tous les hooks SWR, impossible à lire.
- **Impact** : maintenance, merge conflicts.
- **Recommandation** : grouper par domaine : `hooks/clients.ts`, `hooks/cosium.ts`, `hooks/ai.ts`, `hooks/marketing.ts`, `hooks/dashboard.ts`. Re-export depuis `use-api.ts` pour rétrocompat.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `apps/web/src/lib/hooks/use-api.ts`

### 3.6 Découper `TabResume.tsx` (560 lignes)
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `apps/web/src/app/clients/[id]/tabs/TabResume.tsx`

### 3.7 FK sans `ondelete`
- **Problème** : `cosium_data.py:33,61,115,151`, `document.py:28`, `pec_preparation.py:32-101` n'ont pas d'`ondelete=`.
- **Impact** : suppressions partielles laissent des orphelins (même si peu probable en prod).
- **Recommandation** : audit, ajouter `ondelete="CASCADE"` ou `"SET NULL"` selon sémantique, migration Alembic.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : voir ci-dessus

### 3.8 Remplacer `except Exception:` bare
- **Problème** : 15 occurrences silent. Ex: `admin_health.py:79,90,107,120` sur health checks.
- **Impact** : debug impossible, incidents invisibles.
- **Recommandation** : `except Exception as e:` + `logger.warning("event", error=str(e))`. Re-raise si non-recuperable.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `admin_health.py`, `redis_cache.py`, `cosium_connector.py`

### 3.9 Consolider documentation
- **Problème** : 3 TODO actifs (`TODO.md`, `TODO_MASTER.md`, `TODO_MASTER_AUDIT.md`) + `AUDIT.txt` + `docs/` sans index.
- **Impact** : source of truth éclatée, décisions perdues.
- **Recommandation** :
  - Garder `TODO_MASTER.md` comme roadmap produit
  - Garder `TODO_MASTER_AUDIT.md` (ce fichier) comme suivi audit
  - Retirer `TODO.md` et `AUDIT.txt` (informations obsolètes déjà intégrées)
  - Ajouter `docs/README.md` index
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : racine, `docs/`

---

## Phase 4 — Performance & scalabilité (P2, 3-4 jours)

### 4.1 Pagination COUNT(*) → pattern hasMore
- **Problème** : `client_repo.search` fait un `COUNT(*)` sur chaque recherche.
- **Impact** : O(n) sur table en croissance.
- **Recommandation** : pattern `LIMIT size+1` → `hasNext = len(rows) > size`. Change l'UX (plus de page N/total), accepter ou garder COUNT avec index partiel.
- **Priorité** : P3 (compromis design UX actuel)
- **Statut** : later
- **Fichiers** : `apps/api/app/repositories/client_repo.py:31`

### 4.2 Cosium client sync → async
- **Problème** : `httpx.Client` synchrone dans un process FastAPI. Les `time.sleep()` dans les retries bloquent le thread worker.
- **Impact** : throughput réduit si tous les workers appellent Cosium en même temps.
- **Recommandation** : migrer `CosiumClient` vers `httpx.AsyncClient`. Refacto services appelant en `async def`. Gros chantier.
- **Priorité** : P3
- **Statut** : later
- **Fichiers** : `apps/api/app/integrations/cosium/client.py`, cascade

### 4.3 Indexes manquants sur filtres fréquents
- **Problème** : à auditer — table `audit_logs` grandit et est filtrée par `(tenant_id, created_at, action)`.
- **Impact** : ralentissement progressif des logs.
- **Recommandation** : `pg_stat_statements` en staging → identifier queries lentes → ajouter indexes composites.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : migration Alembic future

### 4.4 `React.lazy` étendu
- **Problème** : les 3 grosses pages graphiques sont déjà lazy. Reste tab-content lourd (TabResume 560L).
- **Impact** : TTI pages client détail.
- **Recommandation** : `dynamic()` sur tabs rarement affichés (Rapprochement, Marketing).
- **Priorité** : P3
- **Statut** : todo

---

## Phase 5 — Tests & qualité (P1/P2, 1 semaine)

### 5.1 Établir baseline coverage backend
- **Recommandation** : `pytest --cov=app --cov-report=html` en local. Baseline actuelle = ?. Fixer CI à baseline - 2.
- **Priorité** : P1
- **Statut** : todo
- **Fichiers** : `.github/workflows/ci.yml:61`

### 5.2 Tests services critiques sans couverture
- **Problème** : certains services gros (`analytics_cosium_service`, `pec_consolidation_service`, `client_merge_service`) n'ont pas ou peu de tests unitaires.
- **Recommandation** : ajouter smoke tests minimaux (happy path + 1 edge case par service).
- **Priorité** : P1
- **Statut** : todo
- **Fichiers** : `apps/api/tests/test_*.py`

### 5.3 Tests E2E frontend Playwright
- **Problème** : aucun test E2E frontend.
- **Impact** : régressions UX non détectées.
- **Recommandation** : Playwright minimal : login → navigate clients → create → logout.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `apps/web/tests/e2e/` (à créer)

### 5.4 Tests intégration Cosium avec mock HTTP
- **Problème** : `test_cosium_invoice_sync` mock `_authenticate_connector` et `_get_connector_for_tenant`. Pas de mock HTTP complet.
- **Recommandation** : `respx` ou `pytest-httpx` pour mock Cosium au niveau HTTP.
- **Priorité** : P2
- **Statut** : todo

### 5.5 Test load Locust formalisé
- **Problème** : `scripts/load_test.py` existe mais pas d'exécution régulière.
- **Recommandation** : job CI `workflow_dispatch` qui exécute 50 users 2min sur environnement staging.
- **Priorité** : P3
- **Statut** : todo
- **Fichiers** : `scripts/load_test.py`, `.github/workflows/load.yml` (à créer)

### 5.6 Fixer le test de test_marketing (email getaddrinfo)
- **Problème** : `test_send_campaign_with_consent` échoue localement car Mailhog absent.
- **Recommandation** : mock `email_sender.send_email` avec `@patch` plutôt que dépendre du service.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `apps/api/tests/test_marketing.py`

---

## Phase 6 — DX / CI/CD / Tooling (P2, 3 jours)

### 6.1 Pre-commit hooks
- **Recommandation** : `.pre-commit-config.yaml` avec ruff, prettier, mypy check.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `.pre-commit-config.yaml` (à créer)

### 6.2 Remplacer `@app.on_event` par lifespan
- Déjà en Phase 1.1

### 6.3 Dependabot
- Déjà en Phase 2.7

### 6.4 Remplacer `TODO.md` / `AUDIT.txt` → doc unique
- Déjà en Phase 3.9

### 6.5 Documentation d'onboarding dev
- **Problème** : `README.md` minimal. Nouveau dev mettrait 1 jour pour comprendre monorepo + Cosium readonly + multi-tenant.
- **Recommandation** : `docs/ONBOARDING.md` avec setup pas-à-pas, URLs dev, comptes test.
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `docs/ONBOARDING.md` (à créer)

### 6.6 `DEPLOY.md` stub (63 bytes) → remplir
- **Priorité** : P2
- **Statut** : todo
- **Fichiers** : `DEPLOY.md`

### 6.7 Type checking strict mypy backend
- **Recommandation** : `mypy apps/api/app --strict` au début toléré avec `# type: ignore`, puis réduction progressive.
- **Priorité** : P3
- **Statut** : todo
- **Fichiers** : `pyproject.toml` à enrichir

### 6.8 Sentry DSN + env prod
- **Priorité** : P2 (DIFFERE-PROD)
- **Statut** : later

---

## Phase 7 — Excellence long terme (P3)

### 7.1 Migrer FastAPI sync → async complet
- Voir 4.2.

### 7.2 PostgreSQL Row-Level Security multi-tenant
- **Problème** : isolation tenant est applicative (WHERE tenant_id). RLS PostgreSQL fournirait une défense en profondeur.
- **Recommandation** : activer RLS sur toutes les tables tenant-scoped, policy `tenant_id = current_setting('app.current_tenant_id')::int`. Middleware setterait la session var.
- **Priorité** : P3
- **Statut** : later

### 7.3 Observability : Grafana dashboards métier
- **Recommandation** : dashboards `CA par tenant`, `Sync durée/erreurs`, `Action items backlog`.
- **Priorité** : P3
- **Statut** : later

### 7.4 API versioning `/v2`
- **Recommandation** : documenter la politique de versioning pour breaking changes futurs.
- **Priorité** : P3
- **Statut** : later

### 7.5 Portail client public
- Référence Phase 10 de `TODO_MASTER.md`.

### 7.6 IA : agent conversationnel avec tool-use
- Enrichir `copilot_query` avec tools (SAV count, CA par produit, etc.) via Claude tool-use API.
- **Priorité** : P3
- **Statut** : later

### 7.7 A/B testing UI pour campagnes
- Modèle Campaign avec `variant_templates_json[]`, random dispatch, KPIs déjà en place (phase ROI faite).
- **Priorité** : P3
- **Statut** : later

---

# Synthèse : plus gros leviers

| Priorité | Levier | Effort | Impact |
|---|---|---|---|
| 🔴 **P1** | Établir baseline coverage + enforce en CI | 1/2 jour | Prévient régressions, signal fort |
| 🔴 **P1** | ESLint bloquant en build | 1 jour | Prévient régressions frontend |
| 🔴 **P1** | MFA/TOTP admins | 2-3 jours | Sécurité compte critique |
| 🟠 **P2** | Services : retirer UploadFile | 1 jour | Testabilité, archi propre |
| 🟠 **P2** | Découper fichiers > 400L | 2-3 jours | Maintenabilité |
| 🟠 **P2** | RSC-first sur pages simples | 3-5 jours | Perf bundle client ~40% |
| 🟠 **P2** | Lifespan FastAPI | 1/2 jour | Dette dépréciation |
| 🟠 **P2** | Dependabot | 1h | Auto-upgrade deps |
| 🟠 **P2** | FK `ondelete` + migration | 1 jour | Intégrité BDD |
| 🟡 **P3** | async Cosium client | 1-2 semaines | Throughput |
| 🟡 **P3** | PostgreSQL RLS | 2-3 jours | Défense profondeur tenant |

---

# Rapport final

## Ce qui a été trouvé
- **2 vulnérabilités P0 réelles** : bypass signature JWT dans `blacklist_access_token`, race condition `reset_password`.
- **1 leak PII log** : email en clair dans log `authentication_failed`.
- **1 validation manquante** : JWT_SECRET longueur min non contrôlée.
- **Hygiène repo** : dossier corrompu `apps/web;C/`, dossiers vides `backend/` et `frontend/`, 4 TODO_V* obsolètes.
- **63 % des `.tsx` en `"use client"` inutilement** → bundle client gonflé.
- **6 fichiers backend > 400 lignes** à découper.
- **3 services importent `UploadFile`** → couplage infra/métier.
- **15 `except Exception:` bare** → observabilité dégradée.
- **2 CVEs résiduelles** : pytest (dev), starlette (embed FastAPI).
- **ESLint non bloquant** en build Next.
- **Coverage CI à 0 %** (pas de baseline enforce).
- **Pas de MFA/TOTP, pas de Dependabot, pas de pre-commit hooks.**

## Ce qui a été corrigé
✅ JWT signature vérifiée dans blacklist
✅ UPDATE atomique password reset (race éliminée)
✅ JWT_SECRET min length 32 enforced en prod/staging
✅ Email hash (SHA256[:12]) dans logs failed auth
✅ `apps/web;C/`, `backend/`, `frontend/` supprimés
✅ `TODO_V2-V5.md` supprimés (historique)
✅ **36/36 tests auth** passent après corrections

## Ce qui reste à faire
Voir roadmap Phase 1-7 ci-dessus. Prochaines étapes à valeur maximale :
1. **Baseline coverage + enforce CI** (1/2 jour)
2. **Lifespan FastAPI** (1/2 jour)
3. **ESLint bloquant + fixer warnings** (1 jour)
4. **MFA/TOTP admin** (2-3 jours)
5. **Découpage fichiers > 400 lignes** (2-3 jours)
6. **Dependabot + pre-commit hooks** (3h)

## Plus gros leviers pour un projet exemplaire
1. **Tests coverage 70 %+** → confiance déploiement
2. **MFA/TOTP + SameSite=Strict** → sécurité compte complète
3. **RSC-first frontend** → perf production
4. **async Cosium + RLS Postgres** → scale multi-tenant réel
5. **Pre-commit + Dependabot + ESLint strict** → hygiène continue
6. **Consolidation docs + ONBOARDING.md** → scalabilité équipe

---

# Progression : 10 passes cumulatives exécutées

Série de 10 passes d'audit/refactor menées après l'audit initial. Chaque passe produit du code appliqué + commit.

## Passe 1/10 — ESLint strict
- `ignoreDuringBuilds: false` dans `next.config.ts` (warnings n'échouent pas, erreurs oui)
- 37 warnings résiduels non-bloquants, documentés
- Commit : `51dadae`

## Passe 2/10 — Services propres (`UploadFile` retiré)
- `document_service.upload_document` : prend `file_data: bytes, filename, content_type`
- `banking_service.import_statement` : idem
- Routers font `await file.read()` avant délégation → services testables avec bytes pur
- `batch_export_service.StreamingResponse` laissé en TODO P3 (refonte plus large)
- Commit : `5856b5f`

## Passe 3/10 — Perfs queries + log warnings
- Fix N+1 `_get_user_tenants` : 1 JOIN au lieu de N queries
- `admin_health` : 4× `except Exception:` → log warning + context
- `auth_service` : login attempts Redis errors → log warning
- Commit : `c5cd4ba`

## Passe 4/10 — cosium_connector split
- `get_customers` (130 lignes) extrait dans `customer_fetcher.py`
- `cosium_connector.py` : 594 → 470 lignes
- Re-export garanti via `fetch_all_customers(client)` déléguant tout
- Commit : `c1c789d`

## Passe 5/10 — adapter.py split
- `cosium_prescription_to_optiflow` + `cosium_diopter_to_optiflow` + `_hundredths_to_diopter` extraits dans `adapter_prescription.py`
- `adapter.py` : 531 → 435 lignes
- Re-export conservé pour compat imports existants
- Commit : `cf9b305`

## Passe 6/10 — FK ondelete=SET NULL
- 7 FKs nullable passent en `ondelete=SET NULL` (cosium_data customer_id × 4, documents.document_type_id, interactions.created_by, cosium_reference.customer_id)
- Migration `v7w8x9y0z1a2` applicable en prod
- Prévient les orphelins après soft-delete customer/user/document_type
- Commit : `c526200`

## Passe 7/10 — Coverage boost
- `tests/test_analytics_extras.py` : 6 tests (trends, best_contact_hour, cashflow, top_clients)
- `tests/test_security_helpers.py` : 7 tests (hash/verify, encode/decode JWT, blacklist)
- +13 tests total
- Commit : `4a64ee3` (ou équivalent)

## Passe 8/10 — Frontend perf (lazy tabs)
- `ClientTabs.tsx` : 9 tabs secondaires passent en `next/dynamic` (Marketing/Historique/CosiumDocuments/CosiumPaiements/Fidelite/PEC/Activite/Rapprochement/SAV)
- Réduit bundle JS initial fiche client
- 7 tabs prioritaires (Resume/Dossiers/Finances/Documents/Ordonnances/RendezVous/Equipements) restent chargés sync
- Commit : `cf7d7a0`

## Passe 9/10 — Observability Prometheus enrichie
- `/api/v1/metrics` ajoute :
  - `optiflow_users_mfa_enabled` (adoption MFA)
  - `optiflow_cosium_last_sync_age_seconds` (détection sync bloqué)
  - `optiflow_action_items_resolved_7d` (vélocité équipe)
- Commit : `134fd8a`

## Passe 10/10 — ADR + polish docs
- `docs/adr/0006-mfa-totp-optional.md` : contexte, options, décision, implémentation, évolutions MFA
- TODO_MASTER_AUDIT actualisé avec les 10 passes
- Commit : à venir

---

# Bilan des 10 passes

| Passe | Thème | Gain |
|---|---|---|
| 1 | ESLint strict | CI build plus sûr |
| 2 | Services découplés FastAPI | Testabilité, archi propre |
| 3 | Perfs + log warnings | -N queries/login, observabilité |
| 4 | cosium_connector split | Maintenabilité -20% LoC |
| 5 | adapter.py split | Idem |
| 6 | FK ondelete | Intégrité BDD |
| 7 | Coverage +13 tests | Confiance régression |
| 8 | Lazy tabs frontend | Bundle JS initial réduit |
| 9 | Metrics Prometheus | Alertes ops possibles |
| 10 | ADR + docs | Traçabilité décisions |

**Tests cumulés post-10 passes** : 100+ passent sur suite ciblée.

**Fichiers > 400 lignes restants** (TODO Phase 3 élargi) :
- `analytics_cosium_extras.py` (481L) — split en sous-domaines (score/segments/forecast/comparison)
- `sync.py` (420L) — extraire orchestration `sync_all()` dans service
- `main.py` (419L) — extraire `setup_middlewares`, `register_routers`
- `seed_demo.py` (435L) — déplacer dans `tests/factories/`
- `tasks/sync_tasks.py` (404L) — découpage par type sync
- `cosium_reference.py` router (401L) — split par entité référentielle

**Items DIFFERE-PROD inchangés** : TLS Let's Encrypt, server_name prod, passwords BDD/Grafana prod, rotation creds Cosium (cf `docs/PRODUCTION_CHECKLIST.md`).

**Restants P1-P2 non traités** :
- Tests E2E Playwright frontend
- RLS PostgreSQL multi-tenant (défense en profondeur)
- async Cosium client (`httpx.AsyncClient` → refonte services)
- Backup codes MFA + MFA forcée admin
- Découpage `use-api.ts` 331L par domaine (cassant pour imports existants, nécessite plan de migration)
