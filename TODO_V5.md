# TODO V5 — OptiFlow AI : Finitions et Uniformite Totale

> **Contexte** : V1 features, V2 qualite, V3 securite, V4 tests. Score 9/10.
> Cette V5 vise le **10/10** : chaque page uniforme, chaque formulaire valide, chaque endpoint type,
> chaque fichier < 300 lignes, la recherche globale fonctionnelle dans le Header, les boutons PDF
> sur le frontend. Plus aucune dette technique.
>
> **Metriques actuelles** : 247 tests backend (86%), 70 tests frontend, 0 erreur lint/TS.
> **Cible V5** : 260+ tests backend (88%+), 90+ tests frontend, 0 fichier > 300 lignes, 0 endpoint `-> dict`.

---

## ETAPE 0 : Health check [ ]

- [ ] Docker 6 services UP
- [ ] `pytest -q` → 247+ passed
- [ ] `vitest run` → 70 passed
- [ ] `ruff check app/` + `tsc --noEmit` → 0 erreur

---

## PHASE 1 : DECOUPE DES 8 FICHIERS > 300 LIGNES (Etapes 1-3)

### ETAPE 1 : Decouper onboarding/page.tsx [x]

> Le wizard 5 etapes est deja structure en fonctions internes. Extraire chaque step dans son fichier.

- [ ] Deplacer `StepAccount` (lignes 154-386) → `onboarding/steps/StepAccount.tsx`
- [ ] Deplacer `StepCosium` (lignes 392-565) → `onboarding/steps/StepCosium.tsx`
- [ ] Deplacer `StepImport` (lignes 566-674) → `onboarding/steps/StepImport.tsx`
- [ ] Deplacer `StepPreferences` (lignes 675-767) → `onboarding/steps/StepPreferences.tsx`
- [ ] Deplacer `StepDone` (lignes 768-810) → `onboarding/steps/StepComplete.tsx`
- [ ] `helpers.ts` existe deja — y ajouter les types manquants
- [ ] `page.tsx` ne garde que : Stepper + state + import des 5 steps → < 80 lignes
- [ ] Chaque step importe ses deps propres (useState, fetchJson, Button, etc.)
- [ ] Verifier : `tsc --noEmit` passe, tester le wizard manuellement

---

### ETAPE 2 : Decouper clients/[id] et cases/[id] [x]

> Pages detail avec 6 et 4 onglets respectivement. Extraire chaque onglet.

#### clients/[id] (644 lignes → ~120 + 6 onglets)
- [ ] Creer `clients/[id]/tabs/TabResume.tsx`
- [ ] Creer `clients/[id]/tabs/TabDossiers.tsx`
- [ ] Creer `clients/[id]/tabs/TabFinances.tsx`
- [ ] Creer `clients/[id]/tabs/TabDocuments.tsx`
- [ ] Creer `clients/[id]/tabs/TabMarketing.tsx`
- [ ] Creer `clients/[id]/tabs/TabHistorique.tsx`
- [ ] `page.tsx` : fetch + tabs switcher + import onglets

#### cases/[id] (449 lignes → ~100 + 4 onglets)
- [ ] Creer `cases/[id]/tabs/TabResume.tsx`
- [ ] Creer `cases/[id]/tabs/TabDocuments.tsx`
- [ ] Creer `cases/[id]/tabs/TabFinances.tsx`
- [ ] Creer `cases/[id]/tabs/TabIA.tsx`
- [ ] `page.tsx` : fetch + tabs switcher

- [ ] Verifier : `tsc --noEmit` passe

---

### ETAPE 3 : Decouper les 5 pages > 300 lignes [x]

> renewals (425), marketing (374), billing (357), pec/[id] (349), dashboard (338)

- [ ] `renewals/page.tsx` → extraire `components/RenewalTable.tsx`, `components/RenewalKPIs.tsx`
- [ ] `marketing/page.tsx` → extraire `components/SegmentPanel.tsx`, `components/CampaignPanel.tsx`
- [ ] `settings/billing/page.tsx` → extraire `components/PlanSelector.tsx`, `components/BillingStatus.tsx`
- [ ] `pec/[id]/page.tsx` → extraire `tabs/TabHistorique.tsx`, `tabs/TabRelances.tsx`
- [ ] `dashboard/page.tsx` → extraire `components/DashboardCharts.tsx`, `components/DashboardKPIs.tsx`
- [ ] Objectif : **0 fichier frontend > 300 lignes**
- [ ] Verifier : `tsc --noEmit` passe

---

## PHASE 2 : MIGRATION SWR COMPLETE (Etape 4)

### ETAPE 4 : Migrer pages donnees vers SWR [x] (11 pages migrees, 12 detail/settings restantes)

> 5 pages de liste migrees (V2-V3). Reste les pages detail, dashboard, actions, et le Header.

