# TODO — OptiFlow AI (audit complet 2026-04-13)

> Consolidation des audits Backend + Frontend + Infra/CI/CD.
> **Total : ~230 items, ~280h** — du P1 critique au polish nice-to-have.
> Plan V12 PEC Intelligence : **largement implémenté** (reste batch, auto-relance, tracking mutuelle).

---

## 📊 Synthèse par priorité

| Priorité | Items | Effort | Description |
|----------|-------|--------|-------------|
| **P1 Critique** | 18 | ~35h | Sécurité, prod blockers, data integrity |
| **P2 Important** | 72 | ~95h | Architecture, fiabilité, features métier |
| **P3 Modéré** | 58 | ~70h | Qualité code, refacto, UX |
| **P4 Monitoring** | 28 | ~30h | Observabilité, perf, alerting |
| **P5 Nice-to-have** | 54 | ~50h | Polish, docs, tests avancés |

---

## 🔴 P1 — CRITIQUE (prod blockers, ~35h)

### Sécurité & isolation
- [x] Tests isolation multi-tenant : user tenant A ne peut PAS accéder tenant B — `tests/test_tenant_isolation.py` (3 tests ✓) — ~4h
- [x] Test auth E2E complet : login → access → refresh → switch tenant → logout → blacklist — `tests/test_auth_e2e.py` (5 tests ✓) — ~3h
- [x] Test endpoints admin : 403 si non-admin sur `/admin/*` — `tests/test_admin_auth.py` (6 tests ✓) — ~2h
- [x] Remplacer `db.commit()` par `db.flush()` dans `refresh_token_repo.py` (2 occurrences) — ~30min
- [x] CSP policy : retirer `unsafe-eval` (nonces CSP reporté) — `nginx/nginx.conf` — ~1h
- [x] Activer HSTS en prod (décommenter `Strict-Transport-Security`) — `nginx/nginx.conf` — ~20min
- [x] MinIO/Mailhog : binder sur `127.0.0.1` au lieu de `0.0.0.0` — `docker-compose.yml` — ~20min
- [x] Enforcer changement `minioadmin:minioadmin` en non-dev — check startup — ~30min

