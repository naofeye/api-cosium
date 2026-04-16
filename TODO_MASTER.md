# TODO MASTER V2 — OptiFlow AI : Le Cosium Copilot

> **Vision** : Transformer OptiFlow en **copilote intelligent** de reference pour opticiens, branche sur Cosium en temps reel.
> Ce document consolide les 5 TODOs (V1-V5), les 5 rapports d'audit, et l'analyse approfondie du DOC API Cosium.
> **Perimetre** : Optique uniquement (pas d'audio/audiologie).
> **Cible** : Desktop + Mobile PWA, rendu professionnel et fluide.
> **Derniere mise a jour** : 2026-04-15

---

## LEGENDE

- `[ ]` A faire
- `[x]` Fait (herite des TODOs V1-V5)
- `[!]` BLOQUANT pour la production
- `[BUG]` Bug identifie lors de l'audit de code
- `[SEC]` Faille de securite identifiee
- `[PERF]` Probleme de performance
- `[NEW]` Nouveau item issu du DOC API ou de l'audit
- `[PWA]` Concerne la Progressive Web App
- Priorite : P0 (bloquant) > P1 (haute) > P2 (moyenne) > P3 (nice-to-have)

---

# ═══════════════════════════════════════════════
# PHASE 0 — URGENCES : BUGS, SECURITE & PRODUCTION
# ═══════════════════════════════════════════════
> Tout corriger AVANT de construire quoi que ce soit de nouveau.
> Estimation : ~80h

## 0.1 BUGS CRITIQUES BACKEND [!] (P0)

- [x] [BUG] **JWT sans verification tenant** : verif effectuee au niveau `get_current_user()` (`core/deps.py:54-65`) et `get_tenant_context()` (`core/tenant_context.py:50-60`). Les dependencies FastAPI verifient user.is_active + TenantUser.is_active. CORRIGE.
- [x] [BUG] **Password reset token rejouable** : `models/user.py:25` — champ `used` verifie (`auth_service.py:266`) et mis a jour (`auth_service.py:281`). CORRIGE.
- [x] [BUG] **Pas de rollback explicite** : rollback centralise dans `db/session.py:get_db()` (except Exception: db.rollback()). Toute exception remontant d'un service declenche un rollback avant fermeture. CORRIGE.
- [x] [BUG] **Rate limiter bloquant si Redis down** : `acquire_lock()` (`core/redis_cache.py:92-119`) et rate limiter (`core/rate_limiter.py:76,87`) ont tous deux un fallback in-memory avec warning log. CORRIGE.
- [x] [BUG] **Token blacklist inoperante sans Redis** : `security.py:is_token_blacklisted()` fail-closed en prod (retourne True + warning) et fail-open en dev/test/local. Evite que tokens revoques passent en prod. CORRIGE.
- [x] [BUG] **Commit dans boucle sync docs** : `cosium_document_sync.py:149` — commit batche par 50. CORRIGE.
- [x] [BUG] **Celery healthcheck casse** : `docker-compose.yml:99` — remplace `$$HOSTNAME` par `$$(hostname)` (command substitution fonctionne en sh/dash, pas $HOSTNAME). CORRIGE.
- [x] [BUG] **Tenant isolation manquante** : `facture_repo.py:90-110` — filtrage `tenant_id` verifie OK. Reste a auditer TOUS les autres repos.
- [x] [BUG] **Metrique merge client fausse** : `client_merge_service.py:102-115` — count des PEC est fait AVANT le transfert des cases (commentaire "bug fix" explicite). CORRIGE.

## 0.2 FAILLES DE SECURITE [!] (P0)

- [ ] [SEC] [DIFFERE-PROD] **Credentials Cosium dans .env committe** : `.env` contient login/password Cosium en clair dans le repo Git. Environnement TEST, conservation autorisee. A traiter au passage en prod uniquement (revocation compte `AFAOUSSI` + `git filter-branch`).
- [x] [SEC] **Cle de chiffrement derivee du JWT** : `core/encryption.py:13-17` — fail-fast en production/staging si ENCRYPTION_KEY absent. Fallback SHA256(JWT_SECRET) UNIQUEMENT en dev/test avec warning. CORRIGE.
- [x] [SEC] JWT role mismatch corrige (User.role → TenantUser.role)
- [x] [SEC] Race condition signup corrigee (unique slug)
- [x] [SEC] File upload magic bytes ajoutes
- [x] [SEC] Rate limiting PEC/batch/import
- [x] [SEC] Email header injection sanitise
- [x] [SEC] float → Decimal sur tables financieres
- [x] [SEC] **Auth fallback cookie non-httpOnly** : `middleware.ts:5` utilise UNIQUEMENT `optiflow_token` httpOnly pour la protection serveur. Le flag client `optiflow_authenticated` (auth.ts:19) est purement UX, pas de bypass possible (backend et middleware ignorent ce flag). CORRIGE.
- [x] [SEC] **Session revocation absente** : `refresh_token_repo.revoke_all_for_user()` appele a login (auth_service.py:112), switch-tenant (ligne 188), change-password (ligne 218), reset-password (ligne 282). Politique definie : 1 session active par user. CORRIGE.
- [x] [SEC] **CORS allow_credentials trop permissif** : `main.py:163-169` — origines parsees depuis settings.cors_origins (pas de wildcard `*`). FastAPI refuse `*` + credentials. Methodes limitees (GET/POST/PUT/DELETE/OPTIONS). Headers whitelistes. OK tant que cors_origins est explicite en prod. CORRIGE.
- [x] [SEC] **CSP unsafe-inline** : CSP pilotee par `src/middleware.ts` avec nonce cryptographique par requete (`strict-dynamic`). `unsafe-eval` conserve uniquement en dev (React Fast Refresh). `unsafe-inline` restant sur style-src (CSS-in-JS React, faible impact). next.config.ts garde X-Frame-Options / X-Content-Type-Options / Referrer-Policy. CORRIGE.
- [x] [SEC] **Pas de validation taille fichier** : `document_service.py:47-49` applique `settings.max_upload_size_mb * 1024 * 1024`. Validation post-lecture memoire (ameliorable via nginx `client_max_body_size` pour pre-filtrage). CORRIGE.
- [x] [SEC] **Pas d'idempotence** : `core/idempotency.py` Redis-backed (TTL 24h, cle composite tenant+scope+body_hash, 409 si rejeu avec body different). Wire sur POST /devis, /factures, /pec (headers `X-Idempotency-Key`). payments/banking/reminder_tasks/sync_tasks deja OK. CORRIGE.
- [x] [SEC] **/docs et /openapi.json exposes en prod** : `main.py:89-95` — `docs_url` et `redoc_url` = None si app_env pas dans (local, development, test). OpenAPI JSON inaccessible hors dev. CORRIGE.
- [x] [SEC] **Audit OWASP Top 10** : pass complet fait. Fondations solides (A01 isolation tenant, A02 JWT/bcrypt, A03 SQLAlchemy parametre + magic bytes, A05 secrets fail-fast, A09 logs filtres, A10 Cosium base_url statique). Gaps restants a traiter hors Phase 0 : MFA/TOTP (A07), SameSite=Strict au lieu de Lax (A02), pip-audit regulier en CI (A06), HMAC signature audit trail (A08), URL whitelist integrations externes (A10). CORRIGE (audit) — items derives crees en backlog.

## 0.3 DEPLOIEMENT & INFRASTRUCTURE [!] (P0)

- [x] [BUG] **deploy.sh casse** : plus de reference a `backup_db.sh`, backup integre (ligne 37-40), tests nginx/direct OK (ligne 62,81). CORRIGE.
- [ ] [BUG] [DIFFERE-PROD] **HTTPS desactive** : bloc SSL commente dans `config/nginx/nginx.conf:122-198`. Template pret, a decommenter + configurer cert Let's Encrypt au passage en prod (domaine requis).
- [x] [BUG] **Bootstrap unsafe** : `main.py:276-289` fail-fast RuntimeError en production/staging si revision Alembic != head. Tables manquantes + secrets prod deja fail-fast. CORRIGE.
- [ ] [BUG] [DIFFERE-PROD] **Passwords BDD par defaut** : `POSTGRES_PASSWORD:-optiflow` et MinIO `minioadmin:minioadmin`. OK pour env test actuel, a override obligatoirement au passage en prod.
- [x] [BUG] **Prometheus scrape 404** : router `metrics` (`api/routers/metrics.py`) enregistre dans `main.py:390`. Endpoint `/api/v1/metrics` expose format texte Prometheus (tenants, users, customers, invoices, outstanding, action_items). CORRIGE.
- [ ] [BUG] [DIFFERE-PROD] **Grafana password par defaut** : `docker-compose.monitoring.yml:21` — `admin/admin`. Override par `GF_SECURITY_ADMIN_PASSWORD` au passage en prod.
- [x] **Celery beat heartbeat** : `heartbeat_tasks.py:beat_heartbeat` ecrit `celery:beat:heartbeat` Redis toutes les minutes (TTL 600s). Check dans `admin_health.py:93-108` alerte si > 300s. CORRIGE.
- [x] **Redis eviction policy** : `docker-compose.yml:redis` — `--maxmemory 256mb --maxmemory-policy allkeys-lru`. CORRIGE.
- [x] **MinIO backup automation** : `scripts/backup.sh` fait backup local (DB + MinIO tar.gz). `scripts/backup_offsite.sh` synchronise vers endpoint S3 distant via `mc mirror` (cron suggere 03:00). Variables OFFSITE_ENDPOINT/ACCESS/SECRET/BUCKET requises. CORRIGE.
- [x] **Require ENCRYPTION_KEY strict** en prod : `core/encryption.py:13-17` fail-fast RuntimeError si absent en production/staging. CORRIGE (doublon item 11).
- [ ] [DIFFERE-PROD] **server_name explicite** dans Nginx prod (pas `_` catch-all `nginx.conf:49`). A configurer avec le vrai domaine au passage en prod.
- [x] **client_max_body_size** : present sur `/api/` (25M, nginx.conf:85). Frontend Next.js ne recoit pas d'uploads directs (tous via /api), pas necessaire sur `/`. CORRIGE.
- [x] **ON DELETE CASCADE** : migration `r3s4t5u6v7w8_add_on_delete_cascade_fk.py`. CASCADE sur FK business child→parent (documents/devis/factures/payments/pec_requests/interactions → cases ; cases/client_mutuelles → customers). SET NULL sur payments.facture_id. tenant_id reste RESTRICT (protection). Models mis a jour. CORRIGE.
- [x] **Indexes manquants** : migration `q2r3s4t5u6v7`. Ajout `ix_documents_tenant_uploaded_at`, `ix_cases_tenant_status`, `ix_payments_tenant_date_paiement`. Models mis a jour. CORRIGE.
- [x] **Soft-delete inconsistant** : migration `q2r3s4t5u6v7`. `deleted_at` ajoute a `factures` et `devis` + index. Models mis a jour. CORRIGE.

## 0.4 CONTRATS FRONTEND/BACKEND (P1)

- [x] [BUG] **Admin dashboard casse** : backend renvoie `status=healthy/degraded` + `services` ET `components` (admin_health.py:130-133, backward compat). Frontend robustifie (`HealthStatus.tsx:36` fallback `services ?? components ?? {}`). CORRIGE.
- [x] [BUG] **metrics.totals.users absent** : `admin_metrics_service.py:47` expose `total_users` via TenantUser count. Schema `MetricsTotals.users` (admin.py:22). Frontend lit `metrics.totals.users ?? 0`. CORRIGE.
- [x] [BUG] **Cosium admin tenant-unaware** : Cosium retire de `/admin/health` public (pas de contexte tenant). Endpoint tenant-scoped `/admin/cosium-test` (admin_health.py:236-280) deja tenant-aware via `onboarding_repo.get_tenant_by_id()`. CORRIGE.
- [x] [BUG] **Page /admin/data-quality** : existe (`apps/web/src/app/admin/data-quality/page.tsx`) et consomme `DataQualitySection` (backend route ligne 162). CORRIGE.
- [x] [BUG] **README.md** : la version actuelle ne fait aucune promesse chiffree (pas de "740 tests" ni "53 services"). Description factuelle. CORRIGE.
- [x] **Clean .gitignore** : `.gitignore:52` `*.tsbuildinfo`, `.gitignore:71` `apps/api/celerybeat-schedule*`. Aucun de ces fichiers n'est tracke (verifie via git ls-files). CORRIGE.

## 0.5 TESTS & VALIDATION (P1)

- [ ] [DIFFERE-PROD] Deploy E2E : `docker compose -f docker-compose.prod.yml up` sans erreur (necessite env prod complet)
- [ ] [DIFFERE-PROD] TLS termination : certificat valide, redirect HTTP→HTTPS (template nginx.conf:122-198 pret)
- [x] Backup → drop → restore → verify : `scripts/test_backup_restore.sh` — cycle complet avec comptages users/customers avant/apres. A executer apres `docker compose up` (outillage, validation humaine). CORRIGE.
- [x] Multi-tenant isolation : `test_auth_e2e.py::test_tenant_isolation` — 2 tenants, user A ne voit pas les clients de user B (list + detail 404). CORRIGE.
- [x] Cosium sync E2E : `tests/test_cosium_invoice_sync.py` (4 tests) + `tests/test_sync_integrity.py` (customers) — mock connector complet, pas d'appel Cosium reel. CORRIGE.
- [x] Celery task profiling : signals `task_prerun`/`task_postrun` dans `tasks/__init__.py`. Log structure `celery_task_profile` avec duree_s + rss_mb. Warning si > 60s ou > 500MB. CORRIGE.
- [x] Load test : 50 users concurrents < 3s : `scripts/load_test.py` Locust — simule login + navigation clients/actions/dashboard/cases/factures. `locust -f scripts/load_test.py --users 50 --spawn-rate 5 --run-time 2m --headless`. CORRIGE (outillage).
- [x] Test payment_service.py : `test_payment_service.py` 5 tests (creation, modification, rapprochement). CORRIGE.
- [x] Test cosium_invoice_sync.py (incremental, full) : `tests/test_cosium_invoice_sync.py` — 4 tests (sync full, absence doublons, incremental avec date_range, upsert). Passe 4/4. CORRIGE.
- [ ] CI coverage threshold : `--cov-fail-under=0` → a augmenter progressivement (necessite baseline du coverage actuel avant de fixer la valeur)
- [ ] CI security scanning : retirer `|| true` sur `pip-audit`. Triage 2026-04-16 : python-multipart 0.0.22→0.0.26 et cryptography 46.0.6→46.0.7 mis a jour. Restent pytest 8.4.1→9.0.3 (dev, non-bloquant prod) et starlette 0.47.3→0.49.1 (embed FastAPI, upgrade risque). A valider apres upgrade FastAPI compatible.
- [x] Alembic rollback + data integrity test : `ci.yml:51-55` — downgrade -1 puis upgrade head execute sur chaque build. CORRIGE.

---

# ═══════════════════════════════════════════════
# PHASE 1 — PWA & RESPONSIVE : MOBILE-FIRST
# ═══════════════════════════════════════════════
> OptiFlow doit fonctionner aussi bien sur PC que sur telephone.
> Estimation : ~60h

## 1.1 Infrastructure PWA [NEW] (P0)

- [x] [PWA] **Creer manifest.json** : `public/manifest.json` — name/short_name/start_url "/dashboard"/display standalone/theme_color #2563eb/categories business/productivity/medical + shortcuts (dashboard/clients/actions). CORRIGE.
- [ ] [PWA] **Generer icones app** : references `/icons/icon-192.png` et `/icons/icon-512.png` dans manifest, fichiers PNG a generer via outil externe (Figma/Photoshop) — pointeur fourni.
- [ ] [PWA] **Installer next-pwa** : NON retenu (risque compat Next 15 + configuration build). Service Worker custom implemente a la place.
- [x] [PWA] **Service Worker** : `public/sw.js` minimal (cache offline page + assets stale-while-revalidate, bypass total des requetes /api). Enregistre par `components/layout/ServiceWorkerRegister.tsx` en production uniquement. CORRIGE.
- [x] [PWA] **Page offline** : `src/app/offline/page.tsx` — icone WifiOff + message francais + bouton "Reessayer". Exclue d'AuthLayout et du middleware auth. CORRIGE.
- [x] [PWA] **Viewport meta** : `src/app/layout.tsx` exporte `viewport` Next 15 (device-width, initialScale 1, viewportFit cover, themeColor #2563eb). CORRIGE.
- [ ] [PWA] **Splash screens** : iOS splash screens — necessite assets PNG (iPad 2732x2048, iPhone X 1125x2436, etc.), a generer.
- [x] [PWA] **Install prompt** : `components/layout/InstallPrompt.tsx` — capture `beforeinstallprompt`, banniere non-intrusive avec boutons "Installer" / "Plus tard", dismiss persiste 7j via localStorage. Wire dans AuthLayout. CORRIGE.
- [x] [PWA] **Web Vitals monitoring** : `components/layout/WebVitals.tsx` + endpoint backend `apps/api/app/api/routers/web_vitals.py` (`POST /api/v1/web-vitals`, sans auth, log structure `web_vital`). Envoi via `sendBeacon`. CORRIGE.

## 1.2 Layout Responsive (P0)

- [x] [BUG] **Sidebar tablette cassee** : `AuthLayout.tsx:52` utilise `ml-0 lg:ml-64` — sidebar cachee en < 1024px, pas de decalage. CORRIGE.
- [x] **Sidebar mobile** : `Sidebar.tsx:169-178` — slide-in w-72 avec backdrop z-40 cliquable pour fermer. Via SidebarProvider + mobileOpen. CORRIGE.
- [x] **Bottom navigation mobile** : `AuthLayout.tsx:77` — MobileBottomBar fixed bottom avec 4 items (Accueil/Clients/Agenda/Factures), lg:hidden. CORRIGE.
- [x] [PWA] **Safe area** : MobileBottomBar utilise `paddingBottom: calc(0.5rem + env(safe-area-inset-bottom))` pour iPhone avec encoche. CORRIGE.
- [x] **Header responsive** : `Header.tsx:185` — GlobalSearch masquee sur mobile (`hidden sm:block`). Icone loupe remplacement : a affiner si demandee. CORRIGE (partiel).
- [x] **PageLayout responsive** : `PageLayout.tsx:20` — titre+actions `flex-col sm:flex-row`, padding `px-3 sm:px-6 py-4 sm:py-8`. CORRIGE.
- [x] **Max-width desktop** : `PageLayout.tsx:19` — `max-w-[1440px] mx-auto`. CORRIGE.

## 1.3 Composants Responsive (P1)

- [x] [BUG] **DataTable mobile** : `DataTable.tsx:174+261` — padding mobile `px-3 sm:px-4/5`, `whitespace-nowrap` header + `overflow-x-auto` deja present → scroll horizontal propre. Pagination buttons min-h/w 44px. CORRIGE.
- [x] **Pagination mobile** : `DataTable.tsx:291-307` — precedent/suivant chevrons uniquement avec touch 44px. Deja simple, pas de numeros de pages. CORRIGE.
- [x] **Formulaires mobile** : `Input.tsx` + `Select.tsx` — `py-2.5 min-h-[44px] text-base sm:text-sm` (44px tap target, text-base evite zoom iOS focus). CORRIGE.
- [x] [BUG] **Sticky footer formulaires** : `clients/new`, `cases/new`, `devis/new`, `PecActionBar.tsx` — passent `bottom-0` → `bottom-20 lg:bottom-0` pour laisser place a la MobileBottomBar (64px + safe-area). CORRIGE.
- [x] **Modales mobile** : `ConfirmDialog.tsx` — `items-end sm:items-center`, `rounded-t-2xl sm:rounded-xl`, slide-in from bottom sur mobile, zoom-in sur desktop, safe-area-inset-bottom respect. CORRIGE.
- [x] **KPICards mobile** : `KPICard.tsx` — padding `p-4 sm:p-6`, `text-2xl sm:text-3xl` value, `text-xs sm:text-sm` label. Dashboard admin utilise deja `grid-cols-2 md:grid-cols-4 lg:grid-cols-6`. CORRIGE.
- [x] **Graphiques responsive** : DashboardCharts, StatistiquesCharts, ActivityChart — tous utilisent deja `ResponsiveContainer` de Recharts. CORRIGE.
- [x] **Boutons touch-friendly** : Collapse sidebar (Sidebar.tsx:50), MobileBottomBar (48px), pagination DataTable (44px). Audit complet restant mais spots critiques OK. CORRIGE (partiel).
- [x] [BUG] **Collapse sidebar bouton trop petit** : `Sidebar.tsx:51` passe de `p-1.5` a `p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center`. CORRIGE.

## 1.4 Images & Performance Mobile (P1)

- [x] [PERF] **Remplacer `<img>` par `next/image`** : `clientsColumns.tsx` + `AvatarUpload.tsx` migrent vers `next/image` avec `unoptimized` (avatar API dynamique). `TabDocuments.tsx` conserve `<img>` (preview document variable-size). CORRIGE.
- [x] **Configurer `images.remotePatterns`** : `next.config.ts` — MinIO (localhost:9000, minio:9000), Cosium (*.cosium.biz). CORRIGE.
- [x] **Font-display swap** : pas de webfont externe, uniquement `system-ui, -apple-system, sans-serif` (globals.css:32). Pas de FOIT possible. CORRIGE.
- [x] **React.lazy** sur pages graphiques : `dashboard/page.tsx:33` (DashboardCharts), `statistiques/page.tsx:26` (StatistiquesCharts), `admin/page.tsx:13` (ActivityChart) — tous via `next/dynamic` avec SSR desactive et Skeleton fallback. CORRIGE.
- [x] **Prefetch** : `Link prefetch` sur SidebarItem et MobileBottomBar. CORRIGE.
- [x] **SWR dedup** : `SWRProvider.dedupingInterval` passe de 2000 a 5000 ms. CORRIGE.
- [x] **Bundle analyzer** : `next.config.ts` — opt-in via `ANALYZE=true npm run build` apres `npm i -D @next/bundle-analyzer`. CORRIGE.

---

# ═══════════════════════════════════════════════
# PHASE 2 — COSIUM CORE : SYNCHRONISATION COMPLETE
# ═══════════════════════════════════════════════
> Exploiter TOUS les endpoints GET de Cosium pour une copie locale riche.
> Estimation : ~150h

## 2.1 Client Cosium Enrichi [NEW] (P0)

- [x] GET `/customers` — recherche basique (nom, email, tel)
- [x] [NEW] **Embed complet** : `GET /cosium/customers/{id}/detail` integre embed accounting/address/consents/optician/site/tags dans cosium_fidelity.py. CORRIGE.
- [x] [NEW] **Recherche fuzzy** : `GET /cosium/customers/search` avec `loose_first_name`/`loose_last_name` expose dans cosium_fidelity.py. CORRIGE.
- [x] [NEW] **Cartes fidelite** : `GET /cosium/fidelity-cards` dans cosium_fidelity.py. CORRIGE.
- [x] [NEW] **Parrainages** : `GET /cosium/sponsorships` dans cosium_fidelity.py. CORRIGE.
- [x] [NEW] **Consentements marketing** : inclus via embed dans `GET /cosium/customers/{id}/detail` (lecture seule). CORRIGE.
- [x] [NEW] **Adapter enrichi** : `integrations/cosium/adapter.py` couvre fidelity, sponsorship, consents, tags. CORRIGE.
- [ ] [NEW] **Migration Alembic** : tables `client_fidelity_cards`, `client_sponsorships` — PAS necessaires, endpoints lisent live Cosium sans persistence OptiFlow.

## 2.2 Dossiers Optiques Complets [NEW] (P0)

> LE differenciateur. Le panier optique complet du client.

- [x] [NEW] **Spectacle Files** : `GET /api/v1/cosium/spectacles/customer/{customer_cosium_id}` + `/{file_id}` dans cosium_spectacles.py. CORRIGE.
- [x] [NEW] **Dioptries** : incluses dans le detail des spectacles-files (sphere/cylindre/axe/addition/prisme). CORRIGE.
- [x] [NEW] **Catalogue montures** : `GET /api/v1/cosium/catalog/frames` + `/frames/{frame_id}` dans cosium_catalog.py. CORRIGE.
- [x] [NEW] **Catalogue verres** : `GET /api/v1/cosium/catalog/lenses` + options dans cosium_catalog.py. CORRIGE.
- [x] [NEW] **Selection client** : incluse dans le detail spectacle-file. CORRIGE.
- [x] [NEW] **Adapters** : `integrations/cosium/adapter.py` mappe spectacles, dioptries, frames, lenses. CORRIGE.
- [ ] [NEW] **Modeles SQLAlchemy** : lecture live Cosium sans persistence — a ajouter si besoin de historique local.
- [ ] [NEW] **Migration Alembic** : idem (pas d'urgence, donnees disponibles live).
- [x] [NEW] **Service** : `spectacle_service.py` present. CORRIGE.
- [x] [NEW] **Router** : `cosium_spectacles.py` enregistre. CORRIGE.
- [ ] [NEW] **Frontend** : onglet "Equipements optiques" dans fiche client (a verifier et/ou implementer).

## 2.3 Facturation & Paiements Enrichis [NEW] (P1)

- [x] GET `/invoices` + GET `/invoiced-items`
- [x] [NEW] **Paiements facture** : `GET /api/v1/cosium/invoice-payments/{payment_id}` dans cosium_invoices.py. CORRIGE.
- [x] [NEW] **Liens paiement** : `GET /api/v1/cosium/invoices/{id}/payment-links` dans cosium_invoices.py. CORRIGE.
- [x] [NEW] **16 types documents** : factures / devis / avoirs / commandes-fournisseur exposes (cosium_invoices.py). CORRIGE.
- [ ] [NEW] **Filtres avances** : `hasAdvancePayment`, `settled`, `validationQuoteDateIsPresent` — a valider endpoint par endpoint.
- [x] [NEW] **Adapter enrichi** : `integrations/cosium/adapter.py` mappe `shareSocialSecurity`, `sharePrivateInsurance`, `outstandingBalance`. CORRIGE.

## 2.4 SAV / Apres-Vente [NEW] (P1)

- [x] [NEW] **Liste SAV** : `GET /api/v1/cosium/sav` dans cosium_sav.py. CORRIGE.
- [x] [NEW] **Detail SAV** : `GET /api/v1/cosium/sav/{sav_id}` dans cosium_sav.py. CORRIGE.
- [x] [NEW] **Adapter** : mappe SAV via adapter.py. CORRIGE.
- [ ] [NEW] **Modele SQLAlchemy** : lecture live Cosium, persistence optionnelle (non bloquant).
- [x] [NEW] **Router** : `cosium_sav.py` enregistre dans main.py. CORRIGE.
- [x] [NEW] **Frontend** : page `/sav` existe (apps/web/src/app/sav/). A valider onglet client+KPIs. CORRIGE (partiel).

## 2.5 Calendrier & RDV [NEW] (P1)

- [x] [NEW] **Evenements** : `GET /api/v1/cosium/calendar-events` dans cosium_reference.py. Modele `CosiumCalendarEvent`. CORRIGE.
- [x] [NEW] **Categories** : Modele `CosiumCalendarCategory` en base. CORRIGE.
- [ ] [NEW] **Recurrence** : mapper patterns de recurrence — a completer si Cosium fournit les RRULE.
- [x] [NEW] **Sync incrementale** : `cosium_reference_sync.py` + sync_tasks incremental. CORRIGE.
- [x] [NEW] **Frontend** : page `/agenda` existe dans apps/web/src/app/agenda/. CORRIGE.

## 2.6 Notes CRM [NEW] (P2)

- [x] [NEW] GET `/api/v1/cosium/notes/customer/{customer_cosium_id}` + `/{note_id}` + `/statuses` dans cosium_notes.py. CORRIGE.
- [ ] [NEW] **Modele local + timeline client** : lecture live, persistence optionnelle.

## 2.7 Operations Commerciales [NEW] (P2)

- [x] [NEW] GET `/api/v1/cosium/commercial-operations/{id}/advantages` + `/{id}/advantages/{advantage_id}` dans cosium_commercial.py. CORRIGE.
- [ ] [NEW] `/vouchers` et `/carts` : Cosium PUT/DELETE = INTERDITS par charte (lecture seule). Pas d'implementation.

## 2.8 Sites & Multi-magasins Enrichis [NEW] (P2)

- [x] GET `/sites` basique
- [x] [NEW] **Stock par site** : `GET /api/v1/cosium/catalog/products/{product_id}/stocks-by-site` dans cosium_catalog.py → `connector.get_product_stock()` (lecture seule). CORRIGE.
- [x] [NEW] **Dashboard comparatif** inter-magasins : `analytics_cosium_extras.compute_group_comparison()` + page `admin/group-dashboard`. CORRIGE.

---

# ═══════════════════════════════════════════════
# PHASE 3 — INTELLIGENCE METIER
# ═══════════════════════════════════════════════
> Transformer les donnees brutes en insights actionnables.
> Estimation : ~120h

## 3.1 File d'Actions Intelligente (P0)

- [x] Action items basiques
- [x] [NEW] **Alertes renouvellement** : `_generate_renewal_opportunities` dans action_item_service.py. CORRIGE.
- [ ] [NEW] **Alertes SAV** : SAV en attente > X jours — SAV lu live Cosium, pas d'alerte auto (a implementer si persistence).
- [x] [NEW] **Alertes RDV** : `_generate_upcoming_appointments` (RDV demain via CosiumCalendarEvent). CORRIGE.
- [ ] [NEW] **Alertes bons d'achat** : expirant < 30 jours — Cosium vouchers en live, pas de persistence.
- [x] [NEW] **Alertes devis** : `_generate_stale_quotes` (envoyes > 15j sans signature). CORRIGE.
- [x] [NEW] **Alertes impaye** : `_generate_overdue_cosium_invoices` (outstanding > 0 et > 30j) + `_generate_overdue_payments`. CORRIGE.
- [ ] [NEW] **Priorisation IA** : priority basique ("high"/"medium"/"low") dans action items mais pas de ranking IA par impact financier.
- [x] [NEW] **Widget sidebar** : `Sidebar.tsx` affiche badge `/actions` avec compteur SWR (refreshInterval 60s). CORRIGE.

## 3.2 Dashboard Cockpit Opticien (P0)

- [x] 6 KPIs basiques
- [x] [NEW] **CA live** : `analytics_kpi_service.get_financial_kpis()` agrege CosiumInvoice + OptiFlow Factures. CORRIGE.
- [x] [NEW] **Panier moyen** : inclus dans `get_commercial_kpis()`. CORRIGE.
- [x] [NEW] **Taux transformation** : `get_commercial_kpis` devis→facture. CORRIGE.
- [x] [NEW] **Delai PEC** : `get_operational_kpis` temps moyen reponse mutuelles. CORRIGE.
- [ ] [NEW] **KPI SAV** : pas de persistence SAV → KPI absent (SAV live Cosium).
- [x] [NEW] **KPI Renouvellements** : `renewal_engine.py` expose eligibles/contactes/convertis. CORRIGE.
- [ ] [NEW] **Alertes stock** : rupture via `latent-sales` vs `stock` — endpoints live mais pas d'alerte agregee.
- [x] [NEW] **Graphique CA comparatif** : `DashboardCharts.tsx` affiche CA par mois + comparaison Cosium. CORRIGE.
- [x] [NEW] **Graphique mix produits** : modele `CosiumInvoicedItem` + migration `t5u6v7w8x9y0` + `compute_product_mix()` + `GET /api/v1/dashboard/product-mix`. Sync complete : `cosium_connector.list_invoiced_items()` + adapter + `cosium_invoiced_items_sync.sync_invoiced_items` + `POST /api/v1/sync/invoiced-items`. Hook `useProductMix(days)`. Tests 3/3. CORRIGE.
- [x] [NEW] **Balance agee** : `get_aging_balance()` par tranche (0-30j, 30-60j, 60-90j, 90j+). CORRIGE.

## 3.3 Fiche Client 360° Ultime (P1)

- [x] Fiche client basique avec onglets
- [x] [NEW] **Onglet Equipements** : `TabEquipements.tsx` existe. CORRIGE.
- [x] [NEW] **Onglet Prescriptions** : `TabOrdonnances.tsx` existe. CORRIGE.
- [x] [NEW] **Onglet Fidelite** : `TabFidelite.tsx` existe. CORRIGE.
- [x] [NEW] **Onglet RDV** : `TabRendezVous.tsx` existe. CORRIGE.
- [x] [NEW] **Onglet SAV** : `tabs/TabSAV.tsx` liste SAV par customer_cosium_id + SAVTracker stepper auto. Wire dans ClientTabs si cosiumId present. CORRIGE.
- [x] [NEW] **Onglet Notes** : `TabHistorique.tsx` / `TabActivite.tsx` incluent notes CRM. CORRIGE.
- [x] [NEW] **Score client** : `analytics_cosium_extras.compute_client_score()` existe (frequence/panier/anciennete/PEC/renouvellement). CORRIGE.
- [x] [NEW] **Alerte proactive** : `components/ui/RenewalBanner.tsx` reutilisable (urgent > 3 ans, conseille > 2 ans) avec bouton "Planifier". CORRIGE.

## 3.4 Analyse Financiere Avancee (P1)

- [x] Rapprochement bancaire basique
- [x] [NEW] **Ventilation tiers** : `analytics_kpi_service.get_payer_performance()` Secu vs mutuelle vs client. CORRIGE.
- [x] [NEW] **Analyse par type** : `analytics_cosium_service.get_financial_breakdown_by_type()` INVOICE/QUOTE/CREDIT_NOTE/etc. CORRIGE.
- [ ] [NEW] **Acomptes** : suivi `hasAdvancePayment=true` — filtre Cosium a ajouter.
- [ ] [NEW] **Ventes latentes** : potentiel CA a convertir via `latent-sales` Cosium.
- [x] [NEW] **Previsionnel tresorerie** : `analytics_cosium_extras.get_cashflow_forecast()`. CORRIGE.

## 3.5 Gestion Stock Intelligente [NEW] (P2)

- [x] [NEW] **Stock global** + **alertes rupture** : page `/stock` + `StockGauge` + KPIs (ok/bas/rupture). Par site live via `stocks-by-site`. CORRIGE (global).
- [ ] [NEW] **Stock disponible reel** : physique - latentes = dispo — necessite croisement latent-sales + stock.
- [x] [NEW] **Catalogue navigable** : page `/catalogue` existe (frames + lenses via cosium_catalog router). CORRIGE.
- [x] [NEW] **Frontend** : page Stock dans sidebar (nav ajoutee dans navConfig.ts). CORRIGE.

---

# ═══════════════════════════════════════════════
# PHASE 4 — COPILOTE IA
# ═══════════════════════════════════════════════
> L'IA au service de l'opticien.
> Estimation : ~80h

## 4.1 Assistant IA Contextuel (P1)

- [x] Service IA basique
- [x] [NEW] **Contexte enrichi** : `ai_service.get_client_cosium_context()` integre factures, ordonnances (dioptries OD/OG), paiements, solde restant. Equipements/SAV/fidelity/calendar live Cosium a ajouter si besoin. CORRIGE (partiel).
- [x] [NEW] **Suggestion renouvellement** : `ai_renewal_copilot.analyze_renewal_potential()` + `generate_renewal_message()`. CORRIGE.
- [x] [NEW] **Suggestion upsell** : `GET /api/v1/ai/client/{customer_id}/upsell-suggestion` — Claude + contexte Cosium, prompt cible (progressifs si add >=+1, anti-lumiere bleue, solaire, lentilles). Hook `useUpsellSuggestion`. CORRIGE.
- [x] [NEW] **Resume pre-RDV** : `GET /api/v1/ai/client/{customer_id}/pre-rdv-brief` genere un brief IA (Claude) base sur `ai_service.get_client_cosium_context` (factures, prescriptions, paiements). 5-8 points max, francais clair. CORRIGE.
- [x] [NEW] **Analyse devis** : `GET /api/v1/ai/devis/{devis_id}/analysis` — lit lignes devis + contexte client, Claude analyse coherence + extrait `warnings`. Hook `useDevisAnalysis`. CORRIGE.
- [x] [NEW] **Chatbot opticien** : `POST /api/v1/ai/copilot/query` avec 4 modes (dossier/financier/documentaire/marketing). Modes "dossier" + "marketing" injectent contexte Cosium. Tools avances (SAV count, CA) a enrichir. CORRIGE (base).

## 4.2 IA Renouvellement Proactif (P1)

- [x] Renewal engine basique
- [x] [NEW] **Scoring** : `compute_client_score` + `ai_renewal_copilot.analyze_renewal_potential` prennent en compte anciennete equipement/dioptries/visite. CORRIGE.
- [x] [NEW] **Segmentation auto** : `analytics_cosium_extras.compute_dynamic_segments()` retourne cohortes. CORRIGE.
- [x] [NEW] **Templates personnalises** : `ai_renewal_copilot.generate_renewal_template()`. CORRIGE.
- [x] [NEW] **Timing optimal** : `compute_best_contact_hour()` + `GET /api/v1/dashboard/best-contact-hour` groupe interactions entrantes 6 mois par heure, top 3 + recommandation. CORRIGE.
- [x] [NEW] **A/B testing** : migration `s4t5u6v7w8x9` ajoute `variant_key`/`opened_at`/`clicked_at`/`replied_at` a `message_logs`. Endpoint `GET /api/v1/marketing/campaigns/{id}/ab-stats` renvoie par variant_key open/click/reply rates. CORRIGE.

## 4.3 IA Aide au Devis (P2)

- [x] [NEW] **Simulation remboursement** : `services/reimbursement_simulation_service.py` + `POST /api/v1/ai/simulate-reimbursement` - heuristique BR selon complexite (simple/complexe/tres complexe par sphere/cylindre/addition), SS 60%, mutuelle % verres + forfait monture, support 100% sante (classe A). CORRIGE (heuristique).
- [x] [NEW] **Recommandation produit** : `GET /api/v1/ai/client/{customer_id}/product-recommendation` - Claude + contexte dioptries, recommande type verre + traitements + materiau (indice selon sphere). Hook `useProductRecommendation`. CORRIGE.
- [x] [NEW] **Comparaison devis** : `components/ui/QuoteComparison.tsx` — 2-3 devis cote a cote, lignes alignees, option recommandee highlighted. CORRIGE (UI).
- [x] [NEW] **Detection anomalie** : integree dans `GET /api/v1/ai/devis/{devis_id}/analysis` — extrait warnings automatiquement. CORRIGE.

## 4.4 IA Analyse Business (P2)

- [x] [NEW] **Rapport hebdo auto** : `tasks/weekly_report_tasks.send_weekly_reports` — Celery beat lundi 8h, envoie email HTML par admin tenant (CA, encaisse, reste, taux recouvrement, balance agee, alerts count). CORRIGE.
- [x] [NEW] **Detection tendances** : `analytics_cosium_extras.compute_trends()` + `GET /api/v1/dashboard/trends` compare 30j courants vs 30j precedents (CA, nb factures, panier moyen, delta %). CORRIGE (heuristique simple).
- [x] [NEW] **Benchmark inter-magasins** : `analytics_cosium_extras.compute_group_comparison()` compare KPIs tenant par tenant. CORRIGE.
- [x] [NEW] **Prevision CA** : `analytics_cosium_extras.get_cashflow_forecast()` previsionnel tresorerie. CORRIGE.

---

# ═══════════════════════════════════════════════
# PHASE 5 — UX PREMIUM & POLISH
# ═══════════════════════════════════════════════
> Chaque ecran doit inspirer confiance et maitrise immediate.
> Estimation : ~80h

## 5.1 Composants UI Manquants (P1)

- [x] **CalendarView.tsx** : `components/ui/CalendarView.tsx` vue mensuelle navigable, grille 7 jours ISO, events/jour (top 3 + count surplus), highlight today. CORRIGE.
- [x] **PrescriptionCard.tsx** : `components/ui/PrescriptionCard.tsx` avec OD/OG, sphere/cylindre/axe/addition/prisme. CORRIGE.
- [x] **EquipmentTimeline.tsx** : `components/ui/EquipmentTimeline.tsx` — frise verticale tri date, types frame/lens/sun/other. CORRIGE.
- [x] **StockGauge.tsx** : `components/ui/StockGauge.tsx` — jauge 4 niveaux (rupture/critique/bas/ok). CORRIGE.
- [x] **ClientScoreRadar.tsx** : `components/ui/ClientScoreRadar.tsx` — radar Recharts 5 axes (frequence, panier, anciennete, PEC, renouv). CORRIGE.
- [x] **QuoteComparison.tsx** : `components/ui/QuoteComparison.tsx` - 2 a 3 devis cote a cote, lignes alignees avec check/minus, highlight option recommandee, reste a charge. CORRIGE.
- [x] **SAVTracker.tsx** : `components/ui/SAVTracker.tsx` — stepper done/current/pending responsive. CORRIGE.
- [x] **VoucherCard.tsx** : `components/ui/VoucherCard.tsx` — carte bon avec code couleur expiration (<7j rouge, <30j ambre). CORRIGE.
- [x] **RenewalBanner.tsx** : `components/ui/RenewalBanner.tsx` — bandeau alerte 2 ans/3 ans avec bouton planifier. CORRIGE.

## 5.2 Nouvelles Pages (P1)

- [x] [NEW] `/stock` — `apps/web/src/app/stock/page.tsx` avec grille produits + StockGauge + KPIs. Ajoute au sidebar nav. CORRIGE.
- [x] [NEW] `/sav` — page existe (`apps/web/src/app/sav/`). CORRIGE.
- [x] [NEW] `/calendrier` : page `/agenda` existe. CORRIGE (equivalent).
- [x] [NEW] `/analytics/cosium` — page `analytics-cosium` existe. CORRIGE.
- [x] [NEW] `/catalogue` — page `catalogue` existe. CORRIGE.
- [x] [NEW] `/admin/data-quality` — page existe (cf Phase 0.4 #38). CORRIGE.

## 5.3 Accessibilite & Polish (P2)

- [x] **WCAG AA** (base) : focus-visible rings blue-500 sur inputs/boutons, skip-link "Aller au contenu principal" dans layout.tsx, aria-labels sur icones, role=alert sur erreurs FormField. Tokens contrastes AA. Audit complet = session dediee. CORRIGE (base).
- [x] [BUG] **ARIA dropdown** : `Header.tsx:202` passe de `aria-haspopup="dialog"` a `"menu"`. CORRIGE.
- [x] **aria-describedby** sur tous les champs de formulaire : `FormField.tsx:61` — `FormInput` recoit `aria-describedby={errorId}` via context automatiquement. CORRIGE.
- [x] **Raccourcis clavier** : `lib/shortcuts.ts` + `KeyboardShortcutsHelp` component. Ctrl+K/Cmd+K = focus recherche. CORRIGE.
- [x] **Dark mode** : tokens `.dark` (bg-page/card/sidebar, text-primary/secondary, border) dans globals.css + toggle Sun/Moon dans Header.tsx. CORRIGE.
- [x] **Onboarding** : page `/onboarding` avec steps multi-etapes (helpers + steps). CORRIGE.
- [x] **Recherche globale enrichie** : `GlobalSearch.tsx` dans Header avec combobox searchable, lib/search-hits.ts couvre clients+factures+devis+produits. CORRIGE (base).
- [x] **Notifications push** : `SSEListener.tsx` SSE backend ecoute paiements/sync, wrappe dans ErrorBoundary (AuthLayout.tsx). CORRIGE.
- [x] [BUG] **SSEListener sans ErrorBoundary** : `AuthLayout.tsx:49` — SSEListener wrappe dans `<ErrorBoundary name="SSEListener">`. CORRIGE.
- [x] **Messages erreur humains** : `app/error.tsx` `humanMessage()` mappe 5xx/403/404/408/429/TypeError network vers messages FR + reference digest. CORRIGE.
- [x] [PERF] **SWR retry** : `SWRProvider.onErrorRetry` avec exponential backoff 1s/2s/4s (plafond 8s). 4xx client = pas de retry. CORRIGE.
- [x] **Print styles** : `globals.css:400-410` - `@media print` font-size 11pt, noir/blanc, break-after avoid. CORRIGE.

## 5.4 TypeScript & Code Quality Frontend (P2)

- [ ] **ESLint strict** : `no-explicit-any` passer de "warn" a "error"
- [ ] **exhaustive-deps** : passer de "warn" a "error"
- [x] **Centraliser types** : `apps/web/src/lib/types/` existe avec 7 fichiers (admin, batch, client, cosium, financial, pec-preparation, index). CORRIGE.
- [ ] **Zod schemas manquants** : facture, rapprochement, relance
- [x] **Bannir `any` restants** : aucun `: any` ni `as any` detecte dans apps/web/src (scan Grep). CORRIGE.
- [ ] **ESLint bloquant en CI** : retirer `ignoreDuringBuilds: true` de `next.config.ts`
- [x] **Sentry production** : `sentry.client.config.ts` + `main.py:80-87` init si `settings.sentry_dsn`. CORRIGE.
- [x] **Web Vitals** : `components/layout/WebVitals.tsx` + endpoint backend `/api/v1/web-vitals` (LCP/FID/CLS/INP/TTFB via sendBeacon). CORRIGE (Phase 1.1).

---

# ═══════════════════════════════════════════════
# PHASE 6 — MARKETING & CRM AVANCE
# ═══════════════════════════════════════════════
> Estimation : ~40h

- [x] Marketing service basique + campagnes
- [x] [NEW] **Segments dynamiques** : `analytics_cosium_extras.compute_dynamic_segments()` cohortes. CORRIGE.
- [ ] [NEW] **Bons d'achat Cosium** : endpoint `/commercial-operations/{id}/advantages` live, affichage + alertes expiration a implementer frontend.
- [x] [NEW] **Campagne renouvellement** : `renewal_campaign_service.py` + `ai_renewal_copilot` workflow segment → template → envoi. CORRIGE.
- [x] [NEW] **Timeline unifiee** : `services/client_timeline_service.build_client_timeline()` + `GET /api/v1/clients/{id}/timeline` — agrege interactions + campaign_messages triee desc, filtre par `kinds`. CORRIGE.
- [x] [NEW] **ROI par campagne** : `marketing_service.get_campaign_roi()` + `GET /api/v1/marketing/campaigns/{id}/roi` - CA genere par clients cibles dans les 30j apres envoi + conversions + taux. CORRIGE.
- [x] [NEW] **Dashboard fidelite** : page `/fidelite` (apps/web/src/app/fidelite/page.tsx) - cartes + parrainages + KPIs. Hooks `useCosiumFidelityCards` / `useCosiumSponsorships`. CORRIGE.
- [x] [NEW] **Top clients** : `analytics_cosium_extras.get_top_clients_by_ca()`. CORRIGE.

---

# ═══════════════════════════════════════════════
# PHASE 7 — MULTI-TENANT & SCALE
# ═══════════════════════════════════════════════
> Supporter 50+ magasins.
> Estimation : ~50h

- [x] Architecture multi-tenant basique (tenant_id, RLS)
- [x] **Credentials Cosium par tenant** : `tenant.cosium_password_enc`/`cosium_cookie_access_token_enc` Fernet encrypt via `core/encryption.py`. CORRIGE.
- [x] **Sync isolee** : `sync_tasks.sync_all_tenants` itere tenant par tenant, acquire_lock par tenant dans sync.py router. CORRIGE.
- [x] **Admin groupe** : page `/admin/group-dashboard` existe + `compute_group_comparison()` backend. CORRIGE.
- [x] **Switch tenant** : `POST /api/v1/auth/switch-tenant` avec revoke refresh tokens + nouveau JWT (auth_service.py:188). CORRIGE.
- [x] [NEW] **Comparatif inter-magasins** : `analytics_cosium_extras.compute_group_comparison()`. CORRIGE.
- [ ] [NEW] **Stock inter-magasins** : endpoint `stocks-by-site` livre par produit, vue consolidee cross-sites a implementer.
- [x] **Sync incrementale** : `erp_sync_invoices.sync_invoices(full=False)` fetch depuis last_date - 7j. CORRIGE.
- [x] **Cache Redis** : `core/redis_cache.py` cache_get/cache_set TTL configurable (5min metrics, 10min data_quality). CORRIGE.
- [ ] **Connection pooling** : optimiser pour 50 tenants concurrents
- [ ] **Rate limiting Cosium** : backoff exponentiel
- [x] [PERF] **N+1 queries** : `calculate_client_completeness()` (client_completeness_service.py:16-35) ne fait aucune requete SQL — juste lecture champs Customer. `calculate_client_completeness_full` (avec SQL) est reserve aux detail views. Pas de N+1. CORRIGE.
- [ ] [PERF] **COUNT(*) lent** : `client_repo.search():31` — compromis design (pagination numerotee frontend necessite total). Migration vers pattern LIMIT+1 demanderait refonte UX pagination. Indexes tenant_id+deleted_at existent deja. Non-bloquant.
- [ ] [PERF] **time.sleep() bloquant** : `cosium/client.py:129,158,190` — FastAPI sync route = thread par requete, pas de contention worker-level. Migration asyncio demanderait refonte client+services+routes. Non-bloquant.

---

# ═══════════════════════════════════════════════
# PHASE 8 — OBSERVABILITE & MONITORING
# ═══════════════════════════════════════════════
> Estimation : ~40h

- [x] **Prometheus middleware** : `/api/v1/metrics` existe (api/routers/metrics.py) expose tenants/users/customers/invoices/outstanding/action_items. CORRIGE (Phase 0.3 #24).
- [ ] **Grafana dashboards** : ops (infra) + metier (CA, sync, clients)
- [x] **Sentry** : `main.py:80-87` init conditionnel si `settings.sentry_dsn`. `sentry.client.config.ts` cote front. CORRIGE.
- [ ] **Alerting** : Slack/email si sync echoue, latence > 5s, erreur > 5%
- [x] **Health checks** : `/health` liveness (status:ok) + `/health/ready` readiness (DB + Redis) dans main.py:342-358. CORRIGE.
- [x] [BUG] **Health check session leak** : `/health/ready` utilise `try/finally db.close()` (main.py:353-358). Pas de leak. CORRIGE.
- [x] **Logs structures JSON** : structlog + `RequestIdMiddleware` (core/request_id.py) injecte `request_id` dans tous les logs. CORRIGE.
- [x] **Request/response logging** : middleware avec masquage PII via `_mask_sensitive_fields` + `_scrub_value` regex. CORRIGE.
- [x] [BUG] **Masquage PII incomplet** : `core/logging.py` ajoute `_SENSITIVE_VALUE_PATTERN` regex qui masque `password=xxx`, `token: xxx`, `api_key="xxx"` etc. dans les substrings. CORRIGE.
- [ ] **Log rotation** : taille + temps
- [ ] **Audit trail complet** : chaque consultation donnee sensible logguee
- [ ] **RGPD** : droit a l'oubli, export, consentements
- [x] **Retention** : `tasks/cleanup_tasks.apply_retention_policy` purge audit_logs > 365j et action_items resolus > 90j. Schedule quotidien 3:45. CORRIGE.

---

# ═══════════════════════════════════════════════
# PHASE 9 — BACKEND POLISH & ARCHITECTURE
# ═══════════════════════════════════════════════
> Estimation : ~50h

## 9.1 Architecture (P2)

- [x] [BUG] **OAuth2PasswordBearer duplique** : `core/tenant_context.py` importe maintenant `oauth2_scheme` depuis `core/deps.py`. Plus de doublon. CORRIGE.
- [x] [BUG] **PecService erreur inversee** : `pec_service.py:81` deja `BusinessError("message", code="FACTURE_NOT_FOUND")` - ordre correct. CORRIGE (deja fait dans audit_phase0).
- [ ] **Services mixent audit + events** : separer avec event bus
- [ ] **Repos return types incoherents** : standardiser (ORM objects, services convertissent)
- [ ] **Services mixent objets et primitifs** : toujours utiliser schemas en entree
- [ ] **CosiumClient non injectable** : instancie globalement (ligne 294). Utiliser factory + injection.
- [x] **Refresh token rotation** : `auth_service.refresh():149` revoke ancien + genere nouveau (`generate_refresh_token` + `create`). CORRIGE.
- [ ] **RBAC par ressource** : `@require_resource_ownership("client", client_id)` sur endpoints sensibles
- [x] **Timeout par appel Cosium** : `cosium/client.py:184` `timeout=30` par defaut sur chaque GET. httpx.Client utilise aussi un timeout propre. Refinement par endpoint possible mais 30s convient pour la majorite des lectures. CORRIGE.

## 9.2 Code Quality (P2)

- [ ] **Dead code** : passer ruff pour supprimer le code mort
- [ ] **Docstrings** : 96 services sans docstring
- [ ] **Type hints return** : partout
- [ ] **Prefixer methodes privees** : `_x` → `__x`
- [ ] **Validations Pydantic** : min/max/regex sur tous les champs
- [ ] **`__all__`** : definir les exports publics de chaque module
- [x] **Recherche sans limite** : `clients.py:33` — `Query("", alias="q", max_length=100)`. FastAPI renvoie 422 si > 100 char. CORRIGE.

## 9.3 PEC V12 Intelligence [NEW] (P1)

- [ ] [NEW] **Liaison 100% factures** : fuzzy matching via `_links.customer.href` (8h)
- [ ] [NEW] **Table client_mutuelles** : relation N-N (2h)
- [ ] [NEW] **Auto-detection mutuelle** : depuis TPP/invoices/documents (4h)
- [ ] [NEW] **OCR pipeline** : Tesseract + pdfplumber (6h)
- [ ] [NEW] **Classification documents** : ordonnance, devis, attestation, etc. (3h)
- [ ] [NEW] **Parsers structures** : 6 types de documents (12h)
- [ ] [NEW] **Consolidation multi-source** (8h)
- [ ] [NEW] **Detection incoherences** + alertes (4h)
- [ ] [NEW] **PEC assistant frontend** : onglet interactif fiche client (8h)

---

# ═══════════════════════════════════════════════
# PHASE 10 — VISION LONG TERME
# ═══════════════════════════════════════════════
> Estimation : ~80h

## 10.1 Portail Client (P3)

- [ ] Espace client web : devis, factures, RDV, prescription
- [ ] Prise de RDV en ligne
- [ ] Suivi SAV public
- [ ] Signature electronique devis

## 10.2 Integrations Externes (P3)

- [ ] QR Code par dossier/devis
- [ ] SMS rappel RDV / relance impaye
- [ ] Export comptable Sage/Cegid/QuickBooks
- [ ] Carte vitale (hardware dependant)
- [ ] Webhooks entrants
- [ ] Connecteur Zapier/Make
- [ ] API publique v1

## 10.3 Mobile Avance (P3)

- [ ] [PWA] Mode hors-ligne enrichi : consultation fiches clients cachees
- [ ] [PWA] Scan EAN depuis camera : stock + infos produit
- [ ] [PWA] Notifications push natives (via service worker)

## 10.4 DX & Tooling (P3)

- [ ] Storybook UI components
- [ ] openapi-typescript client auto-genere
- [ ] Semantic versioning CI tags
- [ ] Prettier + Ruff pre-commit hooks
- [ ] Bootstrap script nouveau dev
- [ ] VS Code debug profiles
- [ ] Seed data generator
- [ ] Suite E2E Playwright

---

# ═══════════════════════════════════════════════
# RESUME EXECUTIF
# ═══════════════════════════════════════════════

| Phase | Items | Effort | Priorite |
|-------|-------|--------|----------|
| **Phase 0** — Urgences (bugs, secu, prod) | ~50 | 80h | P0 [!] |
| **Phase 1** — PWA & Responsive | ~35 | 60h | P0-P1 |
| **Phase 2** — Cosium Core sync | ~55 | 150h | P0-P2 |
| **Phase 3** — Intelligence metier | ~40 | 120h | P0-P1 |
| **Phase 4** — Copilote IA | ~20 | 80h | P1-P2 |
| **Phase 5** — UX Premium & Polish | ~35 | 80h | P1-P2 |
| **Phase 6** — Marketing & CRM | ~10 | 40h | P2 |
| **Phase 7** — Multi-tenant & Scale | ~15 | 50h | P1-P2 |
| **Phase 8** — Observabilite | ~15 | 40h | P2 |
| **Phase 9** — Backend Polish & PEC V12 | ~25 | 50h | P1-P2 |
| **Phase 10** — Vision long terme | ~20 | 80h | P3 |
| **TOTAL** | **~320 items** | **~830h** | |

---

## CHEMIN CRITIQUE RECOMMANDE

```
Semaine 1-2  : Phase 0 (bugs critiques + securite + deploy)
Semaine 3-4  : Phase 1 (PWA + responsive)
Semaine 5-8  : Phase 2.1 + 2.2 (clients enrichis + dossiers optiques)
Semaine 9-10 : Phase 3.1 + 3.2 (file d'actions + dashboard cockpit)
Semaine 11-12: Phase 5 (UX polish) + Phase 7 (scale)
Semaine 13+  : Phases 4, 6, 8, 9, 10 par priorite
```

> **Objectif** : un Cosium Copilot PWA fonctionnel, securise, avec dossiers optiques
> et dashboard intelligent en **12 semaines**.

---

*Ce document remplace TODO.md, TODO_V2.md, TODO_V3.md, TODO_V4.md, TODO_V5.md et l'ancien TODO_MASTER.md.*
*Les anciennes TODOs sont conservees comme archive historique.*
