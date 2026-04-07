# TODO V2 — OptiFlow AI — Post-audit de refactoring

> **Date** : 2026-04-07
> **Contexte** : Audit V2 apres le refactoring massif (232 taches V1 terminees)
> **Methode** : Audit profond backend + frontend + infra par Claude Opus
> **Regle** : Cocher `[x]` quand termine. Ne jamais supprimer une ligne.

---

## PHASE 1 — BUGS ET INCOHERENCES POST-REFACTORING (Semaine 1)
> Objectif : corriger les problemes introduits ou reveles par le refactoring

### 1.1 db.query restants dans les routers [ELEVE]
- [ ] `api/routers/auth.py:163` — `logout_all()` utilise `db.query(RefreshToken)` → remplacer par `refresh_token_repo.revoke_all_for_user()`
- [ ] `api/routers/admin_health.py:38,235` — `_check_cosium_status()` et `test_cosium_connection()` utilisent `db.query(Tenant)` → deplacer dans le service

### 1.2 db.query restants dans les tasks [ELEVE]
- [ ] `tasks/sync_tasks.py:41,175,334` — `db.query(Tenant).filter(...)` → utiliser `onboarding_repo.get_tenant_by_id()` ou creer un `tenant_repo`
- [ ] `tasks/sync_tasks.py:202,373` — `db.query(TenantUser)` → utiliser `tenant_user_repo`
- [ ] `tasks/sync_tasks.py:387` — `db.query(Notification)` → creer `notification_repo.exists_recent()` ou laisser (1 query)

### 1.3 Repo avec syntaxe legacy [FAIBLE]
- [ ] `repositories/refresh_token_repo.py:41` — `db.query(RefreshToken).update()` → migrer vers SQLAlchemy 2.0 `update()` statement

### 1.4 Composant frontend orphelin [FAIBLE]
- [ ] `frontend/src/app/dashboard/components/CosiumDataSection.tsx` — Non importe nulle part → supprimer

---

## PHASE 2 — ACCENTS FRANCAIS MANQUANTS (Semaine 1)
> Objectif : corriger les textes utilisateur avec accents manquants

### 2.1 Fichiers frontend avec accents manquants [MOYEN]
- [ ] `components/ui/ErrorBoundary.tsx` — 8 corrections : rencontree, passe→passe, prevu→prevu, entiere, Reessayer, details
- [ ] `app/onboarding/steps/StepImport.tsx` — 3 corrections : succes→succes, Reessayer, etape
- [ ] `app/reset-password/page.tsx` — 4 corrections : caracteres, succes, redirige, Repetez
- [ ] `app/login/page.tsx` — 1 correction : oublie→oublie
- [ ] `app/factures/[id]/page.tsx` — 1 correction : entierement
- [ ] `app/onboarding/helpers.ts` — 1 correction : caracteres
- [ ] `app/onboarding/steps/StepAccount.tsx` — 1 correction : caracteres
- [ ] `app/settings/page.tsx` — 1 correction : caracteres
- [ ] `app/admin/users/components/CreateUserDialog.tsx` — 1 correction : caracteres

---

## PHASE 3 — INFRASTRUCTURE PRODUCTION (Semaine 1-2)
> Objectif : securiser le deploiement en production

### 3.1 Scripts de deploiement [ELEVE]
- [ ] `scripts/backup_db.sh:24` — Remplacer `-U optiflow` hardcode par `${POSTGRES_USER:-optiflow}`
- [ ] `scripts/restore_db.sh:35` — Idem pour les credentials hardcodes
- [ ] `scripts/deploy.sh` — Ajouter une validation des variables d'environnement obligatoires avant deploiement
- [ ] `scripts/deploy.sh:17-18` — Utiliser `${POSTGRES_USER}` au lieu de `optiflow` hardcode

