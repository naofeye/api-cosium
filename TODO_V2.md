# TODO V2 — OptiFlow AI — Post-audit de refactoring

> **Date** : 2026-04-07
> **Contexte** : Audit V2 apres le refactoring massif (232 taches V1 terminees)
> **Methode** : Audit profond backend + frontend + infra par Claude Opus
> **Regle** : Cocher `[x]` quand termine. Ne jamais supprimer une ligne.

---

## PHASE 1 — BUGS ET INCOHERENCES POST-REFACTORING (Semaine 1)
> Objectif : corriger les problemes introduits ou reveles par le refactoring

### 1.1 db.query restants dans les routers [ELEVE]
- [x] `api/routers/auth.py` — `logout_all()` migre vers `refresh_token_repo.revoke_all_for_user()`
- [x] `api/routers/admin_health.py` — `db.query(Tenant)` remplace par `onboarding_repo`

### 1.2 db.query restants dans les tasks [ELEVE]
- [x] `tasks/sync_tasks.py` — `db.query(Tenant)` remplace par `onboarding_repo.get_active_cosium_tenants()`
- [x] `tasks/sync_tasks.py` — `db.query(TenantUser)` remplace par `tenant_user_repo`
- [x] `tasks/sync_tasks.py:387` — `db.query(Notification)` acceptable (1 query notification, pattern simple)

### 1.3 Repo avec syntaxe legacy [FAIBLE]
- [x] `repositories/refresh_token_repo.py` — Modernise vers SQLAlchemy 2.0 `update()` statement

### 1.4 Composant frontend orphelin [FAIBLE]
- [x] `CosiumDataSection.tsx` supprime (orphelin confirme)

---

## PHASE 2 — ACCENTS FRANCAIS MANQUANTS (Semaine 1)
> Objectif : corriger les textes utilisateur avec accents manquants

### 2.1 Fichiers frontend avec accents manquants [MOYEN]
- [x] `components/ui/ErrorBoundary.tsx` — 8 corrections accents
- [x] `app/onboarding/steps/StepImport.tsx` — 3 corrections
- [x] `app/reset-password/page.tsx` — 4 corrections
- [x] `app/login/page.tsx` — 1 correction
- [x] `app/factures/[id]/page.tsx` — 1 correction
- [x] `app/onboarding/helpers.ts` — 1 correction
- [x] `app/onboarding/steps/StepAccount.tsx` — 1 correction
- [x] `app/settings/page.tsx` — 1 correction
- [x] `app/admin/users/components/CreateUserDialog.tsx` — 1 correction

---

## PHASE 3 — INFRASTRUCTURE PRODUCTION (Semaine 1-2)
> Objectif : securiser le deploiement en production

### 3.1 Scripts de deploiement [ELEVE]
- [x] `scripts/backup_db.sh` — Credentials parametrables `${POSTGRES_USER:-optiflow}`
- [x] `scripts/restore_db.sh` — Idem
- [x] `scripts/deploy.sh` — Validation env vars (JWT_SECRET, ENCRYPTION_KEY) + credentials parametrables

### 3.2 Docker Compose production [ELEVE]
- [x] `docker-compose.prod.yml` — MinIO restreint a `127.0.0.1:9000:9000` et `127.0.0.1:9001:9001`
- [x] DEPLOY.md : documente MinIO self-hosted + worker -B beat

### 3.3 Nginx securite [MOYEN]
- [x] `nginx/nginx.conf:32` — CSP documente : unsafe-inline/unsafe-eval requis par Next.js hydration
- [x] `nginx/nginx.conf` — Commentaire explicite ajoute pour le domaine

### 3.4 CI/CD corrections [MOYEN]
- [x] `.github/workflows/ci.yml` — `ENCRYPTION_KEY` ajoute dans `security-check`
- [x] `.github/workflows/ci.yml` — `alembic upgrade head` ajoute dans `backend-tests`
- [x] `.github/workflows/ci.yml` — Job `gitignore-check` ajoute

### 3.5 Documentation [FAIBLE]
- [x] `CLAUDE.md` — Mis a jour : "Migrations : Alembic (configure, upgrade head)"
- [x] `.gitignore` — `**/*.pid` et `celerybeat-schedule*` ajoutes
- [x] DEPLOY.md — Clarifie que `-B` gere le beat en prod (section Worker Celery ajoutee)

---

## PHASE 4 — SERVICES > 300 LIGNES RESTANTS (Semaine 2-3)
> Objectif : derniers gros fichiers a evaluer

### 4.1 Services backend > 300 lignes [MOYEN]
- [x] `reconciliation_service.py` (484l) — Logique dense de rapprochement, split non justifie (domaine unique)
- [x] `export_service.py` (480l) — Facade qui orchestre les sous-modules export_pdf_*, acceptable
- [x] `erp_sync_extras.py` (455l) — Bulk sync upsert, acceptable (pattern specifique)
- [x] `ocr_service.py` (383l) — Traitement OCR monolithique, split non justifie
- [x] `cosium_document_sync.py` (356l) — Bulk sync, acceptable
- [x] `client_mutuelle_service.py` (350l) — Detection analytics, logique dense acceptable

### 4.2 Pages frontend > 300 lignes [MOYEN]
- [x] `dashboard/page.tsx` (651l) — Deja 6+ composants importes, split additionnel non justifie
- [x] `pec-preparation/[prepId]/page.tsx` (648l) — Formulaire dynamique complexe, state trop couple pour split propre
- [x] `TabResume.tsx` (493l) — Onglet resume avec sections multiples, acceptable
- [x] `TabCosiumDocuments.tsx` (432l) — Logique de documents specifique, acceptable
- [x] `Sidebar.tsx` (422l) — Navigation complexe avec collapse/expand, acceptable
- [x] `rapprochement/page.tsx` (390l) — Seulement 90l au-dessus du seuil, acceptable
- [x] `PreControlPanel.tsx` (337l) — Composant metier dense, acceptable
- [x] `ConsolidatedFieldDisplay.tsx` (334l) — Affichage complexe, acceptable

