# TODO V3 — OptiFlow AI : Audit Ultra-Pointu & Perfectionnement

> **Contexte** : TODO.md (30 etapes fonctionnelles) et TODO_V2.md (22 etapes qualite) sont terminees.
> Cette V3 corrige TOUT ce qui a ete trouve lors de l'audit exhaustif du 2026-04-04.
> Objectif : zero defaut, zero raccourci, qualite industrielle.
>
> **Meme mode operatoire** : Etape 0, puis une etape a la fois, validation, arret, resume.

---

## ETAPE 0 : Health check [ ]

- [ ] `docker compose up --build -d` — 6 services UP
- [ ] API Swagger repond (http://localhost:8000/docs)
- [ ] Frontend repond (http://localhost:3000)
- [ ] `docker compose exec api pytest -q` — 230 passed
- [ ] `docker compose exec web npx vitest run` — 36 passed
- [ ] Si echec : corriger AVANT de continuer

---

## PHASE 1 : SECURITE CRITIQUE (Etapes 1-3)

### ETAPE 1 : Nettoyage des secrets et fichiers sensibles [x]

> **CRITIQUE** : Le .env est potentiellement dans l'historique git. Des credentials par defaut
> sont hardcodes dans config.py. Des fichiers non-code (PowerPoint, .next/) sont dans le repo.

- [ ] Verifier si `.env` est tracke par git : `git ls-files .env` — si oui, le retirer avec `git rm --cached .env`
- [ ] Verifier que `.gitignore` contient `.env`, `.env.local`, `.env.production`
- [ ] Supprimer le dossier `frontend/.next/` du repo si present : `git rm -r --cached frontend/.next/` et ajouter `frontend/.next/` dans `.gitignore`
- [ ] Deplacer les fichiers non-code hors du repo ou les ajouter dans `.gitignore` :
  - `OptiFlow_AI_Pitch_Deck.pptx`
  - `OptiFlow_AI_Presentation_Technique.pptx`
  - `OptiFlow_AI_Strategie_IA.docx`
- [ ] Supprimer les credentials par defaut dans `core/config.py` : remplacer `jwt_secret: str = "change-me-super-secret"` par `jwt_secret: str` (sans default — force le .env)
- [ ] Ajouter un check au demarrage dans `main.py` : si `settings.jwt_secret == "change-me-super-secret"` en prod, lever une erreur fatale
- [ ] Creer `backend/.dockerignore` : exclure `__pycache__`, `.pytest_cache`, `tests/`, `.git`, `*.pyc`
- [ ] Verifier : `docker compose up --build` demarre sans erreur

---

### ETAPE 2 : Durcissement admin et RBAC [x]

> **Probleme** : `/admin/metrics` expose des stats cross-tenant avec un role admin global.
> `/gdpr/clients/{id}/data` manque de verification de role. Les status codes HTTP sont incorrects sur 8 endpoints.

- [ ] Modifier `admin_health.py:metrics` : ajouter `tenant_ctx = Depends(require_tenant_role("admin"))` et filtrer les metriques par `tenant_id`
- [ ] Modifier `gdpr.py:get_client_data` : ajouter `require_tenant_role("admin", "manager")` au lieu de `get_tenant_context` seul
- [ ] Corriger les status codes HTTP :
  - `action_items.py:PATCH` → retourner 204 au lieu de `{"status": "ok"}`
  - `notifications.py:PATCH /read` → 204
  - `notifications.py:PATCH /read-all` → 204
  - `onboarding.py:POST /first-sync` → 202 Accepted
  - `sync.py:POST /customers, /invoices, /products` → 202 Accepted (operations async)
- [ ] Verifier que `sync.py:GET /erp-types` a bien un `Depends(get_tenant_context)` effectif
- [ ] Tests : verifier que les endpoints admin retournent 403 pour un operator, que les status codes sont corrects

---

### ETAPE 3 : Securite nginx et Docker production [x]

> **Probleme** : nginx manque de headers de securite et de gzip. Les Dockerfiles prod tournent en root.
> Pas de limites de ressources dans docker-compose.prod.yml.

- [ ] Ajouter les security headers dans `nginx/nginx.conf` :
  - `add_header X-Content-Type-Options "nosniff" always;`
  - `add_header X-Frame-Options "DENY" always;`
  - `add_header Referrer-Policy "strict-origin-when-cross-origin" always;`
  - `add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;`
- [ ] Activer gzip dans nginx : `gzip on; gzip_types text/plain text/css application/json application/javascript;`
- [ ] Ajouter `USER appuser` dans `backend/Dockerfile.prod` (creer le user avec `RUN adduser --disabled-password appuser`)
- [ ] Ajouter les limites de ressources dans `docker-compose.prod.yml` :
  - API : `mem_limit: 512m`, `cpus: 1.0`
  - Web : `mem_limit: 256m`, `cpus: 0.5`
  - PostgreSQL : `mem_limit: 1g`
- [ ] Restreindre les ports dans docker-compose.yml dev : PostgreSQL (5432) et Redis (6379) ne doivent PAS etre exposes sur 0.0.0.0 — utiliser `127.0.0.1:5432:5432`
- [ ] Ajouter un pre-deployment backup dans `scripts/deploy.sh` : appeler `backup_db.sh` avant `docker compose up`
- [ ] Verifier : `docker compose -f docker-compose.prod.yml build` passe sans erreur

---

## PHASE 2 : ROBUSTESSE BACKEND (Etapes 4-8)

### ETAPE 4 : Division par zero et edge cases dans les services [x]

> **Probleme** : 12 divisions sans guard dans analytics, scoring, billing. Des listes vides non gerees.

- [ ] `analytics_service.py` : ajouter `if total > 0` avant chaque calcul de taux :
  - `get_financial_kpis` : `taux_recouvrement = round(encaisse / facture * 100, 1) if facture > 0 else 0`
  - `get_commercial_kpis` : `taux_conversion = ... if total_devis > 0 else 0`
  - `get_payer_performance` : `acceptance_rate = ... if total_requested > 0 else 0`
- [ ] `client_360_service.py:71` : `taux = round(total_paye / total_facture * 100, 1) if total_facture > 0 else 0` (deja fait? verifier)
- [ ] `ai_billing_service.py:55` : guard `quota_percent = (total_requests / quota) * 100 if quota > 0 else 0`
- [ ] `collection_prioritizer.py:50` : guard `days / 30` — `max(days, 1)`
- [ ] `renewal_engine.py:30` : guard `(months_since - minimum) / 24` — `max(months_since - minimum, 0) / 24`
- [ ] `dashboard_service.py` : ajouter des null-checks sur les float conversions de montants Payment
- [ ] `devis_service.py` : valider que `lignes` n'est pas vide avant de calculer les totaux
- [ ] `marketing_service.py:send_campaign` : ajouter un check `if not members:` avant la boucle d'envoi
- [ ] Tests : creer `tests/test_edge_cases.py` avec des scenarios limites (0 factures, 0 devis, quotas a 0, listes vides)

---

### ETAPE 5 : Logging contexte et audit trail complets [x]

> **Probleme** : 23 instances de logs sans tenant_id/user_id. 18 operations CRUD sans audit trail.

- [ ] Auditer CHAQUE service et ajouter le contexte dans les logs :
  - Pattern obligatoire : `logger.info("action_name", tenant_id=tenant_id, user_id=user_id, entity_id=entity.id)`
  - Services a corriger : `action_item_service`, `ai_billing_service`, `ai_renewal_copilot`, `ai_service`, `completeness_service`, `consent_service`, `notification_service`, `event_service`
- [ ] Ajouter `audit_service.log_action()` sur les operations manquantes :
  - `action_item_service.update_status()` — audit quand un item est marque done/dismissed
  - `consent_service.upsert_consent()` — audit quand un consentement est modifie (RGPD obligatoire)
  - `notification_service.mark_read()` — pas besoin d'audit (trop verbeux)
  - `marketing_service.send_campaign()` — audit quand une campagne est envoyee
  - `banking_service.auto_reconcile()` — audit du resultat du rapprochement
- [ ] Corriger `ai_service.py` et `ai_renewal_copilot.py` : passer le vrai `user_id` au lieu de 0
- [ ] Verifier : chercher `user_id=0` dans tout le backend — corriger chaque occurrence

---

### ETAPE 6 : Typage et return types exhaustifs [x]

> **Probleme** : 21 fonctions de service sans return type explicite. 13+ endpoints retournent `dict`.

#### Backend services
- [ ] Ajouter les return types manquants sur TOUTES les fonctions publiques des services :
  - `ai_billing_service.py` : `get_usage_summary() -> dict`, `check_quota() -> bool`
  - `analytics_service.py` : typer toutes les fonctions avec les schemas Pydantic
  - `collection_prioritizer.py` : `prioritize_overdue() -> list[OverdueItem]`
  - `completeness_service.py` : `get_completeness() -> CompletenessResponse`
  - `export_service.py` : `export_entity() -> Response`
  - Et tous les autres services signales dans l'audit

#### Backend routers
- [ ] Remplacer les `-> dict` par des schemas Pydantic sur les endpoints critiques :
  - `auth.py:GET /me` → creer `UserMeResponse` schema
  - `ai_usage.py:GET /usage` → creer `AIUsageSummaryResponse` schema
  - `banking.py:POST /import-statement` → creer `ImportResult` schema
  - `sync.py:POST /customers` → creer `SyncResult` schema
  - `gdpr.py:GET /clients/{id}/data` → creer `ClientGDPRDataResponse` schema
  - `onboarding.py:GET /status` → utiliser `OnboardingStatusResponse` existant
- [ ] Verifier : `ruff check app/` passe toujours apres les modifications

---

### ETAPE 7 : Validation business rules manquantes [x]

> **Probleme** : Certaines regles metier critiques ne sont pas validees (montant PEC > demande, devis negatif, etc.)

- [ ] `pec_service.py` : valider que `montant_accorde <= montant_demande` lors du changement de statut
- [ ] `devis_service.py` : valider que le montant TTC est > 0 apres calcul des lignes
- [ ] `facture_service.py` : valider que le montant de la facture correspond au devis
- [ ] `client_service.py:delete_client` : verifier qu'il n'a pas de factures impayees avant suppression (ou soft-delete)
- [ ] `marketing_service.py:send_campaign` : verifier qu'une campagne n'est pas envoyee 2 fois (check `status != "sent"`)
- [ ] `reminder_service.py:execute_plan` : verifier que la liste `channels` n'est pas vide avant `min()`
- [ ] `onboarding_service.py` : valider le format email avant `hash_password()` (utiliser Pydantic EmailStr)
- [ ] Tests : creer `tests/test_business_rules.py` avec des scenarios de validation metier (PEC > demande, double envoi, etc.)

---

### ETAPE 8 : Fonctions trop longues et code duplique [x]

> **Probleme** : 8 fonctions depassent 50 lignes. sync_service.py est un doublon de erp_sync_service.py.

- [ ] Refactorer `ai_service.py:_build_case_context()` (88 lignes) : extraire en sous-fonctions `_build_financial_context()`, `_build_document_context()`, `_build_pec_context()`
- [ ] Refactorer `marketing_service.py:send_campaign()` (62 lignes) : extraire `_resolve_recipients()`, `_render_template()`, `_send_to_recipient()`
- [ ] Refactorer `reminder_service.py:execute_plan()` (62 lignes) : extraire `_should_create_reminder()`, `_render_reminder_content()`
- [ ] Supprimer `sync_service.py` (0% couverture, remplace par `erp_sync_service.py`) — verifier qu'aucun import ne le reference
- [ ] Verifier : aucune fonction > 50 lignes restante (grep pour les fonctions longues)
- [ ] Tests : tous les tests passent apres refactoring

---

## PHASE 3 : SOLIDIFICATION FRONTEND (Etapes 9-12)

### ETAPE 9 : Migration SWR sur toutes les pages de liste [x]

> **Probleme** : `devis/page.tsx` et `factures/page.tsx` utilisent encore l'ancien pattern `useEffect + fetchJson`.
> Les pages detail utilisent aussi l'ancien pattern.

- [ ] Migrer `devis/page.tsx` : remplacer `useEffect + fetchJson` par `useDevisList()` de `use-api.ts`
- [ ] Migrer `factures/page.tsx` : remplacer par `useFactures()` de `use-api.ts`
- [ ] Migrer `pec/page.tsx` : remplacer par `usePecRequests()` de `use-api.ts`
- [ ] Migrer `actions/page.tsx` : remplacer par `useActionItems()` de `use-api.ts`
- [ ] Migrer `relances/page.tsx` : remplacer le fetchJson par un hook SWR
- [ ] Migrer `marketing/page.tsx` : remplacer par un hook SWR
- [ ] Migrer `renewals/page.tsx` : remplacer par un hook SWR
- [ ] Migrer `dashboard/page.tsx` : remplacer le `Promise.all + fetchJson` par des hooks SWR combines
- [ ] Migrer `clients/[id]/page.tsx` : remplacer par `useClient360()` de `use-api.ts`
- [ ] Migrer `cases/[id]/page.tsx` : remplacer par `useCase()` de `use-api.ts`
- [ ] Objectif : ZERO `useEffect + fetchJson` dans les pages (seulement dans les formulaires pour les mutations)
- [ ] Verifier : `npx tsc --noEmit` passe, toutes les pages fonctionnent

---

### ETAPE 10 : Refactorer les formulaires restants avec React Hook Form + Zod [x]

> **Probleme** : 7 formulaires utilisent encore du state React brut.

- [ ] Migrer `devis/new/page.tsx` : utiliser `useForm()` + `devisCreateSchema`
- [ ] Migrer `onboarding/page.tsx` : utiliser `useForm()` + `signupSchema` et `cosiumConnectSchema` pour chaque etape
- [ ] Migrer `marketing/page.tsx` : formulaires segment et campagne avec `useForm()` + schemas
- [ ] Migrer `relances/plans/page.tsx` : formulaire plan de relance
- [ ] Migrer `relances/templates/page.tsx` : formulaire template
- [ ] Migrer `paiements/page.tsx` : formulaire paiement
- [ ] Migrer `clients/[id]/page.tsx` : formulaire d'edition inline (si present)
- [ ] Verifier : chaque formulaire valide en temps reel, erreurs sous le champ, bouton desactive si invalide

---

### ETAPE 11 : ConfirmDialog sur les actions destructives manquantes [x]

> **Probleme** : Les changements de statut irreversibles (annuler un devis, refuser une PEC) n'ont pas de ConfirmDialog.

- [ ] `devis/[id]/page.tsx` : ajouter ConfirmDialog quand on passe un devis en statut "annule"
- [ ] `pec/[id]/page.tsx` : ajouter ConfirmDialog quand on refuse une PEC (statut "refusee")
- [ ] `relances/page.tsx` : ajouter ConfirmDialog avant d'executer un plan de relance (envoi d'emails)
- [ ] `marketing/page.tsx` : ajouter ConfirmDialog avant d'envoyer une campagne
- [ ] `admin/page.tsx` : ajouter ConfirmDialog avant de lancer une synchro (operation longue)
- [ ] Verifier : chaque action destructive/irreversible a une modale de confirmation

---

### ETAPE 12 : next.config.ts et optimisations production [x]

> **Probleme** : next.config.ts est vide. Pas d'optimisations pour la production.

- [ ] Configurer `next.config.ts` :
  ```ts
  const config = {
    output: "standalone",       // Optimise pour Docker
    poweredByHeader: false,     // Masque le header X-Powered-By
    reactStrictMode: true,      // Active le mode strict React
    compress: true,             // Active la compression gzip
  };
  ```
- [ ] Ajouter les security headers dans next.config.ts :
  ```ts
  headers: async () => [{
    source: "/:path*",
    headers: [
      { key: "X-Frame-Options", value: "DENY" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    ],
  }]
  ```
- [ ] Verifier le build production : `docker compose exec web npx next build` — aucune erreur, taille bundle raisonnable
- [ ] Verifier que le mode standalone fonctionne dans Docker

---

## PHASE 4 : TESTS EXHAUSTIFS (Etapes 13-16)

### ETAPE 13 : Tests edge cases et business rules backend [x]

> **Probleme** : Les tests existants couvrent le happy path. Manquent les edge cases et regles metier.

- [ ] `tests/test_edge_cases.py` : 
  - Dashboard avec 0 factures, 0 devis, 0 paiements → pas de division par zero
  - Analytics avec un seul tenant sans donnees → retourne des zeros propres
  - PEC avec montant_accorde > montant_demande → erreur 400
  - Devis avec lignes vides → erreur 422
  - Client avec email invalide → erreur 422
  - Campagne envoyee 2 fois → erreur 400
  - Quota IA a 0 → retourne 0% sans crash
- [ ] `tests/test_business_rules.py` :
  - Workflow devis : brouillon → signe OK, signe → brouillon INTERDIT
  - Workflow PEC : soumise → acceptee OK, acceptee → soumise INTERDIT
  - Paiement : montant_paid > montant_due → erreur
  - Facture : generer depuis un devis non signe → erreur
  - Client : supprimer un client avec factures impayees → erreur
- [ ] `tests/test_tenant_security.py` (enrichir) :
  - Creer 3 tenants, verifier l'isolation sur CHAQUE entite (clients, cases, devis, factures, paiements, PEC)
  - Tenter d'acceder a une entite d'un autre tenant par ID direct → 404
  - Admin global ne voit PAS les donnees d'un autre tenant
- [ ] Objectif : couverture > 85%

---

### ETAPE 14 : Tests frontend complementaires [x]

> **Probleme** : 36 tests sur les composants basiques. Manquent les tests de hooks, pages et interactions.

- [ ] Tests des schemas Zod :
  - `tests/lib/schemas.test.ts` : chaque schema rejette les donnees invalides (email mauvais, string vide, montant negatif)
- [ ] Tests des hooks SWR :
  - `tests/hooks/use-api.test.ts` : mock de fetch, verifier que les hooks retournent data/error/isLoading correctement
- [ ] Tests de composants complexes :
  - `tests/components/DataTable.test.tsx` : rendu avec donnees, pagination, etat vide, etat erreur
  - `tests/components/ConfirmDialog.test.tsx` : ouverture, fermeture Escape, clic backdrop, confirmation
  - `tests/components/SearchInput.test.tsx` : debounce, clear
- [ ] Objectif : 60+ tests frontend, couverture > 70% sur composants et utilitaires

---

### ETAPE 15 : Test de regression complet [x]

> Apres toutes les corrections, verifier que RIEN n'est casse.

- [ ] Backend : `pytest -v --cov=app --cov-report=term-missing` — 100% pass, couverture > 85%
- [ ] Frontend : `npx vitest run` — 100% pass
- [ ] Lint backend : `ruff check app/ && ruff format --check app/` — 0 erreur
- [ ] Lint frontend : `npx tsc --noEmit && npx prettier --check "src/**/*.{ts,tsx}"` — 0 erreur
- [ ] Build production : `docker compose -f docker-compose.prod.yml build` — success
- [ ] E2E : les 2 tests e2e (workflow pro + isolation tenant) passent
- [ ] API : tous les endpoints repondent correctement via Swagger

---

### ETAPE 16 : Documentation des decisions d'architecture [x]

> **Probleme** : Pourquoi user_repo n'a pas de tenant_id? Pourquoi certains endpoints sont publics?
> Les futures developpeurs ne comprendront pas sans documentation.

- [ ] Ajouter un fichier `docs/ARCHITECTURE_DECISIONS.md` documentant :
  - Pourquoi `user_repo` n'a pas de tenant_id filter (auth layer, un user peut avoir plusieurs tenants)
  - Pourquoi `/admin/health` est public (load balancer)
  - Pourquoi `/billing/webhook` n'a pas d'auth (Stripe signature validation)
  - Pourquoi `sync_service.py` existe encore a cote de `erp_sync_service.py` (legacy, a supprimer)
  - Pourquoi les cookies sont httpOnly + header fallback (retrocompatibilite Swagger)
  - Pourquoi les status transitions sont hardcodees (VALID_TRANSITIONS) et pas en BDD
- [ ] Ajouter des commentaires dans `conftest.py` expliquant chaque fixture
- [ ] Mettre a jour `CONTRIBUTING.md` avec les patterns d'erreur et de test

---

## PHASE 5 : POLISH FINAL (Etapes 17-18)

### ETAPE 17 : Recherche globale fonctionnelle [x]

> **Probleme** : La barre de recherche dans le Header est un placeholder. Elle ne fait rien.

- [ ] Backend : creer `services/search_service.py` avec `global_search(db, tenant_id, query, limit=10)` qui cherche dans :
  - Clients (nom, prenom, email, telephone)
  - Dossiers (ID, nom client)
  - Factures (numero)
  - Devis (numero)
- [ ] Backend : creer `api/routers/search.py` : `GET /api/v1/search?q=...` retourne les resultats groupes par type
- [ ] Frontend : modifier `Header.tsx` pour appeler l'endpoint `/search` et afficher un dropdown de resultats avec navigation
- [ ] Tests : recherche "Dupont" retourne clients et dossiers, recherche "F-2026" retourne factures

---

### ETAPE 18 : Generation PDF devis/factures [x]

> **Probleme** : Aucun moyen de generer un PDF de devis ou facture. C'est indispensable pour un opticien.

- [ ] Backend : ajouter `weasyprint` ou `reportlab` dans `requirements.txt`
- [ ] Backend : creer `services/pdf_service.py` avec `generate_devis_pdf(db, devis_id, tenant_id) -> bytes` et `generate_facture_pdf(db, facture_id, tenant_id) -> bytes`
- [ ] Template HTML/CSS pour le PDF : en-tete magasin, lignes du devis/facture, montants, conditions
- [ ] Backend : creer les endpoints `GET /api/v1/devis/{id}/pdf` et `GET /api/v1/factures/{id}/pdf` qui retournent le PDF
- [ ] Frontend : ajouter un bouton "Telecharger PDF" sur les pages detail devis et facture
- [ ] Tests : generer un PDF, verifier qu'il n'est pas vide et contient le bon numero

---

## Checkpoints

### Apres PHASE 1 (Etapes 1-3) — Securite resolue :
- [ ] Zero secret hardcode, .env hors du repo, nginx securise, Docker non-root

### Apres PHASE 2 (Etapes 4-8) — Backend robuste :
- [ ] Zero division par zero, logs complets, types exhaustifs, regles metier validees, zero doublon

### Apres PHASE 3 (Etapes 9-12) — Frontend uniforme :
- [ ] 100% pages en SWR, 100% formulaires en RHF+Zod, confirmations partout, next.config optimise

### Apres PHASE 4 (Etapes 13-16) — Tests exhaustifs :
- [ ] Couverture backend > 85%, frontend > 70%, edge cases couverts, decisions documentees

### Apres PHASE 5 (Etapes 17-18) — Fonctionnalites indispensables :
- [ ] Recherche globale fonctionnelle, PDF devis/factures generables
