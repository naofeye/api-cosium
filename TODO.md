# TODO — OptiFlow AI (polish & nice-to-have)

> Session du 2026-04-13 : 23 items P1/P2 fermés (commit `b5b66d6`).
> Reste : **~220 items, ~310h** dont la majorité est polish & nice-to-have.
> Roadmap suggérée : Sprint polish 60h → Sprint observabilité 40h → Sprint nice-to-have 80h+.

---

## 📊 Vue d'ensemble

| Bloc | Items | Effort | Impact |
|------|-------|--------|--------|
| **A. Reste critique prod** | 12 | ~25h | Déploiement réel, sécu, data integrity |
| **B. Architecture & tests** | 40 | ~55h | Dette technique, fiabilité |
| **C. Polish frontend** | 45 | ~50h | UX, accessibilité, mobile, perfs |
| **D. Polish backend** | 25 | ~30h | Code quality, refactor, logs |
| **E. Observabilité** | 20 | ~30h | Prometheus, Grafana, Sentry |
| **F. Documentation** | 18 | ~25h | Docs techniques + runbook |
| **G. Nice-to-have features** | 35 | ~60h | Copilote IA, i18n, mobile, extras |
| **H. DX & outillage** | 15 | ~15h | Makefile, pre-commit, scripts |
| **I. Infra avancée** | 10 | ~20h | Backups S3, chaos, load |

---

## 🔴 A. Reste critique (prod blockers, ~25h)

