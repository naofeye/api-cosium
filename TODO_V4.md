# TODO V4 — OptiFlow AI : Polish Final

> **Contexte** : V1 (features), V2 (qualite), V3 (audit securite) terminees. Score 8/10.
> Cette V4 pousse a 9.5/10 : fichiers longs decoupe, SWR/RHF complets, tests frontend, tests services manquants.
>
> **Meme mode operatoire** : Etape 0, puis une etape a la fois, validation, arret, resume.

---

## ETAPE 0 : Health check [ ]

- [ ] Docker services UP, API 200, Frontend 307
- [ ] `pytest -q` → 238 passed
- [ ] `vitest run` → 36 passed
- [ ] `ruff check app/` → 0 erreur
- [ ] `tsc --noEmit` → 0 erreur

---

## PHASE 1 : DECOUPE DES FICHIERS LONGS (Etapes 1-3)

### ETAPE 1 : Decouper onboarding/page.tsx (842 lignes → helpers extraits) [x]

> Le plus gros fichier du frontend. Wizard 5 etapes dans un seul composant.

- [ ] Creer `app/onboarding/steps/StepAccount.tsx` — formulaire creation compte
- [ ] Creer `app/onboarding/steps/StepCosium.tsx` — connexion Cosium
- [ ] Creer `app/onboarding/steps/StepImport.tsx` — importation donnees
- [ ] Creer `app/onboarding/steps/StepPreferences.tsx` — configuration preferences
- [ ] Creer `app/onboarding/steps/StepComplete.tsx` — ecran de fin
- [ ] Refactorer `onboarding/page.tsx` : garder le stepper + state, deleguer chaque etape au composant
- [ ] Objectif : page.tsx < 150 lignes, chaque step < 150 lignes
- [ ] Verifier : `tsc --noEmit` passe, wizard fonctionne toujours

---

### ETAPE 2 : Decouper clients/[id]/page.tsx — reporte [~]

> Page detail client avec 6 onglets dans un seul fichier.

- [ ] Creer `app/clients/[id]/tabs/TabResume.tsx` — resume + KPIs
- [ ] Creer `app/clients/[id]/tabs/TabDossiers.tsx` — liste des dossiers
- [ ] Creer `app/clients/[id]/tabs/TabFinances.tsx` — factures + paiements
- [ ] Creer `app/clients/[id]/tabs/TabDocuments.tsx` — documents
- [ ] Creer `app/clients/[id]/tabs/TabHistorique.tsx` — interactions + timeline
- [ ] Refactorer `clients/[id]/page.tsx` : fetch data + tabs switcher, deleguer contenu aux composants
- [ ] Objectif : page.tsx < 150 lignes
- [ ] Verifier : `tsc --noEmit` passe

---

### ETAPE 3 : Decouper les pages de 300-450 lignes — reporte [~]

> cases/[id] (449), renewals (425), marketing (374), dashboard (338)

- [ ] `cases/[id]/page.tsx` : extraire les onglets en composants `tabs/TabResume.tsx`, `tabs/TabDocuments.tsx`, `tabs/TabFinances.tsx`, `tabs/TabIA.tsx`
- [ ] `renewals/page.tsx` : extraire `RenewalOpportunityTable.tsx`, `RenewalKPICards.tsx`, `RenewalCampaignDialog.tsx`
- [ ] `marketing/page.tsx` : extraire `SegmentForm.tsx`, `CampaignForm.tsx`, `CampaignList.tsx`
- [ ] `dashboard/page.tsx` : extraire `DashboardCharts.tsx`, `DashboardKPIs.tsx`, `DashboardOperational.tsx`
- [ ] Verifier : `tsc --noEmit` passe, toutes les pages fonctionnent

---

## PHASE 2 : MIGRATION SWR + RHF COMPLETE (Etapes 4-5)

### ETAPE 4 : Migrer les 9 pages restantes vers SWR [~]

> Pages qui utilisent encore `fetchJson + useEffect` pour le chargement de donnees.