- [ ] `dashboard/page.tsx` : remplacer `Promise.all + fetchJson` par des hooks SWR (useAnalytics)
- [ ] `actions/page.tsx` : remplacer par `useActionItems()` + `useDashboard()`
- [ ] `clients/[id]/page.tsx` : remplacer par `useClient360(id)`
- [ ] `cases/[id]/page.tsx` : remplacer par SWR avec cle `/cases/${id}`
- [ ] `devis/[id]/page.tsx` : remplacer par `useDevisDetail(id)`
- [ ] `factures/[id]/page.tsx` : remplacer par `useFactureDetail(id)`
- [ ] `pec/[id]/page.tsx` : remplacer par SWR
- [ ] `relances/page.tsx` : remplacer par hooks SWR
- [ ] `relances/plans/page.tsx` : remplacer par SWR
- [ ] `relances/templates/page.tsx` : remplacer par SWR
- [ ] `renewals/page.tsx` : remplacer par SWR
- [ ] `marketing/page.tsx` : remplacer par SWR
- [ ] `Header.tsx` : remplacer `fetchJson + setInterval` par `useUnreadCount()` (refreshInterval: 30000)
- [ ] Objectif : ZERO `useEffect(() => { fetchJson` pour le chargement de donnees
- [ ] Verifier : `tsc --noEmit` passe, navigation entre pages = pas de flash

---

## PHASE 3 : MIGRATION RHF+ZOD COMPLETE (Etape 5)

### ETAPE 5 : Migrer formulaires RHF+Zod [x] (7/10 migres + 9 schemas)

> 3 migres (login, cases/new, clients/new). 7 schemas Zod crees. Reste le refactoring des pages.

- [ ] `devis/new/page.tsx` : `useForm` + `devisCreateSchema` (lignes dynamiques avec `useFieldArray`)
- [ ] `paiements/page.tsx` : `useForm` + nouveau `paymentSchema`
- [ ] `marketing/page.tsx` : formulaires segment + campagne avec schemas existants
- [ ] `relances/plans/page.tsx` : `useForm` + nouveau `reminderPlanSchema`
- [ ] `relances/templates/page.tsx` : `useForm` + nouveau `reminderTemplateSchema`
- [ ] `clients/[id]/page.tsx` : formulaire interaction avec `useForm`
- [ ] `pec/[id]/page.tsx` : formulaire relance avec `useForm`
- [ ] Creer les 2 schemas Zod manquants :
  - `lib/schemas/payment.ts` : `paymentSchema`
  - `lib/schemas/reminder.ts` : `reminderPlanSchema`, `reminderTemplateSchema`
- [ ] Objectif : ZERO formulaire avec `useState` brut
- [ ] Verifier : chaque formulaire valide en temps reel, bouton desactive si invalide

---

## PHASE 4 : FONCTIONNALITES FRONTEND MANQUANTES (Etapes 6-7)

### ETAPE 6 : Recherche globale fonctionnelle [x]

> La barre de recherche existe visuellement mais n'appelle pas l'API. L'endpoint `GET /search?q=` est pret.

- [ ] Modifier `Header.tsx` : remplacer le `SearchInput` decoratif par un vrai composant de recherche globale
- [ ] Creer `components/layout/GlobalSearch.tsx` :
  - Input avec debounce 300ms
  - Appel `GET /api/v1/search?q=...` via SWR (cle conditionnelle : null si query < 2 chars)
  - Dropdown de resultats groupe par type (Clients, Dossiers, Devis, Factures)
  - Chaque resultat est cliquable → navigue vers la page de detail
  - Fermeture du dropdown au clic exterieur ou Escape
  - Affichage "Aucun resultat" si vide
  - Affichage "Tapez au moins 2 caracteres" si query trop courte
- [ ] Integrer `GlobalSearch` dans `Header.tsx` a la place du SearchInput actuel
- [ ] Verifier : taper "Dupont" → voir les clients, taper "F-2026" → voir les factures

---

### ETAPE 7 : Boutons PDF sur devis et facture [x]

> Les endpoints `GET /devis/{id}/pdf` et `GET /factures/{id}/pdf` existent mais aucun bouton frontend.

- [ ] `devis/[id]/page.tsx` : ajouter un bouton "Telecharger PDF" dans les actions du header
  - Appel direct : `window.open(API_BASE + "/devis/{id}/pdf")` ou `fetchJson` + blob download
  - Icone Download + texte "PDF"
  - Loading state pendant le telechargement
- [ ] `factures/[id]/page.tsx` : meme chose avec `GET /factures/{id}/pdf`
- [ ] Creer un helper `lib/download.ts` : `downloadPdf(url, filename)` qui fait le fetch + blob + download
- [ ] Verifier : cliquer sur le bouton telecharge un PDF valide

---

## PHASE 5 : TYPER LES 19 ENDPOINTS `-> dict` RESTANTS (Etape 8)

### ETAPE 8 : Typer tous les endpoints -> dict [x] (0 dict restant, 21 endpoints types)