### Déploiement
- [ ] Déploiement E2E `docker-compose.prod.yml` testé bout en bout — ~4h
- [ ] TLS bout en bout avec vrai cert (mkcert local ou Let's Encrypt) — ~2h
- [ ] Variables `.env.prod.example` exhaustives documentées — ~1h
- [ ] Certbot staging config testée avant prod — ~30min
- [x] Health endpoint `/health/deep` (DB + Redis + MinIO + Cosium) — déjà implémenté dans `admin_health.py:62` — ~1h

### Sécurité & RBAC
- [x] Rate limiting global API (60r/s burst 120) en plus du login — ~1h
- [ ] Rate limit anti-brute-force signup/forgot-password — ~1h
- [ ] Audit trail accès tenant (security logging) — ~1h
- [x] Bloquer `/redoc` en plus de `/docs` en prod — ~20min
- [ ] Rotation secrets documentée (JWT_SECRET, ENCRYPTION_KEY) — ~1h

### Data integrity
- [ ] Test rollback migration Alembic (`alembic downgrade -1 && upgrade +1` en CI) — ~1h
- [ ] Index sur Cosium* (tenant_id, status, created_at) — ~1h
- [ ] Vérifier index sur Marketing/Interaction/Notification — ~30min
- [x] Pool PostgreSQL tuning (`max_connections=150`, `idle_in_transaction_session_timeout=60s`, slow query 500ms) — ~30min
- [ ] Celery beat monitoring heartbeat — ~1h
- [ ] Redis éviction policy (`maxmemory 512mb --maxmemory-policy allkeys-lru`) — ~30min

---

## 🟠 B. Architecture & tests (~55h)

### Refacto backend (dette)
- [ ] Refacto 19 repos : retirer `db.commit()` → services, repos `db.flush()` — ~8h
- [x] Dict → Pydantic `pec_preparation.py` 3 endpoints : `PecPreparationListResponse` + `PecSubmissionResponse` + `PrecontrolResponse` (sous-schemas inclus) — ~1h
- [x] Dict → Pydantic `cosium_documents.py:80` → `BulkSyncResponse` (started+task_id ou completed+BulkSyncResult) — ~1h
- [x] Audit `response_model` Pydantic sur tous les routers (audit 221 endpoints, 55 sans sont légitimes : 204 No Content + StreamingResponse exports/SSE) — ~3h
- [x] Splitter `reconciliation_service.py` 517→341l + `_reconciliation_helpers.py` 165l ; reconcile_customer_dossier 217→101l — ~2h
- [x] Splitter `export_service.py` 480→186l (facade) + `_export_styles.py` 28l + `export_xlsx_balance.py` 67l + `export_xlsx_clients.py` 82l + `export_xlsx_pec.py` 110l — ~2h
- [x] Splitter `erp_sync_extras.py` 455→24l facade + `erp_sync_products.py` 63l + `erp_sync_payments.py` 105l + `erp_sync_third_party.py` 74l + `erp_sync_prescriptions.py` 108l + `_erp_sync_helpers.py` 88l (BATCH_SIZE, parse_iso_date, batch_flush, customer lookup) — ~2h
- [x] Splitter `client_mutuelle_service.py` 353→203l + `_client_mutuelle_detection.py` 178l (3 sources detection extraites + persistence helper) — ~1h
- [x] Refacto `consolidation_*.py` : helpers 306→212l + `consolidation_loaders.py` 109l extraits ; déjà splitté en sous-modules identity/optical/financial donc pas besoin de `BaseConsolidator` (pattern fonctionnel pur) — ~2h
- [x] Splitter `search_service.global_search()` 216→27l (orchestration) + 7 helpers privés par entité (clients/SSN/cases/devis/factures/cosium/prescriptions/OCR) — ~2h
- [ ] Migrer listes vers `PaginatedResponse[T]` + total (cases/devis/factures/paiements) — ~3h
- [ ] Renommer `pec_preparation_service` → `pec_assistant_service` — ~30min
- [ ] Pattern repository uniforme : interface commune, méthodes standardisées — ~3h

### Celery & async
- [ ] Audit idempotence Celery (EXISTS avant INSERT) — ~3h
- [ ] Déléguer email sync → `email_tasks.py` — ~2h
- [ ] Dead-letter queue Celery — ~1h
- [ ] Retry policy documentée (`docs/CELERY.md`) — ~30min
- [ ] Test : tâche échoue → retry → réussit — ~1h
- [ ] Batch tasks : update statut tous les 100 items (progression visible) — ~1h
- [ ] Task timeout explicite par type (hard_time_limit) — ~1h

### PEC Plan V12
- [ ] Batch PEC submission `POST /pec/batch` — ~6h
- [ ] Auto-relance PEC > 30j sans réponse — ~3h
- [ ] Tracking statut réponse mutuelle — ~2h
- [ ] PDF PEC : inclure corrections utilisateur — ~1h
- [ ] Fermer `[ ]` de `PLAN_V12_PEC_INTELLIGENCE.md` — ~30min

### Tests domaines manquants
- [ ] Test facturation + paiements sync Cosium — ~1h
- [ ] Test reconciliation paiement-facture (lettrage multi-partiel) — ~1h
- [ ] Test export FEC format légal — ~1h
- [ ] Test GDPR right-to-be-forgotten — ~1h
- [ ] Test OCR parsers (ordonnance, devis, attestation) — ~1h
- [ ] Test Claude API error handling — ~1h
- [ ] Test marketing campaign complet — ~1h
- [ ] Test consent RGPD — ~1h
- [ ] Test reminder plan exécution — ~1h
- [ ] Test Stripe webhook — ~1h
- [ ] Test banking import CSV → Payment match — ~1h
- [ ] Test health endpoint — ~1h
- [ ] Test cycle cookie httpOnly — ~2h
- [ ] Tests hooks frontend (useClients, useCase, useDashboard) — ~2h

---

## 🟡 C. Polish frontend (~50h)

### Pages métier CRUD à finaliser
- [ ] Clients : édition inline + archivage — ~1h
- [ ] Factures Cosium : badge read-only + filtres + export CSV — ~45min
- [ ] Devis : création AsyncSelect + confirmation soumission — ~1h
- [ ] Paiements : formulaire création + rapprochement drag-drop — ~1h30
- [ ] PEC préparation : validation champs + confirmation — ~1h
- [ ] Rapprochement bancaire : validation + undo + double-clic protection — ~1h30
- [ ] Relances : envoi masse avec confirmation + retry — ~1h
- [ ] Marketing campagnes : CRUD + segmentation — ~2h
- [ ] Admin sync Cosium : "Sync now" + modal progression — ~1h
- [ ] Admin utilisateurs : édition + reset password — ~1h30
- [ ] Settings : validation + toast succès partout — ~1h

### Refacto fichiers >300 lignes
- [x] `dashboard/page.tsx` 664→145l (types, utils, 7 panneaux extraits + 2 hooks SWR/Export) — ~2h
- [x] `rapprochement/page.tsx` 390→148l (types, KPIs, Toolbar, TransactionsTable, useRapprochementActions) — ~1h30
- [x] `notifications/page.tsx` 384→188l (types, utils, NotificationCard, NotificationFilters) — ~1h
- [x] `aide/page.tsx` 338→58l (data, FAQAccordion, HelpQuickLinks, CosiumCookieGuide, ShortcutsTable, DocumentationLinks/SupportContact) — ~1h30
- [x] `Sidebar.tsx` 433→171l (split en navConfig, SidebarGroup, SidebarItem, useCollapsedGroups + SidebarHeader inline) — ~1h
- [x] `pec-dashboard/page.tsx` 320→73l (types, PecKpiCards, PecToolbar, PecPreparationsTable, useExportXlsx) — ~1h
- [x] `pec-preparation/[prepId]/page.tsx` 648→128l (utils, usePecActions, CopyPasteSummary, PecHeader, PecSections, PecActionBar) — ~2h
- [x] `clients/page.tsx` 313→184l (hooks useClientsSelection + useClientsDuplicates, BatchActionBar, clientsColumns) — ~1h

### Accessibilité WCAG AA
- [ ] Audit `aria-label` toutes icônes seules — ~1h
- [ ] Audit `focus-visible` sur tous interactifs — ~1h
- [ ] Contraste WCAG AA (outils automatisés) — ~1h30
- [ ] Navigation clavier (Tab order, Escape, tri) — ~1h
- [ ] Form labels/inputs (id + htmlFor) — ~30min
- [ ] `role="alert"` + ARIA live regions pour erreurs — ~1h
- [ ] `aria-hidden` sur icônes décoratives — ~30min
- [ ] Skip links ("passer au contenu") — ~30min

### Code quality frontend
- [ ] Remplacer `window.confirm()` par ConfirmDialog — ~1h
- [ ] Remplacer `window.open()` par liens Next.js propres — ~1h
- [ ] Types TS stricts `lib/types/admin.ts` — ~2h
- [ ] Centraliser types inline → `lib/types/` — ~45min
- [ ] Zod schemas manquants (facture, rapprochement, relance) — ~1h
- [ ] Hooks API génériques typés — ~1h
- [x] Retirer tous `console.log` de debug — déjà OK, audit grep vide — ~30min
- [ ] Bannir `any` restants (grep + type) — ~1h

### UX polish
- [ ] Tooltips sur icônes sans label — ~1h
- [ ] Animations page transitions (éviter flicker) — ~1h
- [ ] Empty/error states avec illustrations légères — ~1h
- [ ] Print styles `@media print` pour rapports — ~1h
- [ ] Mobile polish <1366px (sidebar, DataTable) — ~2h
- [ ] Dark mode (toggle + tokens) — ~4h
- [ ] Raccourcis clavier globaux documentés (Ctrl+K, ?, Echap) — ~1h
- [ ] Onboarding tour première connexion — ~2h
- [ ] Toasts auto-dismiss configurables (delay par variant) — ~30min

### Performance frontend
- [ ] Pagination serveur sur tous les hooks — ~1h30
- [ ] `React.lazy` pour pages lourdes (Recharts) — ~1h
- [ ] `<img>` → `next/image` partout — ~1h
- [ ] SWR `stale-while-revalidate` cohérent — ~45min
- [ ] Bundle size audit (`next/bundle-analyzer`) — ~2h
- [ ] Lighthouse ≥90 (Perf + A11y) — ~4h
- [ ] Font-display swap sur Inter/system — ~15min
- [ ] Prefetch hover sur liens Sidebar — ~30min

### Composants UI manquants
- [ ] `Timeline.tsx` chronologie verticale — ~1h
- [ ] `AgingTable.tsx` balance agée couleurs tranches — ~1h
- [ ] `DateRangePicker.tsx` — ~1h
- [ ] `FileUploadZone.tsx` drag-drop multi — ~1h
- [ ] `AsyncSelect.tsx` (autocomplete backend) — ~1h30
- [ ] `Stepper.tsx` (formulaires multi-étapes) — ~1h

---

## 🟡 D. Polish backend (~30h)

### Code quality
- [ ] Supprimer dead code (ruff) — ~1h
- [ ] Docstrings fonctions publiques (91 services) — ~2h
- [ ] Type hints return partout — ~1h
- [ ] Nettoyer commentaires obsolètes — ~30min
- [ ] Préfixer méthodes privées `_x` → `__x` — ~30min
- [ ] Validations Pydantic (min/max, regex email/phone) — ~30min
- [ ] Naming cohérent : tous les services en `*_service.py` — ~30min
- [x] Imports absolus partout (bannir relatifs) — déjà OK, audit grep vide — ~30min
- [ ] `__all__` dans les modules publics — ~30min

### Logs & observabilité light
- [ ] Request/response logging middleware (méthode, chemin, user, tenant, durée) — ~1h
- [ ] Structured logs : `entity_type`, `entity_id`, `action` cohérents partout — ~2h
- [ ] Trace ID propagé dans logs Celery — ~1h
- [x] Slow query logging PostgreSQL (`log_min_duration_statement=500`) — ~30min
- [ ] Sentry custom tags (tenant_id, user_id, endpoint) — ~1h
- [ ] Log rotation configurée (size + time) — ~30min

### Nginx/infra polish
- [ ] `X-Request-ID` logging nginx — ~30min
- [x] Aligner `client_max_body_size` nginx 25M ↔ `MAX_UPLOAD_SIZE_MB=20` — ~20min
- [ ] Commentaires nginx expliquant le tuning — ~30min
- [ ] Health check API via `curl` (pas exec Python) — ~20min

### Scripts maintenance
- [x] `restore_db.sh` : `--dry-run` + pre-restore backup automatique + `--no-pre-backup` — ~1h
- [x] `backup_db.sh` : check espace disque (`BACKUP_MIN_FREE_MB`) + `BACKUP_RETENTION_DAYS` configurable — ~45min
- [ ] `scripts/rollback.sh` orchestrant restore + restart — ~2h
- [ ] `scripts/seed_demo.sh` environnement de démo — ~1h
- [ ] Data migration backfill indexes — ~30min
- [ ] N+1 audit sync Cosium (eager loading) — ~2h
- [ ] Circuit breaker Cosium API (5 erreurs → fail fast) — ~1h

---

## 🔵 E. Observabilité (~30h)

### Métriques
- [ ] Endpoint `/metrics` Prometheus — ~4h
- [ ] Middleware histogram temps réponse par endpoint — ~2h
- [ ] Monitoring queue Celery (Flower ou custom) — ~2h
- [ ] Sentry custom metrics (facturation, OCR rate) — ~1h

### Alerting
- [ ] Alertes Sentry 5xx — ~1h
- [ ] Alertmanager ou webhook PagerDuty — ~2h
- [x] Monitoring backup (`scripts/backup_monitor.sh` — cron + webhook alert) — ~30min
- [ ] Alert si queue Celery > 100 tasks — ~1h
- [ ] Alert si disque /var > 80% — ~30min

### Stack monitoring
- [ ] `docker-compose.monitoring.yml` (Prometheus + Grafana) — ~4h
- [ ] Dashboards Grafana (latence, erreurs, queue, DB) — ~3h
- [ ] Logs agrégés (fluent-bit ou Datadog) — ~4h
- [ ] Loki + Promtail pour logs structurés — ~3h
- [ ] Distributed tracing (OpenTelemetry) — ~4h

### CI/CD
- [ ] Test coverage Codecov — ~1h
- [ ] Matrice Python 3.11/3.12 + Node 18/20 — ~1h
- [ ] Branch protection rules — ~30min
- [x] Dependabot activé (npm + pip + actions + docker) — `.github/dependabot.yml` — ~30min
- [x] CodeQL static analysis (Python + JS/TS, security-extended, weekly cron) — ~1h30

---

## 📚 F. Documentation (~25h)

- [ ] `docs/CONTRIBUTING.md` (git flow, PR) — ~1h
- [ ] `docs/adr/` Architecture Decision Records — ~2h
- [ ] `docs/RUNBOOK.md` (incidents, recovery) — ~2h
- [ ] `docs/ALEMBIC.md` (migrations, rollback) — ~1h
- [ ] `docs/BUSINESS_RULES.md` (clients, devis, PEC, paiement) — ~1h
- [ ] `docs/DATABASE.md` + ERD (mermaid) — ~2h
- [x] `docs/RBAC.md` matrice rôles/permissions (4 roles + group_admin, par module) — ~1h
- [x] `docs/DEPLOY_CHECKLIST.md` (pre-requis, pre/post-deploy, rollback, TLS, monitoring) — ~1h
- [ ] `docs/PERFORMANCE.md` (pool, timeouts, Celery) — ~2h
- [x] `docs/COSIUM_AUTH.md` (3 modes : basic, OIDC, cookie + rotation) — ~30min
- [x] `docs/ENV.md` variables exhaustives (~50 vars + exemple .env.prod) — ~1h
- [ ] `docs/DATABASE_INDEXES.md` stratégie — ~30min
- [ ] TLS setup guide détaillé — ~1h
- [ ] OpenAPI descriptions enrichies — ~1h
- [x] `docs/CELERY.md` (architecture, retry, idempotence, beat, monitoring, troubleshoot) — ~30min
- [ ] `README.md` "Quick start 5 minutes" actualisé — ~1h
- [ ] Storybook pour composants UI — ~6h
- [ ] Video demo 3 min workflows clés (Loom) — ~2h

---

## 🟢 G. Nice-to-have features (~60h)

### Copilote IA
- [ ] Ctrl+K chat contextuel client — ~4h
- [ ] Suggestions automatiques relances (IA propose texte) — ~3h
- [ ] Auto-categorisation documents entrants (OCR + IA) — ~4h
- [ ] Résumé automatique dossier client (IA synthèse) — ~2h
- [ ] Détection anomalies factures (montants inhabituels) — ~3h

### Internationalisation
- [ ] Abstraction i18n (`next-intl` ou `react-i18n`) — ~1h30
- [ ] Traduction EN pour export international — ~4h
- [ ] Formats dates/montants locales (DE, ES, IT) — ~1h
- [ ] RTL support (futur marché MENA) — ~2h

### Features métier
- [ ] Export PDF personnalisable (logo, couleurs tenant) — ~3h
- [ ] Factures récurrentes (abonnements clients) — ~4h
- [ ] Devis signature électronique (YouSign/DocuSign) — ~6h
- [ ] Scan QR code pour cartes mutuelles — ~3h
- [ ] Intégration calendrier (Google/Outlook) rendez-vous — ~4h
- [ ] Portail client public (consultation devis/factures) — ~8h
- [ ] Module stock/SAV (montures cassées, retours) — ~6h
- [ ] Livre de caisse + clôture journalière — ~3h

### Marketing
- [ ] Campagnes SMS (Twilio/OVH) — ~2h
- [ ] Templates emails riches (MJML) — ~2h
- [ ] A/B testing campagnes — ~3h
- [ ] Segments dynamiques (âge correction, dernière visite) — ~2h
- [ ] Birthday automations — ~1h
- [ ] NPS post-vente automatique — ~2h

### Intégrations
- [ ] Webhooks entrants configurables (partenaires) — ~4h
- [ ] Export comptable Cegid/Sage — ~4h
- [ ] Import mutuelles (Almerys, Sante Claire, Viamedis) — ~6h
- [ ] API publique v1 (tokens partenaires) — ~4h
- [ ] Connecteur Zapier/Make — ~3h

### Dashboard & analytics
- [ ] Drill-down graphiques (cliquer KPI → détail) — ~2h
- [ ] Comparaisons période (YoY, MoM) — ~2h
- [ ] Export Excel rapports personnalisables — ~2h
- [ ] Heatmap horaires fréquentation — ~2h
- [ ] Forecast CA (prédiction IA) — ~4h

### Pages "Coming Soon"
- [x] Copilote IA (teaser + waitlist) — ~30min
- [x] Webhooks (teaser) — ~30min
- [x] API publique (teaser + tokens) — ~30min
- [x] Mobile app (teaser Android/iOS) — ~30min

---

## 🛠️ H. DX & outillage (~15h)

- [x] Makefile enrichi (help auto, lifecycle, shells, tests, migrations, deploy, clean) — ~1h
- [ ] `docker-compose.override.yml` local dev — ~30min
- [ ] Semantic versioning tags CI — ~1h
- [ ] Prettier pre-commit hook (husky) — ~1h
- [ ] Ruff pre-commit hook — ~30min
- [x] `.editorconfig` cohérent multi-IDE — ~15min
- [x] Dev containers VS Code (`.devcontainer/devcontainer.json` avec extensions + ports) — ~2h
- [ ] Génération clients API typés (openapi-typescript) — ~1h30
- [ ] `pnpm` workspace (perfs + deduplication) — ~1h
- [x] `.gitmessage` template conventional commits — ~30min
- [ ] Script bootstrap nouveau développeur (`setup.sh` amélioré) — ~1h
- [ ] Alias bash/zsh commandes fréquentes — ~30min
- [ ] Swagger UI auth preset (token pré-rempli) — ~30min
- [ ] Debug profiles VS Code (launch.json) — ~30min
- [ ] Seed dev data generator (Faker) — ~2h

---

## 🏗️ I. Infra avancée (~20h)

### Backups avancés
- [ ] Off-site backups S3 — ~3h
- [ ] Chiffrement backups (gpg ou S3 SSE) — ~1h
- [ ] Backup MinIO documents (mc mirror) — ~2h
- [ ] Test restore périodique hebdo — ~2h
- [ ] Backup encryption keys rotation — ~1h

### Tests stress
- [ ] Profiling endpoints lents (cProfile/py-spy) — ~2h
- [ ] Cycle backup → restore → vérif — ~2h
- [ ] Tests SQL injection regression — ~1h
- [ ] Load test 1000 GET /clients concurrents — ~2h
- [ ] Chaos testing (Cosium timeout, Redis down) — ~2h
- [ ] Suite E2E Playwright complète — ~6h
- [ ] Tests multi-tenant parallèles — ~4h

---

## 🎯 Roadmap suggérée

| Sprint | Focus | Items | Effort |
|--------|-------|-------|--------|
| **Sprint polish 1** | A + D critiques | 25 | 40h |
| **Sprint frontend** | C (polish + refacto) | 30 | 40h |
| **Sprint architecture** | B (dette + tests) | 20 | 35h |
| **Sprint observabilité** | E + partie F | 15 | 30h |
| **Sprint documentation** | F complet | 18 | 25h |
| **Sprint features** | G (nice-to-have prio) | 15 | 35h |
| **Sprint DX + infra** | H + I | 25 | 35h |

Total ~240h ≈ 6 semaines 1 dev ou 3 semaines 2 devs.

---

## 📌 Top 15 quick wins à faire en premier

Items <1h, impact visible, sans dépendance :

1. `[D, 20min]` Bloquer `/redoc` prod
2. `[D, 20min]` Aligner `client_max_body_size` nginx/API
3. `[D, 20min]` Health check API via curl
4. `[A, 30min]` Redis maxmemory + LRU policy
5. `[A, 30min]` Certbot staging config
6. `[D, 30min]` Dedup pool PG tuning
7. `[C, 30min]` Form labels/inputs id+htmlFor
8. `[C, 30min]` `aria-hidden` icônes décoratives
9. `[C, 30min]` Retirer `console.log` debug
10. `[D, 30min]` Imports absolus bannir relatifs
11. `[E, 30min]` Dependabot activé
12. `[E, 30min]` Monitoring backup cron
13. `[F, 30min]` `docs/CELERY.md` retry
14. `[F, 30min]` `docs/COSIUM_AUTH.md`
15. `[H, 15min]` `.editorconfig` cohérent

Total : ~7h pour 15 améliorations visibles.

---

## ✅ Session 2026-04-13 — fait (récap)

Commit `b5b66d6` : 19 fichiers, +843/-83.

**P1 critique (11)** : MinIO enforcement, CSP unsafe-eval retiré, DB timeout Celery, docker-compose.prod.yml, deploy.sh idempotent, healthchecks Celery, tests isolation multi-tenant (3), tests auth E2E (5), test_admin_auth.py (6), ConfirmDialog audit, states audit.

**P2 (7)** : cache pip CI, cache npm CI, backend-security job (bandit+pip-audit), Card.tsx, Badge.tsx, Input.tsx, Select.tsx, Breadcrumb.tsx, `PaginatedResponse[T]` + `MessageResponse`.

Tests verts : 9 pytest.