### Déploiement & infra
- [ ] Déploiement E2E `docker-compose.prod.yml` testé de bout en bout — ~4h
- [ ] TLS bout en bout avec vrai cert (mkcert local ou Let's Encrypt) — ~2h
- [x] Créer `docker-compose.prod.yml` avec limites ressources (CPU, mémoire) — ~1h
- [x] `deploy.sh` idempotent : `git fetch && reset --hard` au lieu de `git pull` — ~1h
- [x] Healthchecks Celery worker + beat (pas juste Redis PING) — `docker-compose.yml` — ~30min
- [x] Séparer timeout DB API (30s) vs Celery (120s au lieu de 300s) — `db/session.py` — ~1h

### Frontend blockers UX
- [x] Ajouter LoadingState/ErrorState/EmptyState aux pages qui n'en ont pas — audit : DataTable encapsule les 3 états, couverture OK — ~2h
- [ ] Pagination serveur sur listes : cases, devis, factures, paiements — API accepte déjà `page/page_size` mais retourne `list[T]` ; besoin migrer vers `PaginatedResponse[T]` + total — ~3h (rescope)
- [x] ConfirmDialog avant TOUTE suppression (audit complet) — ~1h
- [x] Frontend lint manquant en CI : ajouter `npm run lint` — `.github/workflows/ci.yml` — ~30min

---

## 🟠 P2 — IMPORTANT (~95h)

### Architecture backend
- [ ] Refacto 19 repos : retirer `db.commit()` → services gèrent commit, repos `db.flush()` — ~8h
- [ ] Dict → Pydantic dans `pec_preparation.py:37,206,289` — ~1h
- [ ] Dict → Pydantic dans `cosium_documents.py:80` (créer `BulkSyncResponse`) — ~1h
- [ ] Audit systématique : tous endpoints API avec `response_model` Pydantic (40 routers) — ~3h
- [x] Créer `PaginatedResponse[T]` + `MessageResponse` génériques — `schemas/common.py` — ~1h30
- [ ] Splitter `reconciliation_service.py` (517 lignes, fonction 217l) — ~2h
- [ ] Splitter `export_service.py` (480 lignes) en pdf/xlsx — ~2h
- [ ] Splitter `erp_sync_extras.py` (455 lignes) — ~2h
- [ ] Splitter `client_mutuelle_service.py` (353 lignes) — ~1h
- [ ] Refacto `consolidation_*.py` (5 fichiers) : créer `BaseConsolidator` — ~2h
- [ ] Splitter `search_service.global_search()` (216 lignes) par entity type — ~2h

### Celery & async
- [ ] Audit idempotence Celery : toutes tâches `EXISTS` avant INSERT (reminder, extraction, sync) — ~3h
- [ ] Déléguer envoi email sync dans `reminder_tasks.py` vers `email_tasks.py` — ~2h
- [ ] Dead-letter queue pour tâches échouées (Celery error handlers) — ~1h
- [ ] Retry policy documentée : `docs/CELERY.md` — ~30min
- [ ] Test : tâche qui échoue → retry → réussit — ~1h

### PEC (Plan V12 finalisation)
- [ ] Batch PEC submission : `POST /pec/batch` avec liste prep IDs — `services/pec_service.py`, schemas, routers — ~6h
- [ ] Auto-relance PEC > 30j sans réponse : Celery task daily + notifs — `tasks/pec_tasks.py` — ~3h
- [ ] Tracking réponse mutuelle : status `soumise → acceptée_partiellement → acceptée` — ~2h
- [ ] PDF PEC : inclure corrections utilisateur dans export — ~1h
- [ ] Fermer officiellement les `[ ]` du `PLAN_V12_PEC_INTELLIGENCE.md` (items déjà implémentés) — ~30min

### Tests backend par domaine
- [ ] Test facturation + paiements sync Cosium — ~1h
- [ ] Test reconciliation paiement-facture (lettrage multi-partiel) — ~1h
- [ ] Test export FEC format légal français (numérotation, GL codes) — ~1h
- [ ] Test GDPR right-to-be-forgotten (anonymisation + soft-delete) — ~1h
- [ ] Test devis import CSV/Excel → extraction champs — ~1h
- [ ] Test OCR parsers avec vrais PDFs (fixtures ordonnance, devis, attestation) — ~1h
- [ ] Test Claude API error handling (token limit, timeout, unavailable) — ~1h
- [ ] Test marketing campaign complet (créer → segmenter → envoyer) — ~1h
- [ ] Test consent RGPD (opt-in/opt-out, droit à l'oubli) — ~1h
- [ ] Test reminder plan exécution (daily task crée reminders) — ~1h
- [ ] Test Stripe webhook (payment received → update subscription) — ~1h
- [ ] Test banking import CSV → Payment → match invoices — ~1h
- [ ] Test health endpoint (status Cosium, DB, Redis) — ~1h
- [ ] Test cycle cookie httpOnly (déconnexion, expiration, accès non-autorisé) — ~2h

### Index & migrations
- [ ] Vérifier index sur Marketing, Interaction, Notification (colonnes filtrées) — ~30min
- [ ] Index sur Cosium* (CosiumInvoice, CosiumDocument) : (tenant_id, status, created_at) — ~1h
- [ ] Test rollback migration Alembic (`alembic downgrade -1 && upgrade +1` en CI) — ~1h
- [ ] Documenter stratégie d'index : `docs/DATABASE_INDEXES.md` — ~30min

### Frontend — pages métier CRUD
- [ ] Clients/Dossiers : CRUD complet avec édition inline + archivage — ~1h
- [ ] Factures Cosium : indiquer clairement read-only + filtres + export CSV — ~45min
- [ ] Devis : création avec AsyncSelect client + confirmation soumission — ~1h
- [ ] Paiements : formulaire création + rapprochement manuel drag-drop — ~1h30
- [ ] PEC préparation : validation champs + confirmation avant soumission — ~1h
- [ ] Rapprochement bancaire : validation montants + undo + double-clic protection — ~1h30
- [ ] Relances : envoi en masse avec confirmation + retry sur erreur — ~1h
- [ ] Marketing campagnes : CRUD création + segmentation clients — ~2h
- [ ] Admin sync Cosium : bouton "Sync now" + modal progression + erreurs + rollback — ~1h
- [ ] Admin utilisateurs : édition + suppression + changement rôle + reset password — ~1h30
- [ ] Settings : validation input + confirmation save + toast succès partout — ~1h

### Composants UI manquants
- [x] Créer `Card.tsx` réutilisable (Card, CardHeader, CardFooter) — ~30min
- [x] Créer `Badge.tsx` simple (6 variants, distinct de StatusBadge) — ~30min
- [ ] Créer `Timeline.tsx` (chronologie verticale interactions) — ~1h
- [ ] Créer `AgingTable.tsx` réutilisable (balance agée avec couleurs tranches) — ~1h
- [ ] Créer `DateRangePicker.tsx` — ~1h
- [x] Créer `Breadcrumb.tsx` réutilisable (aria-current, ChevronRight) — ~30min
- [x] Créer wrappers `Input.tsx` + `Select.tsx` (leftIcon, error, focus ring) — ~30min

### CI/CD
- [x] Cache dépendances Python en CI (`setup-python` cache=pip) — ~1h
- [x] Cache dépendances npm en CI (déjà présent `cache: npm`) — ~30min
- [x] Security scanning : `bandit`, `pip-audit` — job `backend-security` ajouté. Dependabot restant — ~2h
- [ ] Test coverage rapportage avec Codecov — ~1h
- [ ] Matrice Python 3.11/3.12 + Node 18/20 en CI — ~1h
- [ ] Branch protection rules : CI doit passer avant merge — ~30min

---

## 🟡 P3 — MODÉRÉ (~70h)

### Refacto frontend gros fichiers
- [ ] `dashboard/page.tsx` 664→300l : extraire DashboardKPIs, DashboardCharts, DashboardSections — ~2h
- [ ] `rapprochement/page.tsx` 390→250l : extraire TransactionList, MatchingUI, ConfirmationPanel — ~1h30
- [ ] `notifications/page.tsx` 369l : extraire NotificationList, NotificationFilters — ~1h
- [ ] `aide/page.tsx` 338l : extraire FAQAccordion, Shortcuts, Contact — ~1h30
- [ ] `Sidebar.tsx` 433→200l : extraire SidebarGroup, SidebarItem, SidebarMobileNav — ~1h
- [ ] `pec-dashboard/page.tsx` 320l : extraire PecRequestsList, PecStats, PecActions — ~1h
- [ ] `pec-preparation/[prepId]/page.tsx` 650l : découper sections formulaire — ~2h
- [ ] `clients/page.tsx` 313l : extraire logique état dans hook — ~1h

### Code quality frontend
- [ ] Remplacer tous `window.confirm()` par ConfirmDialog — grep + fix — ~1h
- [ ] Remplacer `window.open()` par liens Next.js / handlers propres — ~1h
- [ ] Types TS stricts pour réponses admin — `lib/types/admin.ts` — ~2h
- [ ] Centraliser types inline des pages dans `lib/types/` — ~45min
- [ ] Compléter schémas Zod manquants : facture, rapprochement, relance — ~1h
- [ ] Hooks API typés génériques (réduire verbosité `useSWR<T>(...)`) — ~1h

### Code quality backend
- [ ] Supprimer dead code : fonctions inutilisées, imports orphelins (ruff) — ~1h
- [ ] Docstrings complets sur fonctions publiques (91 services) — ~2h
- [ ] Type hints : vérifier toutes les fonctions ont return type — ~1h
- [ ] Nettoyer commentaires obsolètes — ~30min
- [ ] Renommer `pec_preparation_service` → `pec_assistant_service` (plus parlant) — ~30min
- [ ] Préfixer méthodes privées `_x` → `__x` pour vraies private — ~30min
- [ ] Validations Pydantic : tous schemas ont min/max length, regex email/phone — ~30min

### Tests frontend manquants
- [ ] Tests hooks personnalisés (`useClients`, `useCase`, `useDashboard`) + fixtures SWR — ~2h
- [ ] Tests flows complets : PEC prep, rapprochement, devis création — ~3h
- [ ] Tests pages critiques avec interactions utilisateur — ~2h

### Accessibilité
- [ ] Audit `aria-label` sur toutes icônes seules (sidebar, boutons actions) — ~1h
- [ ] Audit `focus-visible` sur tous interactifs (DataTable, Inputs) — ~1h
- [ ] Vérification contraste WCAG AA (outils automatisés) — ~1h30
- [ ] Navigation clavier : Tab order logique, Escape ferme modales, tri DataTable — ~1h
- [ ] Form labels/inputs association (id + htmlFor) — ~30min
- [ ] Error messages avec `role="alert"` + ARIA live regions — ~1h
- [ ] `aria-hidden` sur icônes décoratives — ~30min

### Frontend polish
- [ ] Pagination serveur sur tous les hooks (`useCases`, `useDevisList`, etc.) — ~1h30
- [ ] Audit `React.lazy` pour pages lourdes (graphiques Recharts) — ~1h
- [ ] Migration `<img>` → `next/image` partout — ~1h
- [ ] SWR `stale-while-revalidate` cohérent sur tous hooks — ~45min
- [ ] Tooltips sur icônes sans label — ~1h
- [ ] Animations page transitions (éviter flicker loading→data) — ~1h
- [ ] Empty/error states avec illustrations légères — ~1h
- [ ] Print styles `@media print` pour rapports PDF — ~1h
- [ ] Mobile polish <1366px (sidebar, DataTable responsive) — ~2h

### Nginx & infra
- [ ] Rate limiting global API (`limit_req_zone api`) pas juste login — ~1h
- [ ] Bloquer `/redoc` en plus de `/docs` en prod — ~20min
- [ ] `X-Request-ID` logging nginx — ~30min
- [ ] Aligner `client_max_body_size` nginx ↔ `MAX_UPLOAD_SIZE_MB` FastAPI — ~20min
- [ ] Redis éviction policy : `maxmemory 512mb --maxmemory-policy allkeys-lru` — ~30min
- [ ] Celery beat monitoring heartbeat — ~1h
- [ ] Pool PostgreSQL `max_connections=150`, `idle_in_transaction_session_timeout=60000` — ~30min

### Scripts déploiement
- [ ] `restore_db.sh` : ajouter `--dry-run` + backup "pre-restore" — ~1h
- [ ] `backup_db.sh` : check espace disque avant, `BACKUP_RETENTION_DAYS` configurable — ~45min
- [ ] Créer `scripts/rollback.sh` orchestrant restore + docker restart — ~2h
- [ ] Health check API via `curl` au lieu d'exec Python — ~20min

### Batch & performance
- [ ] `batch_tasks.py` : update statut BDD tous les 100 items (progression visible) — ~1h
- [ ] Vérifier pas de N+1 dans sync Cosium (SQLAlchemy eager loading) — ~2h

---

## 🔵 P4 — MONITORING & PERF (~30h)

### Observabilité
- [ ] Endpoint `/metrics` Prometheus-compatible — `api/routers/metrics.py` — ~4h
- [ ] Middleware métriques temps de réponse (histogram par endpoint) — ~2h
- [ ] Monitoring queue Celery (Flower ou endpoint custom) — ~2h
- [ ] Alertes Sentry sur erreurs 5xx — ~1h
- [ ] Slow query logging PostgreSQL (`log_min_duration_statement=500ms`) — ~30min
- [ ] Request/response logging middleware (méthode, chemin, user, tenant, durée) — ~1h
- [ ] Circuit breaker pour Cosium API (5 erreurs → fail fast) — ~1h
- [ ] Sentry custom metrics (facturation, OCR success rate) — ~1h
- [ ] Health endpoint `/health/deep` check DB + Redis + MinIO — ~1h

### Monitoring stack (optionnel mais recommandé)
- [ ] `docker-compose.monitoring.yml` : Prometheus + Grafana — ~4h
- [ ] Dashboards Grafana (latence, erreurs, queue) — ~3h
- [ ] Logs agrégés (fluent-bit ou Datadog) — ~4h
- [ ] Alertmanager ou webhook PagerDuty — ~2h

### Performance frontend
- [ ] Bundle size audit + tree-shaking (`next/bundle-analyzer`) — ~2h
- [ ] Lighthouse score ≥90 (Performance + Accessibility) — ~4h

---

## 🟢 P5 — NICE-TO-HAVE (~50h)

### Tests avancés
- [ ] Sync Cosium avec jeu de données réaliste (nécessite accès live) — ~4h
- [ ] Switch tenant : données changent bien côté frontend — ~2h
- [ ] Tests multi-tenant parallèles (2+ tenants concurrents) — ~4h
- [ ] Profiling endpoints lents (cProfile ou py-spy) — ~2h
- [ ] Cycle backup → restore → vérification données — ~2h
- [ ] Tests SQL injection regression simples — ~1h
- [ ] Load test : 1000 GET /clients concurrents — ~2h
- [ ] Chaos testing : Cosium timeout, retry behavior — ~2h
- [ ] Suite E2E Playwright : auth, CRUD complet, search — ~6h

### Documentation
- [ ] `docs/CONTRIBUTING.md` (git flow, PR process) — ~1h
- [ ] `docs/adr/` Architecture Decision Records — ~2h
- [ ] `docs/RUNBOOK.md` (incidents checklist, recovery) — ~2h
- [ ] `docs/ALEMBIC.md` (migrations, rollback, branching) — ~1h
- [ ] `docs/BUSINESS_RULES.md` (customer, devis, facture, PEC, paiement) — ~1h
- [ ] `docs/DATABASE.md` + ERD (dbdocs.io ou mermaid) — ~2h
- [ ] `docs/RBAC.md` (matrice rôles/permissions) — ~1h
- [ ] `docs/DEPLOY_CHECKLIST.md` production — ~1h
- [ ] `docs/PERFORMANCE.md` (pool, timeouts, Celery tuning) — ~2h
- [ ] `docs/COSIUM_AUTH.md` (3 modes : cookie, OIDC, basic) — ~30min
- [ ] `docs/ENV.md` variables d'environnement exhaustives — ~1h
- [ ] TLS setup guide détaillé (certbot exemples) — ~1h
- [ ] Descriptions OpenAPI enrichies (docstrings routeurs) — ~1h

### Backups avancés
- [ ] Off-site backups S3 (upload après dump) — ~3h
- [ ] Chiffrement backups (gpg ou S3 SSE) — ~1h
- [ ] Monitoring backup (cron vérifie date < 25h) — ~30min
- [ ] Backup MinIO data (documents) — `mc mirror` ou S3 sync — ~2h
- [ ] Test restore périodique hebdomadaire — ~2h

### i18n & avenir
- [ ] Abstraction i18n framework (`next-intl` ou `react-i18n`) — ~1h30
- [ ] Pages "Coming Soon" pour futures features (Copilote IA, Webhooks) — ~30min
- [ ] Copilote IA avec Ctrl+K (chat contextuel client) — ~4h

### Polish & DX
- [ ] Makefile pour dev convenience (`make dev`, `make test`, `make deploy`) — ~1h
- [ ] `docker-compose.override.yml` local dev — ~30min
- [ ] Semantic versioning tags CI (v1.0.0) — ~1h
- [ ] Prettier pre-commit hook (husky) — ~1h
- [ ] Commentaires nginx expliquant choix tuning — ~30min
- [ ] Data migration backfill indexes — ~30min

### Sécurité avancée
- [ ] Rotation secrets documentée (JWT_SECRET, ENCRYPTION_KEY) — ~1h
- [ ] Rate limit anti-brute-force signup/forgot-password — ~1h
- [ ] Certbot staging config avant prod — ~30min
- [ ] Audit trail accès tenant (security logging) — ~1h

---

## 📋 Top 20 priorités immédiates

1. **[P1, 4h]** Tests isolation multi-tenant
2. **[P1, 3h]** Test auth E2E complet
3. **[P1, 2h]** Test endpoints admin 403
4. **[P1, 30min]** Fix `db.commit()` dans `refresh_token_repo`
5. **[P1, 2h]** LoadingState/ErrorState/EmptyState sur 27 pages
6. **[P1, 1h30]** Pagination serveur cases/devis/factures/paiements
7. **[P1, 1h]** ConfirmDialog avant toute suppression
8. **[P1, 4h]** Deploy E2E docker-compose.prod.yml
9. **[P1, 2h]** TLS bout en bout testé
10. **[P2, 8h]** Refacto 19 repos sans `db.commit()`
11. **[P2, 3h]** Audit endpoints Pydantic `response_model`
12. **[P2, 6h]** Batch PEC submission
13. **[P2, 3h]** Auto-relance PEC > 30j
14. **[P2, 3h]** Audit idempotence Celery
15. **[P2, 2h]** Splitter reconciliation_service
16. **[P2, 1h]** Cache deps Python CI
17. **[P2, 2h]** Security scanning (bandit, Dependabot)
18. **[P3, 2h]** Refacto dashboard 664l
19. **[P3, 1h]** Remplacer `window.confirm` par ConfirmDialog
20. **[P4, 4h]** Endpoint `/metrics` Prometheus

---

## 🗺️ Roadmap suggérée

**Sprint 1 (40h)** — Sécurité & prod
P1 complet + démarrage refacto repos

**Sprint 2 (40h)** — Architecture & PEC
P2 architecture + finalisation PEC V12 + tests domaines

**Sprint 3 (40h)** — Frontend refacto & UX
P3 refacto fichiers >300l + composants UI manquants + a11y

**Sprint 4 (40h)** — Observabilité
P4 Prometheus + Grafana + logs agrégés

**Sprint 5 (50h+)** — Polish & docs
P5 docs complètes + tests E2E Playwright + backups off-site

---

## ✅ Rappel PLAN_V12 — État réel

Le plan `docs/PLAN_V12_PEC_INTELLIGENCE.md` affiche toutes les étapes `[ ]` mais **11/12 étapes sont implémentées** :

| Étape | État |
|---|---|
| 1. Liaison client | ✅ `erp_matching_service`, `client_completeness_service` |
| 2. Client↔mutuelle | ✅ `client_mutuelle` complet |
| 3. OCR | ✅ `document_extraction` + `extractions` router |
| 4. Parsers | ✅ 5 parsers (ordonnance, devis, attestation, facture, IA) |
| 5. Consolidation | ✅ `consolidation_service` + 4 modules |
| 6. Incohérences | ✅ intégré consolidation |
| 7-8. PEC prep | ✅ model + schema + service + router |
| 9-10. Frontend PEC | ✅ page 650 lignes (à découper en P3) |
| 11. Tests E2E | ⚠️ partiels |
| 12. Multi-OCAM | ✅ `ocam_operator` |

**Reste V12 uniquement** : batch submission, auto-relance 30j, tracking réponse mutuelle.