### 3.2 Docker Compose production [ELEVE]
- [ ] `docker-compose.prod.yml` — MinIO expose sur `0.0.0.0` → restreindre a `127.0.0.1:9000:9000` ou supprimer en faveur de S3 manage
- [ ] Documenter dans DEPLOY.md que MinIO en prod est pour du self-hosted uniquement

### 3.3 Nginx securite [MOYEN]
- [ ] `nginx/nginx.conf:32` — CSP avec `unsafe-inline` et `unsafe-eval` → documenter pourquoi (Next.js) ou migrer vers nonces
- [ ] `nginx/nginx.conf` — Ajouter un commentaire plus explicite : `# CHANGER: your-domain.com -> votre-domaine.com`

### 3.4 CI/CD corrections [MOYEN]
- [ ] `.github/workflows/ci.yml` — Ajouter `ENCRYPTION_KEY` dans le job `security-check`
- [ ] `.github/workflows/ci.yml` — Ajouter une etape `alembic upgrade head` dans `backend-tests` pour verifier les migrations
- [ ] `.github/workflows/ci.yml` — Ajouter une verification `.gitignore` (pas d'artefacts commites)

### 3.5 Documentation [FAIBLE]
- [ ] `CLAUDE.md:42` — Mettre a jour : "Migrations : Alembic (configure, utilise upgrade head)" au lieu de "a configurer, create_all"
- [ ] `.gitignore` — Ajouter `**/.env*.local` et `**/*.pid`
- [ ] DEPLOY.md — Clarifier que `-B` dans le worker gere le beat scheduling en prod

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
- [ ] Migrer `client_repo` (4 commits) — utilise dans merge/import qui sont multi-entites
- [ ] Migrer les autres repos progressivement au fil des sprints

---

## PHASE 6 — TESTS E2E ET VALIDATION (Semaine 4-6)
> Objectif : valider en conditions reelles

### 6.1 Tests d'integration [MOYEN]
- [ ] Test : user du tenant A ne peut PAS acceder aux donnees du tenant B
- [ ] Test : login → access token → refresh → switch tenant → logout
- [ ] Test : endpoints admin proteges par authentification admin
- [ ] Test : deconnexion, expiration token, token blackliste

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
- [ ] Remplacer les `window.confirm()` par le composant `ConfirmDialog`
- [ ] Remplacer les `window.open()` par des liens Next.js
- [ ] Ajouter un type TypeScript strict pour chaque reponse admin

### 7.2 Monitoring [FAIBLE]
- [ ] Ajouter un endpoint `/metrics` Prometheus-compatible (optionnel)
- [ ] Monitorer les temps de reponse des endpoints critiques
- [ ] Monitorer la taille de la queue Celery
- [ ] Ajouter des alertes sur les erreurs 5xx en production

### 7.3 Celery [FAIBLE]
- [ ] `reminder_tasks.py` — Deleguer l'envoi d'email via tache email separee
- [ ] `batch_tasks.py` — Ajouter progression visible (statut BDD tous les 100 items)
- [ ] `db/session.py:15` — Separer le statement timeout API (30s) vs Celery (300s)

### 7.4 Securite incrementale [FAIBLE]
- [x] Idempotence Celery deja implementee via cles Redis (sync, reminders, overdue)
- [x] Index composites deja ajoutes sur (tenant_id, status) pour Payment et Facture, (tenant_id, numero) pour Devis/Facture/PayerOrg

---

## SUIVI GLOBAL

| Phase | Description | Taches | Priorite |
|-------|-------------|--------|----------|
| Phase 1 | Bugs post-refactoring | 7 | ELEVE |
| Phase 2 | Accents francais | 9 | MOYEN |
| Phase 3 | Infrastructure production | 11 | ELEVE |
| Phase 4 | Services/pages > 300l | 14 | MOYEN |
| Phase 5 | DB commits dans repos | 4 | MOYEN |
| Phase 6 | Tests E2E et validation | 10 | MOYEN |
| Phase 7 | Ameliorations progressives | 12 | FAIBLE |
| **TOTAL** | | **67** | |

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