---

## PHASE 5 — DB COMMITS DANS LES REPOSITORIES (Semaine 3-4)
> Objectif : les repos ne doivent PAS commiter, les services commitent

### 5.1 Audit des db.commit() dans les repos [MOYEN]
- [x] Audit fait : 50+ db.commit() dans 19 repos. Top : marketing(6), reminder(5), pec(5), notification(5)
- [x] Strategie definie : migrer progressivement, commencer par les repos utilises dans des transactions multi-entites
- [x] `client_repo` migre : 4x db.commit() → db.flush() (create, update, delete, restore)
- [x] TOUS les repos migres : 50+ db.commit() → db.flush() dans 19 fichiers (sauf refresh_token_repo: commit necessaire)

---

## PHASE 6 — TESTS E2E ET VALIDATION (Semaine 4-6)
> Objectif : valider en conditions reelles

### 6.1 Tests d'integration [MOYEN]
- [x] Test : user du tenant A ne peut PAS acceder aux donnees du tenant B (test_auth_e2e.py)
- [x] Test : login → access token → refresh → switch tenant → logout (test_auth_e2e.py)
- [x] Test : endpoints admin proteges par authentification admin (test_auth_e2e.py)
- [x] Test : deconnexion, expiration token, token blackliste (test_auth_e2e.py)

### 6.2 Validation production [MOYEN]
- [ ] Tester un deploiement complet de bout en bout avec docker-compose.prod.yml
- [ ] Tester la terminaison TLS de bout en bout (necessite un vrai domaine)
- [ ] Tester un cycle backup → restore → verification donnees
- [ ] Tester avec 2+ tenants actifs en parallele

### 6.3 Validation sync [MOYEN]
- [ ] Tester la sync Cosium avec un jeu de donnees realiste
- [ ] Verifier que la sync ne cree pas de N+1 queries
- [ ] Profiler les endpoints les plus lents

---

## PHASE 7 — AMELIORATIONS PROGRESSIVES (Ongoing)
> Objectif : polissage continu

### 7.1 Frontend UX [FAIBLE]
- [x] `window.confirm()` — 2 occurrences dans `useUnsavedChangesWarning.ts`, contexte synchrone obligatoire (navigation guard), correct
- [x] `window.open()` — 6 occurrences, toutes pour downloads/PDF/mailto, pattern correct
- [x] Types TypeScript stricts pour admin : `lib/types/admin.ts` (health, metrics, data-quality, sync)

### 7.2 Monitoring [FAIBLE]
- [ ] Ajouter un endpoint `/metrics` Prometheus-compatible (optionnel)
- [ ] Monitorer les temps de reponse des endpoints critiques
- [ ] Monitorer la taille de la queue Celery
- [ ] Ajouter des alertes sur les erreurs 5xx en production

### 7.3 Celery [FAIBLE]
- [x] `reminder_tasks.py` — Email delegue via `send_email_async.delay()` (async)
- [x] `batch_tasks.py` — Progression visible en BDD tous les 100 items
- [x] `db/session.py` — Statement timeout separe : 30s API, 300s Celery (detection auto via env)

### 7.4 Securite incrementale [FAIBLE]
- [x] Idempotence Celery deja implementee via cles Redis (sync, reminders, overdue)
- [x] Index composites deja ajoutes sur (tenant_id, status) pour Payment et Facture, (tenant_id, numero) pour Devis/Facture/PayerOrg

---

## SUIVI GLOBAL

| Phase | Description | Taches | Priorite |
|-------|-------------|--------|----------|
| Phase 1 | Bugs post-refactoring | 7/7 | **FAIT** |
| Phase 2 | Accents francais | 9/9 | **FAIT** |
| Phase 3 | Infrastructure production | 8/11 | 73% |
| Phase 4 | Services/pages > 300l | 14/14 | **FAIT** |
| Phase 5 | DB commits dans repos | 2/4 | 50% |
| Phase 6 | Tests E2E et validation | 0/10 | 0% (Docker) |
| Phase 7 | Ameliorations progressives | 2/12 | 17% |
| **TOTAL** | | **42/67** | **63%** |

---

## NOTES D'AUDIT V2

### Ce qui est BIEN apres le refactoring
- **0 `except Exception` non justifie** dans les services (tous remplaces ou documentes)
- **0 `HTTPException` dans les services** (toutes remplacees par exceptions metier)
- **0 `print()`** dans tout le backend
- **0 `any`** dans le frontend TypeScript
- **0 `console.log`** non controle dans le frontend
- **Tous les imports** des sous-modules sont corrects et resolvent
- **Tous les re-exports** des facades sont complets (verifie router par router)
- **Tous les nouveaux repos** sont effectivement utilises
- **266 fichiers Python** compilent sans erreur de syntaxe
- **Token blacklist Redis** operationnelle
- **18 tests de regression** securite en place
- **CI GitHub Actions** avec 4 jobs paralleles
- **DEPLOY.md** complet avec 9 sections

### Ce qui reste a ameliorer
- 3 routers ont encore des `db.query` directs (auth, admin_health)
- 6 appels `db.query` dans sync_tasks.py
- 11 services backend > 300 lignes (mais la plupart sont des patterns bulk/facade acceptables)
- 16 fichiers frontend > 300 lignes (la plupart deja componentises ou complexes par nature)
- 9 fichiers frontend avec accents manquants
- Scripts de deploiement avec credentials hardcodes
- CI manque `ENCRYPTION_KEY` et test de migration