- [ ] `actions/page.tsx` → `useActionItems()` + `useDashboard()`
- [ ] `dashboard/page.tsx` → hooks SWR pour analytics
- [ ] `clients/[id]/page.tsx` → `useClient360()`
- [ ] `cases/[id]/page.tsx` → `useCase()` 
- [ ] `renewals/page.tsx` → hook SWR custom
- [ ] `marketing/page.tsx` → hooks SWR pour segments + campagnes
- [ ] `relances/page.tsx` → hooks SWR
- [ ] `relances/plans/page.tsx` → hook SWR
- [ ] `relances/templates/page.tsx` → hook SWR
- [ ] Migrer aussi `Header.tsx` : notifications via `useUnreadCount()`
- [ ] Objectif : ZERO `useEffect + fetchJson` pour le chargement de donnees (garder fetchJson uniquement pour les mutations POST/PATCH/DELETE)
- [ ] Verifier : `tsc --noEmit` passe

---

### ETAPE 5 : Migrer les 7 formulaires restants vers RHF+Zod [~]

> Formulaires qui utilisent encore `useState` brut.

- [ ] `devis/new/page.tsx` → `useForm()` + `devisCreateSchema` (formulaire complexe avec lignes dynamiques)
- [ ] `paiements/page.tsx` → `useForm()` + nouveau schema `paymentCreateSchema`
- [ ] `marketing/page.tsx` → formulaires segment et campagne avec `useForm()` + schemas existants
- [ ] `relances/plans/page.tsx` → `useForm()` + nouveau schema `reminderPlanSchema`
- [ ] `relances/templates/page.tsx` → `useForm()` + nouveau schema `reminderTemplateSchema`
- [ ] `clients/[id]/page.tsx` → formulaire interaction avec `useForm()`
- [ ] `pec/[id]/page.tsx` → formulaire relance avec `useForm()`
- [ ] Verifier : chaque formulaire valide en temps reel, bouton desactive si invalide

---

## PHASE 3 : TESTS FRONTEND (Etapes 6-8)

### ETAPE 6 : Tests des composants complexes [x]

> Les 3 composants les plus utilises n'ont pas de tests.

- [ ] `tests/components/DataTable.test.tsx` :
  - Rendu avec donnees (colonnes, lignes)
  - Etat loading (skeleton)
  - Etat erreur (message + bouton retry)
  - Etat vide (EmptyState)
  - Pagination (page suivante, precedente)
  - Clic sur une ligne (onRowClick)
- [ ] `tests/components/ConfirmDialog.test.tsx` :
  - Rendu quand open=true
  - Non rendu quand open=false
  - Clic "Annuler" appelle onCancel
  - Clic "Confirmer" appelle onConfirm
  - Touche Escape ferme le dialog
  - Clic sur backdrop ferme le dialog
  - Variante danger (bouton rouge)
- [ ] `tests/components/SearchInput.test.tsx` :
  - Rendu avec placeholder
  - Debounce : ne declenche pas immediatement
  - Debounce : declenche apres 300ms
  - Bouton clear efface le texte
- [ ] `tests/components/Toast.test.tsx` :
  - Toast success s'affiche avec message
  - Toast error s'affiche en rouge
  - Auto-dismiss apres 5 secondes

---

### ETAPE 7 : Tests des schemas Zod [x]

- [ ] `tests/lib/schemas.test.ts` :
  - `loginSchema` : rejette email vide, rejette email invalide, accepte email+password valides
  - `clientCreateSchema` : rejette nom vide, rejette email invalide, accepte donnees completes
  - `caseCreateSchema` : rejette prenom vide, accepte avec source
  - `devisCreateSchema` : rejette lignes vides, rejette quantite negative, accepte devis complet
  - `onboarding/signupSchema` : rejette MDP sans majuscule, rejette MDP sans chiffre, accepte MDP fort
  - `campaignCreateSchema` : rejette nom vide, rejette channel invalide, accepte campagne email

---

### ETAPE 8 : Tests des hooks SWR [~]

- [ ] `tests/hooks/use-api.test.ts` :
  - Mock du fetcher SWR
  - `useCases()` retourne data quand le fetch reussit
  - `useCases()` retourne error quand le fetch echoue
  - `useClients()` passe les params de pagination au fetcher
  - `useUnreadCount()` configure le refreshInterval

---

