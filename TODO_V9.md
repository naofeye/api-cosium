# TODO V9 — OptiFlow AI : Les derniers 2%

> **Contexte** : 8 iterations (V1-V8) completees. 279 tests backend, 70 frontend, 0 lint/TS.
> Le projet est fonctionnellement complet et securise.
> Cette V9 elimine les derniers irritants : 12 pages sur ancien pattern fetch,
> couverture deps.py/claude_provider, et features manquantes pour l'usage reel.
>
> **Regle** : Chaque etape doit apporter une valeur concrete. Pas de polish cosmetique.

---

## ETAPE 0 : Health check [ ]

- [ ] Docker UP, pytest 279+, vitest 70, ruff 0, tsc 0

---

## PHASE 1 : DERNIERE MIGRATION SWR (Etapes 1-2)

### ETAPE 1 : Migrer les 6 pages detail vers SWR [ ]

> 12 pages utilisent encore `useEffect + fetchJson` pour le chargement.
> Les 6 plus visibles sont les pages detail (cases/[id], clients/[id], devis/[id], factures/[id], pec/[id], dashboard).

- [ ] `dashboard/page.tsx` : remplacer `Promise.all([fetchJson(...), fetchJson(...)])` par 2 hooks `useSWR`
- [ ] `cases/[id]/page.tsx` : remplacer le `fetchJson` de chargement par `useSWR`
- [ ] `clients/[id]/page.tsx` : remplacer par `useSWR` pour la vue 360
- [ ] `devis/[id]/page.tsx` : remplacer par `useSWR`
- [ ] `factures/[id]/page.tsx` : remplacer par `useSWR`
- [ ] `pec/[id]/page.tsx` : remplacer par `useSWR`
- [ ] Objectif : navigation entre pages = instant (donnees en cache SWR)
- [ ] Verifier : `tsc --noEmit` passe

---

### ETAPE 2 : Migrer les 6 pages secondaires vers SWR [ ]

> admin, getting-started, rapprochement, settings/ai-usage, settings/billing, settings/erp

- [ ] `admin/page.tsx` : hooks SWR pour health + metrics
- [ ] `getting-started/page.tsx` : hook SWR pour onboarding status
- [ ] `rapprochement/page.tsx` : hook SWR pour transactions + unmatched
- [ ] `settings/ai-usage/page.tsx` : hook SWR pour usage
- [ ] `settings/billing/page.tsx` : hook SWR pour billing status
- [ ] `settings/erp/page.tsx` : hook SWR pour sync status + erp types
- [ ] Objectif : **0 page avec `useEffect + fetchJson` pour le chargement de donnees**
- [ ] Verifier : `grep -rl "setLoading" frontend/src/app/ --include="*.tsx"` retourne 0

---

## PHASE 2 : TESTS MANQUANTS (Etapes 3-4)

### ETAPE 3 : Tester deps.py et claude_provider (couverture < 50%) [ ]

> `deps.py` est a 48% — c'est le coeur de l'auth. `claude_provider.py` est a 41%.

- [ ] `tests/test_deps.py` :
  - Test `get_current_user` avec token valide (cookie) → retourne user
  - Test `get_current_user` avec token expire → 401
  - Test `get_current_user` avec token invalide → 401
  - Test `get_current_user` sans token → 401
  - Test `require_role("admin")` avec user admin → OK
  - Test `require_role("admin")` avec user operator → 403
  - Test `require_tenant_role("admin")` avec bon tenant → OK
  - Test `require_tenant_role("admin")` avec mauvais role → 403
- [ ] `tests/test_claude_provider.py` :
  - Mock de l'API Anthropic
  - Test `query()` retourne du texte
  - Test `query_with_usage()` retourne text + tokens_in + tokens_out
  - Test avec API key vide → erreur propre
- [ ] Objectif : couverture deps.py > 80%, claude_provider > 60%

---

### ETAPE 4 : Tests frontend pour les pages critiques [ ]

> 70 tests sur composants. 0 test de page. Ajoutons les pages critiques.

- [ ] `tests/pages/login.test.tsx` :
  - Rendu du formulaire (email, password, bouton)
  - Bouton desactive si champs vides
  - Erreur affichee si login echoue (mock fetch)
- [ ] `tests/pages/cases-new.test.tsx` :
  - Rendu du formulaire (nom, prenom, source)
  - Bouton desactive si nom vide
  - Soumission appelle fetchJson (mock)
- [ ] `tests/components/GlobalSearch.test.tsx` :
  - Rendu avec input
  - Pas d'appel API si < 2 caracteres
  - Appel API apres saisie de 3+ caracteres (mock SWR)
- [ ] Objectif : 85+ tests frontend

---

## PHASE 3 : FEATURES POUR L'USAGE REEL (Etapes 5-7)

### ETAPE 5 : Rate limiting sur les endpoints sensibles [ ]

> Seul le login est rate-limite. Les endpoints de creation et de mutation sont ouverts.