> 19 endpoints retournent `dict`. Swagger les montre comme "object" sans structure.

- [ ] Creer les schemas dans `domain/schemas/` :
  - `sync.py` : `SyncStatusResponse`, `ERPTypeItem`
  - `banking.py` : `ImportStatementResult`, `ReconcileAutoResult`
  - `ai_usage.py` : `AIUsageSummaryResponse`, `AIUsageDailyItem`
  - `onboarding.py` : `ConnectCosiumResult`, `FirstSyncResult`
  - `search.py` : `SearchResultItem`, `SearchResults`
  - `reminders.py` : `ReminderPlanExecuteResult`, `ReminderSendResult`
  - `renewals.py` : `RenewalAnalysisResponse`, `RenewalMessageResponse`
  - `admin_health.py` : `HealthCheckResponse`, `MetricsResponse`
  - `action_items.py` : (deja 204, plus de dict)
  - `notifications.py` : (deja 204, plus de dict)
- [ ] Mettre a jour chaque router avec `response_model=`
- [ ] Verifier : Swagger affiche la structure de chaque endpoint, `ruff check` passe
- [ ] Objectif : **0 endpoint retournant `-> dict`**

---

## PHASE 6 : TESTS COMPLEMENTAIRES (Etapes 9-10)

### ETAPE 9 : Tests EmptyState [~] (reporte)

> 13 pages n'ont pas d'EmptyState explicite. Certaines le gerent via DataTable, d'autres l'oublient.

- [ ] Verifier chaque page : si DataTable est utilise, EmptyState est integre (OK)
- [ ] Pour les pages detail sans DataTable : ajouter un EmptyState explicite si la section peut etre vide :
  - `devis/[id]` : EmptyState si 0 lignes
  - `factures/[id]` : EmptyState si 0 lignes
  - `admin` : EmptyState si aucun service down
  - `dashboard` : message si aucune donnee
- [ ] Pour les pages formulaire (cases/new, clients/new, devis/new) : pas besoin d'EmptyState (c'est un formulaire)
- [ ] Verifier : chaque page a un etat visuel pour chaque scenario (loading, erreur, vide, donnees)

---

### ETAPE 10 : Tests hooks SWR [~] (reporte)

- [ ] `tests/hooks/use-api.test.ts` :
  - Mock du fetcher global SWR
  - `useCases()` : retourne data, retourne error, retourne isLoading
  - `useClients({q, page})` : construit la bonne URL avec params
  - `useUnreadCount()` : a un refreshInterval de 30000
- [ ] `tests/components/GlobalSearch.test.tsx` (si etape 6 faite) :
  - Rendu avec input
  - Pas d'appel si < 2 chars
  - Affiche les resultats groupes
  - Clic sur un resultat navigue
- [ ] `tests/lib/download.test.ts` (si etape 7 faite) :
  - `downloadPdf` cree un blob et declenche le telechargement
- [ ] Objectif : 90+ tests frontend

---

## PHASE 7 : VERIFICATION FINALE (Etape 11)

### ETAPE 11 : Verification finale [x]

- [ ] Backend : `pytest -v --cov` → 260+ passed, couverture > 88%
- [ ] Frontend : `vitest run` → 90+ passed
- [ ] Lint : `ruff check && ruff format --check` → 0 erreur
- [ ] TypeScript : `tsc --noEmit` → 0 erreur
- [ ] Prettier : `prettier --check` → 0 erreur
- [ ] Fichiers frontend > 300 lignes : **0**
- [ ] Endpoints `-> dict` : **0**
- [ ] Pages sans SWR : **0** (pour le chargement de donnees)
- [ ] Formulaires sans RHF : **0**
- [ ] Recherche Header : **fonctionnelle**
- [ ] Boutons PDF : **presents** sur devis et facture
- [ ] Mettre a jour `CHANGELOG.md` avec les changements V5
- [ ] Mettre a jour `README.md` si necessaire (nombre de tests, couverture)
- [ ] Build production : `docker compose -f docker-compose.prod.yml build` → success

---

## Checkpoints

### Apres PHASE 1 (Etapes 1-3) :
- [ ] 0 fichier frontend > 300 lignes
- [ ] Composants reutilisables extraits (onglets, panels, KPIs)

### Apres PHASE 2-3 (Etapes 4-5) :
- [ ] 0 page avec `useEffect + fetchJson` pour le chargement
- [ ] 0 formulaire avec `useState` brut

### Apres PHASE 4 (Etapes 6-7) :
- [ ] Recherche globale fonctionnelle (taper un nom → resultats)
- [ ] PDF telechargeables depuis le frontend

### Apres PHASE 5 (Etape 8) :
- [ ] 0 endpoint `-> dict`, Swagger 100% documente

### Apres PHASE 6-7 (Etapes 9-11) :
- [ ] 90+ tests frontend, 260+ tests backend
- [ ] Score : **10/10**
- [ ] **Le projet est parfait. Deploie.**