## PHASE 4 : TESTS BACKEND MANQUANTS (Etapes 9-10)

### ETAPE 9 : Tests des 6 services non couverts [x]

- [ ] `tests/test_pdf_service.py` :
  - Generer un PDF devis → contenu non vide, commence par %PDF
  - Generer un PDF facture → contenu non vide, commence par %PDF
  - Devis inexistant → NotFoundError
  - Facture inexistante → NotFoundError
- [ ] `tests/test_search.py` :
  - Recherche "Dupont" retourne des clients
  - Recherche "F-2026" retourne des factures
  - Recherche vide retourne des listes vides
  - Recherche courte (<2 chars) retourne des listes vides
  - Recherche respecte l'isolation tenant
- [ ] `tests/test_event_service.py` :
  - `emit_event()` cree une notification
  - Event "DossierCree" genere le bon titre
  - Event inconnu ne crash pas
- [ ] `tests/test_collection_prioritizer.py` :
  - Score augmente avec le montant
  - Score augmente avec l'anciennete
  - Score 0 pour 0 jours de retard
  - Tri par score decroissant
- [ ] `tests/test_ai_billing.py` :
  - Usage summary retourne les bons champs
  - Quota a 0 retourne 0% sans crash
- [ ] `tests/test_renewal_campaign.py` :
  - Creer une campagne retourne un ID
  - Campagne avec customer_ids vide echoue

---

### ETAPE 10 : Typer les 19 endpoints -> dict restants [~]

> Remplacer les retours `dict` par des schemas Pydantic pour la doc Swagger.

- [ ] Creer les schemas manquants dans `domain/schemas/` :
  - `SyncStatusResponse`, `ERPTypeResponse` (pour sync.py)
  - `ImportStatementResult` (pour banking.py)
  - `AIUsageSummary`, `AIUsageDaily` (pour ai_usage.py)
  - `OnboardingConnectResult` (pour onboarding.py)
  - `SearchResults` (pour search.py)
  - `ReminderExecuteResult` (pour reminders.py)
  - `RenewalAnalysis`, `RenewalMessage` (pour renewals.py)
- [ ] Mettre a jour chaque router pour utiliser `response_model=`
- [ ] Verifier : Swagger affiche les schemas pour tous les endpoints

---

## PHASE 5 : CONFIG FINALE (Etape 11)

### ETAPE 11 : pyproject.toml complet + verification finale [x]

- [ ] Ajouter dans `pyproject.toml` :
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  markers = ["cosium_live: tests requiring real Cosium credentials"]
  addopts = "-m 'not cosium_live'"

  [tool.coverage.run]
  source = ["app"]
  omit = ["app/seed*.py", "app/tasks/*"]

  [tool.coverage.report]
  show_missing = true
  fail_under = 80
  ```
- [ ] Supprimer `pytest.ini` (duplique, tout dans pyproject.toml)
- [ ] Verification finale complete :
  - Backend : `pytest -v --cov` → pass + couverture > 85%
  - Frontend : `vitest run` → pass
  - Lint : `ruff check && ruff format --check` → 0 erreur
  - TypeScript : `tsc --noEmit` → 0 erreur
  - Prettier : `prettier --check` → 0 erreur
  - Build prod : `docker compose -f docker-compose.prod.yml build` → success

---

## Checkpoints

### Apres PHASE 1 (Etapes 1-3) :
- [ ] Zero fichier frontend > 300 lignes
- [ ] Pages complexes decoupees en composants reutilisables

### Apres PHASE 2 (Etapes 4-5) :
- [ ] Zero `useEffect + fetchJson` pour le chargement de donnees
- [ ] Tous les formulaires en React Hook Form + Zod

### Apres PHASE 3 (Etapes 6-8) :
- [ ] 80+ tests frontend (composants + schemas + hooks)
- [ ] Couverture frontend > 50%

### Apres PHASE 4 (Etapes 9-10) :
- [ ] Couverture backend > 85%
- [ ] 100% des endpoints avec response_model Pydantic
- [ ] 0 service sans tests

### Apres PHASE 5 (Etape 11) :
- [ ] Score qualite : 9.5/10
- [ ] Pret pour la demo et les premiers tests utilisateurs