- [ ] Backend : etendre le rate limiter existant (`core/rate_limiter.py`) :
  - `/api/v1/auth/login` : 10 req/min (deja fait)
  - `/api/v1/auth/refresh` : 20 req/min
  - `/api/v1/onboarding/signup` : 5 req/min (anti-spam)
  - `/api/v1/ai/copilot/query` : 30 req/min (IA couteuse)
  - `/api/v1/marketing/campaigns/*/send` : 5 req/min (anti-spam)
- [ ] Tests : depasser la limite → 429

---

### ETAPE 6 : Restreindre Swagger en production [ ]

> `/docs` et `/openapi.json` sont exposes publiquement. En prod, ca expose toute l'API.

- [ ] Modifier `main.py` : conditionner Swagger selon l'environnement :
  ```python
  docs_url = "/docs" if settings.app_env in ("local", "development", "test") else None
  redoc_url = "/redoc" if settings.app_env in ("local", "development", "test") else None
  app = FastAPI(title="OptiFlow AI API", version="1.1.0", docs_url=docs_url, redoc_url=redoc_url)
  ```
- [ ] En production, Swagger est desactive. L'API reste fonctionnelle mais non documentee publiquement.
- [ ] Pour deboguer en prod : `APP_ENV=development docker compose restart api` temporairement
- [ ] Tests : verifier que `/docs` retourne 200 en test et que le comportement est correct

---

### ETAPE 7 : Validation en temps reel du mot de passe sur settings [ ]

> La page settings appelle `/auth/change-password` mais ne montre pas la force du mot de passe en temps reel.

- [ ] Frontend `settings/page.tsx` : ajouter des indicateurs visuels sous le champ "Nouveau mot de passe" :
  - Barre de force (faible/moyen/fort) basee sur : longueur >= 8, contient majuscule, contient chiffre
  - Couleurs : rouge (faible), ambre (moyen), vert (fort)
  - Messages : "8 caracteres minimum", "Ajoutez une majuscule", "Ajoutez un chiffre"
- [ ] Utiliser le schema Zod `ChangePasswordRequest` existant pour la validation cote client
- [ ] Desactiver le bouton tant que le nouveau MDP ne respecte pas les 3 regles

---

## PHASE 4 : DOCUMENTATION FINALE (Etape 8)

### ETAPE 8 : Mise a jour complete de la documentation [ ]

- [ ] `README.md` : mettre a jour les metriques (279 tests, 88% couverture, 70 tests frontend, 115 endpoints)
- [ ] `CONTRIBUTING.md` : ajouter section "Auth httpOnly" et "Encryption Cosium"
- [ ] `CHANGELOG.md` : ajouter v1.2.0 avec toutes les corrections V6-V9
- [ ] `docs/ARCHITECTURE_DECISIONS.md` : ajouter :
  - Pourquoi les tokens ne sont plus dans le body JSON (P0.1 Codex)
  - Pourquoi Fernet pour les credentials Cosium (pas bcrypt)
  - Pourquoi SHA-256 pour les refresh tokens (pas bcrypt — performance)
  - Pourquoi `user_id=0` est garde sur les taches automatiques
- [ ] Verifier que `.env.example` a `ENCRYPTION_KEY` documente
- [ ] Supprimer ou archiver les TODO V1-V8 (garder V9 comme reference active)

---

## PHASE 5 : TEST COSIUM REEL (Etape 9)

### ETAPE 9 : Connexion Cosium reelle — premier test [ ]

> C'est l'etape ultime. Tout ce qui a ete construit depuis V1 converge ici.

- [ ] Configurer `.env` avec les vrais credentials Cosium
- [ ] `docker compose restart api`
- [ ] Depuis l'interface admin, cliquer "Synchroniser les clients"
- [ ] Verifier dans les logs : `docker compose logs api --tail=50`
  - Token obtenu (log `cosium_authenticated`)
  - Clients fetches (log `sync_customers_done`)
  - Warnings eventuels (clients sans nom, champs manquants)
- [ ] Verifier dans l'app :
  - Les clients Cosium apparaissent dans la liste
  - La vue 360 d'un client montre ses donnees
  - Le nombre de clients correspond a ce qui est dans Cosium
- [ ] Si erreur :
  - Timeout → verifier `COSIUM_TIMEOUT` et la connectivite reseau
  - 401 → verifier credentials dans `.env`
  - Parsing error → noter le champ problematique, adapter l'adapter
- [ ] Documenter les ecarts trouves dans `docs/COSIUM_INTEGRATION_NOTES.md`

---

## Checkpoints

### Apres PHASE 1 (Etapes 1-2) :
- [ ] 0 page avec `useEffect + fetchJson` pour le chargement
- [ ] Navigation instantanee grace au cache SWR

### Apres PHASE 2 (Etapes 3-4) :
- [ ] Couverture backend > 90%
- [ ] 85+ tests frontend

### Apres PHASE 3 (Etapes 5-7) :
- [ ] Rate limiting sur 5 endpoints sensibles
- [ ] Swagger desactive en prod
- [ ] Password strength indicator fonctionnel

### Apres PHASE 4 (Etape 8) :
- [ ] Documentation a jour et complete

### Apres PHASE 5 (Etape 9) :
- [ ] **Premiere synchronisation Cosium reussie**
- [ ] Clients reels visibles dans OptiFlow
