# TODO V2 — OptiFlow AI : Version Professionnelle

> **Objectif** : Transformer le prototype fonctionnel (30 etapes completees) en une application de qualite production.
> On ne code PAS de nouvelles fonctionnalites. On solidifie, on teste, on securise, on polit.
>
> **Meme mode operatoire que TODO.md** : Etape 0 obligatoire, puis une etape a la fois, validation, arret, resume.

---

## ETAPE 0 : Health check complet [ ]

> **A executer a CHAQUE session.** Verifier que tout l'environnement tourne.

- [ ] `docker --version` et `docker compose version`
- [ ] `docker compose up --build -d` — les 6 services demarrent (postgres, redis, minio, mailhog, api, web)
- [ ] `curl http://localhost:8000/docs` — Swagger repond
- [ ] `curl http://localhost:3000` — Frontend repond
- [ ] `docker compose exec api python -c "from app.main import app; print('OK')"` — pas d'import error
- [ ] `docker compose logs api --tail=50` — pas d'erreur Python au demarrage
- [ ] `docker compose logs web --tail=50` — pas d'erreur de compilation Next.js
- [ ] Si un service echoue : corriger AVANT de continuer

---

## PHASE 1 : STABILISATION BACKEND (Etapes 1-5)

### ETAPE 1 : Decouper models.py en modules [x]

> **Probleme** : `backend/app/models.py` fait 29K (800+ lignes), un seul fichier contient ~25 modeles SQLAlchemy.
> C'est un cauchemar de maintenance et ca viole la regle des 300 lignes max.
> **Fichiers a lire** : `backend/app/models.py`, `backend/app/db/base.py`, `backend/alembic/env.py`

- [x] Creer `backend/app/models/` en tant que package Python
- [x] Creer `backend/app/models/__init__.py` qui re-exporte tous les modeles (pour ne pas casser les imports existants)
- [x] Decouper en 14 fichiers thematiques : tenant.py, user.py, client.py, case.py, document.py, devis.py, facture.py, payment.py, pec.py, reminder.py, marketing.py, notification.py, audit.py, interaction.py, ai.py
- [x] `alembic/env.py` importe via le package `models` (inchange, fonctionne grace au __init__.py)
- [x] TOUS les imports existants (`from app.models import X`) fonctionnent sans modification grace au re-export
- [x] Ancien `models.py` monolithique supprime
- [x] Verifie : API demarre sans erreur, Swagger 200, health OK, alembic detecte 0 table ajoutee/supprimee

---

### ETAPE 2 : Audit et correction de tous les tests backend [x]

> **Probleme** : 42 fichiers de tests existent mais n'ont probablement jamais ete executes ensemble avec succes.
> Il faut les faire passer a 100% et corriger les cas defaillants.
> **Fichiers a lire** : `backend/tests/conftest.py`, tous les fichiers `backend/tests/test_*.py`

- [ ] Executer `docker compose exec api pytest -v --tb=long 2>&1 | head -200` — noter le nombre de pass/fail/error
- [ ] Lister TOUS les tests en echec et les categoriser :
  - Import errors (modele ou service qui a change)
  - Fixture missing (conftest incomplet)
  - Assertion errors (logique incorrecte)
  - Database errors (schema mismatch)
- [ ] Corriger les fixtures dans `conftest.py` :
  - Verifier que la BDD de test cree TOUTES les tables (via `Base.metadata.create_all`)
  - Verifier que les fixtures creent un tenant par defaut (multi-tenant oblige)
  - Verifier que `auth_headers` fonctionne avec le systeme JWT actuel
- [ ] Corriger chaque fichier de test en echec, un par un, dans cet ordre :
  1. `test_auth.py` (fondation)
  2. `test_cases.py`
  3. `test_clients.py`
  4. `test_documents.py`
  5. `test_payments.py`
  6. `test_devis.py`
  7. `test_factures.py`
  8. `test_pec.py`
  9. `test_reminders.py`
  10. `test_marketing.py`
  11. `test_banking.py`
  12. Tous les autres
- [ ] Objectif : `pytest -v` = 100% pass, 0 fail, 0 error
- [ ] Ajouter `pytest --strict-markers` pour interdire les markers non declares
- [ ] Ajouter un fichier `pytest.ini` ou section `[tool.pytest.ini_options]` dans `pyproject.toml` avec les markers declares (`cosium_live`, `slow`, etc.)
- [ ] Mesurer la couverture : `pytest --cov=app --cov-report=term-missing` — noter le % global

---

### ETAPE 3 : Validation des schemas Pydantic et contrats API [x]

> **Probleme** : Les schemas existent mais la validation peut etre trop permissive (pas de constraints, pas de regex).
> Les reponses API ne sont peut-etre pas toujours conformes aux response_model declares.
> **Fichiers a lire** : Tous les fichiers dans `backend/app/domain/schemas/`

- [ ] Auditer chaque schema de creation (`*Create`) et ajouter les contraintes manquantes :
  - `min_length`, `max_length` sur les champs string
  - `ge=0` sur les montants
  - `EmailStr` pour les emails
  - `Field(pattern=...)` pour les formats specifiques (telephone, SIRET, etc.)
  - `Field(examples=[...])` pour la documentation Swagger
- [ ] Auditer chaque schema de reponse (`*Response`) et verifier que `model_config = ConfigDict(from_attributes=True)` est present
- [ ] Verifier que CHAQUE endpoint a un `response_model` explicite (pas de `dict` ou de `Any`)
- [ ] Verifier que les enums de statut sont des `Enum` Python (pas des strings libres)
- [ ] Creer des tests de schema : `tests/test_schemas.py` — verifier que les schemas rejettent les donnees invalides
- [ ] Generer et sauvegarder le schema OpenAPI : `docker compose exec api python -c "from app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > docs/openapi.json`
- [ ] Verifier dans Swagger que TOUS les endpoints sont documentes avec exemples

---

### ETAPE 4 : Gestion d'erreurs coherente et exhaustive [x]

> **Probleme** : Les exceptions metier existent mais ne sont peut-etre pas utilisees partout. Certains services peuvent encore lever des HTTPException directement.
> **Fichiers a lire** : `backend/app/core/exceptions.py`, `backend/app/main.py`, tous les services

- [ ] Auditer TOUS les services : grep pour `HTTPException` — chaque occurrence doit etre remplacee par une exception metier custom
- [ ] Auditer TOUS les routers : grep pour `db.query`, `db.add`, `db.commit` — aucune logique BDD ne doit etre dans un router
- [ ] Verifier que le handler d'exceptions global dans `main.py` couvre :
  - `BusinessError` → 400
  - `NotFoundError` → 404
  - `AuthenticationError` → 401
  - `ForbiddenError` → 403 (creer si manquant)
  - `ValidationError` → 422
  - `RateLimitError` → 429
  - `Exception` generique → 500 avec log error (PAS de stacktrace expose au client)
- [ ] Standardiser le format d'erreur JSON : `{"error": {"code": "NOT_FOUND", "message": "Ce dossier n'existe pas", "details": {...}}}`
- [ ] Ajouter des tests pour chaque type d'erreur : `tests/test_error_handling.py`

---

### ETAPE 5 : Logging structure et correlation [x]

> **Probleme** : Le logging existe mais il manque la correlation entre les requetes (request_id) et le contexte utilisateur.
> **Fichiers a lire** : `backend/app/core/logging.py`, `backend/app/main.py`

- [ ] Verifier que structlog est configure correctement avec processeurs JSON
- [ ] Ajouter un middleware `RequestIdMiddleware` : genere un UUID par requete, l'injecte dans les headers de reponse (`X-Request-ID`), le bind au logger (contexte structlog)
- [ ] Verifier que CHAQUE service loggue les operations critiques avec contexte :
  - `logger.info("case_created", case_id=..., user_id=..., tenant_id=...)`
  - `logger.error("payment_failed", reason=..., amount=..., facture_id=...)`
- [ ] Configurer les niveaux de log : DEBUG en dev, INFO en prod, WARNING pour les services externes
- [ ] Verifier qu'aucun `print()` ne reste dans le code : `grep -r "print(" backend/app/`
- [ ] Ajouter le request_id dans les audit_logs pour tracer une requete de bout en bout

---

## PHASE 2 : SOLIDIFICATION FRONTEND (Etapes 6-10)

### ETAPE 6 : TypeScript strict et nettoyage des types [x]

> **Probleme** : `tsconfig.json` a `strict: false`. Les types sont faibles, risque de bugs runtime.
> **Fichiers a lire** : `frontend/tsconfig.json`, tous les fichiers `.tsx` et `.ts`

- [ ] Activer `strict: true` dans `tsconfig.json`
- [ ] Corriger TOUTES les erreurs TypeScript une par une :
  - Ajouter les types manquants sur les props de composants
  - Typer les reponses API (creer des interfaces dans `lib/types.ts`)
  - Remplacer tous les `any` par des types explicites
  - Ajouter `null` checks la ou necessaire
- [ ] Creer `frontend/src/lib/types.ts` : interfaces TypeScript pour TOUTES les entites API :
  - `User`, `Tenant`, `Customer`, `Case`, `Document`, `Devis`, `DevisLigne`
  - `Facture`, `FactureLigne`, `Payment`, `PECRequest`, `Notification`, `ActionItem`
  - `Campaign`, `Segment`, `Interaction`, `AuditLog`, `BankTransaction`
  - `ApiResponse<T>`, `PaginatedResponse<T>`, `ApiError`
- [ ] Verifier : `npm run build` passe sans erreur ni warning TypeScript

---

### ETAPE 7 : React Hook Form + Zod pour tous les formulaires [x]

> **Probleme** : Les formulaires utilisent du state React brut. Pas de validation structuree, pas de gestion d'erreurs propre.
> **Fichiers a lire** : Tous les fichiers contenant des `<form>` ou `<input>`

- [ ] Installer : `npm install react-hook-form @hookform/resolvers zod`
- [ ] Creer les schemas Zod dans `lib/schemas/` (un fichier par domaine) :
  - `lib/schemas/auth.ts` : loginSchema
  - `lib/schemas/client.ts` : clientCreateSchema, clientUpdateSchema
  - `lib/schemas/case.ts` : caseCreateSchema
  - `lib/schemas/devis.ts` : devisCreateSchema, devisLineSchema
  - `lib/schemas/pec.ts` : pecCreateSchema
  - `lib/schemas/marketing.ts` : campaignSchema, segmentSchema
  - `lib/schemas/onboarding.ts` : signupSchema, cosiumConnectSchema
- [ ] Creer un composant wrapper `components/form/FormField.tsx` qui integre React Hook Form + affichage erreur
- [ ] Refactorer CHAQUE formulaire existant pour utiliser `useForm()` + `zodResolver()` :
  - `login/page.tsx`
  - `cases/new/page.tsx`
  - `clients/new/page.tsx`
  - `devis/new/page.tsx`
  - `onboarding/page.tsx`
  - Tous les autres formulaires
- [ ] Verifier : chaque formulaire valide en temps reel, les erreurs s'affichent sous le champ, le bouton submit est desactive si invalide

---

### ETAPE 8 : SWR pour le data fetching et cache [x]

> **Probleme** : Chaque page fait un `fetchJson()` dans un `useEffect`. Pas de cache, pas de revalidation, pas de deduplication.
> Navigation = refetch complet a chaque fois.

- [ ] Installer : `npm install swr`
- [ ] Creer `lib/fetcher.ts` : fetcher compatible SWR qui utilise `fetchJson()` avec auth
- [ ] Creer des hooks custom dans `lib/hooks/` :
  - `useClients(params)` — liste clients paginee
  - `useCases(params)` — liste dossiers
  - `useCase(id)` — detail dossier
  - `useDevis(params)`, `useDevisDetail(id)`
  - `useFactures(params)`, `useFactureDetail(id)`
  - `usePECRequests(params)`
  - `usePayments(params)`
  - `useDashboard(period)`
  - `useNotifications()`
  - `useActionItems()`
  - `useAnalytics(type, params)`
- [ ] Refactorer CHAQUE page pour utiliser les hooks SWR au lieu de `useEffect + useState`
- [ ] Configurer SWR globalement : `revalidateOnFocus: false`, `dedupingInterval: 5000`
- [ ] Ajouter des mutations SWR pour les operations d'ecriture (optimistic updates sur les listes)
- [ ] Verifier : naviguer entre pages = pas de flash de chargement si les donnees sont en cache

---

### ETAPE 9 : Error Boundaries et gestion d'erreurs globale [x]

> **Probleme** : Si un composant React crash, la page entiere devient blanche. Aucun Error Boundary n'existe.

- [ ] Creer `components/ErrorBoundary.tsx` : composant React class qui catch les erreurs de rendu, affiche `ErrorState` avec bouton "Recharger"
- [ ] Creer `app/error.tsx` : page d'erreur Next.js globale (Error Boundary racine)
- [ ] Creer `app/not-found.tsx` : page 404 custom avec design coherent et lien retour
- [ ] Creer `app/loading.tsx` : page de chargement globale avec skeleton
- [ ] Wrapper chaque route principale dans un Error Boundary dans `layout.tsx`
- [ ] Ameliorer `lib/api.ts` :
  - Timeout configurable (10s par defaut)
  - Retry automatique sur erreur reseau (1 retry avec backoff)
  - Detection offline (navigator.onLine) avec message "Vous etes hors ligne"
- [ ] Verifier : provoquer une erreur dans un composant, verifier que l'Error Boundary s'affiche, que le reste de l'app fonctionne

---

### ETAPE 10 : Accessibilite et polish UI [x]

> **Probleme** : L'accessibilite est minimale. Pas de focus visible, pas de navigation clavier complete, contrastes non verifies.

- [ ] Auditer les contrastes WCAG AA sur toutes les couleurs de texte :
  - Texte gray-500 sur fond white → verifier ratio >= 4.5:1
  - Texte white sur fond blue-600, emerald-600, red-600 → verifier
  - Badge text sur badge background
- [ ] Ajouter `focus-visible:ring-2 focus-visible:ring-blue-500` sur TOUS les elements interactifs
- [ ] Verifier la navigation clavier complete :
  - Tab navigue entre tous les elements interactifs
  - Enter active les boutons et liens
  - Escape ferme les modales et dropdowns
  - Les menus dropdown sont navigables au clavier (fleches haut/bas)
- [ ] Ajouter `aria-label` sur chaque icone sans texte (boutons icone seule, icones de statut)
- [ ] Ajouter `aria-live="polite"` sur les zones de toast et de notification
- [ ] Verifier que les modales (ConfirmDialog) trappent le focus
- [ ] Verifier le responsive a 1366x768 (laptop) : pas de debordement, sidebar collapsee si necessaire
- [ ] Supprimer TOUS les `console.log` du code frontend

---

## PHASE 3 : QUALITE ET CI/CD (Etapes 11-14)

### ETAPE 11 : Linting et formatage automatique [x]

> **Probleme** : Aucun outil de qualite de code n'est configure. Le style est inconsistant.

#### Backend
- [ ] Creer `backend/pyproject.toml` avec config Ruff :
  - `[tool.ruff]` : `line-length = 120`, `target-version = "py312"`
  - `select = ["E", "W", "F", "I", "N", "UP", "S", "B", "A", "C4", "DTZ", "T20"]`
- [ ] Ajouter `ruff` dans `requirements.txt`
- [ ] Executer `ruff check backend/app/ --fix` — corriger les erreurs auto-fixables
- [ ] Executer `ruff format backend/app/` — formater tout le code
- [ ] Corriger les erreurs restantes manuellement

#### Frontend
- [ ] Verifier que ESLint est configure. Sinon : `npm install -D eslint eslint-config-next`
- [ ] Installer Prettier : `npm install -D prettier eslint-config-prettier`
- [ ] Creer `.prettierrc` : `{ "semi": true, "singleQuote": false, "tabWidth": 2, "trailingComma": "all" }`
- [ ] Executer `npx prettier --write "src/**/*.{ts,tsx}"` — formater tout
- [ ] Executer `npx next lint` — corriger les erreurs ESLint
- [ ] Ajouter les scripts npm : `"lint"`, `"format"`, `"typecheck"`

---

### ETAPE 12 : Tests frontend [x]

> **Probleme** : Zero test frontend. C'est un risque majeur pour la maintenance.

- [ ] Installer : `npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom`
- [ ] Creer `vitest.config.ts` avec environment jsdom
- [ ] Creer `tests/setup.ts` avec les matchers jest-dom
- [ ] Ecrire des tests pour les composants UI critiques :
  - `tests/components/Button.test.tsx` — rendu, variantes, disabled, click
  - `tests/components/StatusBadge.test.tsx` — couleurs par statut
  - `tests/components/MoneyDisplay.test.tsx` — formatage montants
  - `tests/components/DateDisplay.test.tsx` — formatage dates
  - `tests/components/DataTable.test.tsx` — rendu, pagination, tri
  - `tests/components/EmptyState.test.tsx` — rendu avec CTA
  - `tests/components/Toast.test.tsx` — apparition, auto-dismiss
- [ ] Ecrire des tests pour les utilitaires :
  - `tests/lib/format.test.ts` — formatMoney, formatDate, formatPercent
  - `tests/lib/auth.test.ts` — login, logout, refresh (mock fetch)
- [ ] Ajouter les scripts npm : `"test": "vitest run"`, `"test:watch": "vitest"`
- [ ] Objectif : couverture > 60% sur les composants et utilitaires

---

### ETAPE 13 : CI/CD avec GitHub Actions [x]

> **Probleme** : Aucune integration continue. Les bugs sont decouverts manuellement.

- [ ] Creer `.github/workflows/ci.yml` :
  - Job `backend-lint` : ruff check + ruff format --check
  - Job `backend-test` : pytest avec postgres + redis Docker
  - Job `frontend-lint` : eslint + typecheck
  - Job `frontend-test` : vitest
  - Job `build` : docker compose build
- [ ] Creer `docker-compose.test.yml` : postgres + redis uniquement (pour les tests backend CI)
- [ ] Creer `.github/workflows/deploy.yml` : deploiement sur push main (quand VPS configure)
- [ ] Verifier : pousser une branche, la CI tourne, les tests passent

---

### ETAPE 14 : Documentation technique minimale [x]

> **Probleme** : Le README existe mais est-il complet et a jour?

- [ ] Mettre a jour `README.md` :
  - Description du projet (3 lignes)
  - Prerequisites (Docker, Node, Python)
  - Installation en 3 commandes
  - URLs des services (API, Frontend, MinIO, Mailhog, Swagger)
  - Credentials de demo
  - Structure du projet (arbre simplifie)
  - Comment lancer les tests
- [ ] Creer `CONTRIBUTING.md` :
  - Architecture en couches (router → service → repo)
  - Comment ajouter un nouveau module (template des 7 fichiers)
  - Conventions de nommage
  - Comment creer une migration
- [ ] Verifier que `.env.example` est a jour avec TOUTES les variables utilisees dans `core/config.py`

---

## PHASE 4 : SECURITE ET PRODUCTION (Etapes 15-18)

### ETAPE 15 : Securite des tokens et sessions [x]

> **Probleme** : Les tokens JWT sont stockes dans des cookies non httpOnly cote frontend. Vulnerable au XSS.

- [ ] Backend : modifier les endpoints auth pour setter les cookies httpOnly, Secure, SameSite=Lax :
  - `POST /auth/login` → `Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=1800`
  - `POST /auth/refresh` → meme chose avec nouveau access_token
  - `POST /auth/logout` → `Set-Cookie: access_token=; Max-Age=0`
- [ ] Backend : ajouter `GET /auth/me` qui retourne le user courant (le frontend l'appelle au lieu de decoder le JWT)
- [ ] Frontend : supprimer js-cookie pour les tokens. Les cookies httpOnly sont envoyes automatiquement par le navigateur.
- [ ] Frontend : modifier `lib/api.ts` pour utiliser `credentials: "include"` au lieu d'ajouter manuellement le header Authorization
- [ ] Backend : configurer CORS avec `allow_credentials=True` et origines explicites (pas de wildcard `*`)
- [ ] Ajouter protection CSRF : token CSRF dans un cookie non-httpOnly + header `X-CSRF-Token` sur les requetes mutatives
- [ ] Tests : verifier que les cookies sont httpOnly, que le CSRF fonctionne

---

### ETAPE 16 : Seed de donnees realistes [x]

> **Probleme** : Les donnees de demo sont minimalistes. Pour une demo convaincante, il faut des donnees riches et coherentes.

- [ ] Creer `backend/app/seed_professional.py` : script de seed complet qui cree :
  - 1 organisation "OptiDistribution" + 2 tenants ("Paris Champs-Elysees", "Lyon Part-Dieu")
  - 3 utilisateurs par tenant (admin, manager, operateur)
  - 150 clients avec noms/prenoms/emails realistes
  - 80 dossiers (mix de statuts)
  - 200 documents associes
  - 50 devis (statuts varies)
  - 40 factures (payees, partielles, impayees)
  - 60 paiements (dates etalees sur 6 mois)
  - 20 PEC requests (mix de statuts)
  - 30 relances
  - 10 campagnes marketing
  - 500 interactions
  - 50 transactions bancaires
  - Donnees financieres coherentes : les montants s'additionnent correctement
- [ ] Ajouter une commande : `docker compose exec api python -m app.seed_professional`
- [ ] Verifier : le dashboard affiche des KPIs realistes, les graphiques sont parlants

---

### ETAPE 17 : Tests end-to-end du workflow complet [x]

> **Probleme** : Le test e2e existe mais n'a jamais ete valide. Il faut un vrai parcours utilisateur teste.

- [ ] Creer `backend/tests/test_e2e_professional.py` : test sequentiel du workflow complet :
  1. Login admin → obtenir tokens
  2. Creer un client (nom, prenom, email, tel)
  3. Creer un dossier pour ce client
  4. Uploader 2 documents au dossier
  5. Verifier la completude du dossier
  6. Creer un devis avec 3 lignes
  7. Verifier les calculs (HT, TVA, TTC, parts)
  8. Passer le devis en statut "signe"
  9. Generer une facture depuis le devis
  10. Enregistrer un paiement partiel
  11. Verifier le statut de la facture (partiellement_payee)
  12. Creer une PEC request
  13. Changer le statut de la PEC en "acceptee"
  14. Verifier le dashboard
  15. Consulter la vue client 360
  16. Exporter en Excel
  17. Consulter les audit logs
- [ ] Le test doit passer en < 30 secondes
- [ ] Creer un test e2e multi-tenant :
  1. Login admin tenant A → creer un client
  2. Switch tenant B → verifier que le client n'est PAS visible
  3. Creer un client dans tenant B
  4. Switch retour tenant A → verifier isolation
- [ ] Verifier : les 2 tests e2e passent a 100%

---

### ETAPE 18 : Audit securite Cosium (verification finale) [x]

> **Probleme** : La regle de securite Cosium (lecture seule) est critique. Audit formel obligatoire.

- [ ] Scan du code : `grep -ri "put\|\.post\|delete\|patch" backend/app/integrations/cosium/`
- [ ] Verifier que CosiumConnector n'a QUE authenticate() et get_*() comme methodes
- [ ] Verifier qu'il n'y a PAS de methode generique `request()` ou `send()` avec methode HTTP variable
- [ ] Verifier les tests `test_cosium.py` : un test asserte que la classe n'a pas de methode d'ecriture
- [ ] Documenter le resultat dans `docs/AUDIT_COSIUM_SECURITY.md`

---

## PHASE 5 : POLISH FINAL (Etapes 19-22)

### ETAPE 19 : Performance frontend mesuree [x]

> **Probleme** : Aucune mesure de performance. On ne sait pas si les pages chargent en < 3 secondes.

- [ ] Installer `@next/bundle-analyzer` : analyser le bundle, identifier les pages lourdes
- [ ] Appliquer `React.lazy()` + `Suspense` sur les pages avec graphiques
- [ ] Verifier que `next/image` est utilise pour les images
- [ ] Verifier le debounce (300ms) sur TOUTES les barres de recherche
- [ ] Mesurer les Core Web Vitals : Lighthouse en mode production
- [ ] Objectif : LCP < 2.5s, FID < 100ms, CLS < 0.1

---

### ETAPE 20 : Page de settings et preferences utilisateur [x]

> Verifier que les pages de parametres sont completes et fonctionnelles.

- [ ] Verifier que `app/settings/page.tsx` contient :
  - Profil utilisateur (nom, email, changement de mot de passe)
  - Preferences (format de date, timezone)
  - Notifications (quelles notifications recevoir)
  - Connexion ERP (statut, derniere sync, bouton re-sync)
  - Facturation (plan, statut, usage IA)
- [ ] Verifier que le changement de mot de passe fonctionne
- [ ] Ajouter un lien "Aide" / "Support" dans le menu utilisateur

---

### ETAPE 21 : Revue complete de l'UX [x]

> Parcourir TOUTE l'application comme un opticien qui decouvre le logiciel.

- [ ] Parcourir le scenario de demo complet (12 pages) et pour CHAQUE page verifier :
  - [ ] Etat loading present (skeleton, pas page blanche)
  - [ ] Etat erreur present (message + bouton reessayer)
  - [ ] Etat vide present (illustration + texte + CTA)
  - [ ] Tous les textes en francais (zero anglais)
  - [ ] Montants formates (1 234,56 €)
  - [ ] Dates formatees (03 avr. 2026)
  - [ ] Badges de statut avec les bonnes couleurs
  - [ ] Boutons d'action visibles sans scroller
  - [ ] Breadcrumb correct
  - [ ] Navigation retour possible
- [ ] Corriger chaque probleme trouve
- [ ] Verifier la coherence visuelle globale : meme style de cartes, memes espacements, memes ombres partout

---

### ETAPE 22 : Preparation de la V1 release [x]

> **C'est l'etape finale avant le lancement.**

- [ ] Suite de tests complete : backend (pytest) + frontend (vitest) → tout passe
- [ ] Linter : backend (ruff) + frontend (eslint + prettier) → 0 erreur
- [ ] Build de production : `docker compose -f docker-compose.prod.yml build` → success
- [ ] Script de deploiement a jour : `scripts/deploy.sh`
- [ ] Backups fonctionnels : `scripts/backup_db.sh`
- [ ] `.env.production.example` a jour avec toutes les variables documentees
- [ ] Tag Git : `git tag v1.0.0 -m "OptiFlow AI v1.0.0 - Production Ready"`
- [ ] CHANGELOG cree avec la liste des fonctionnalites v1
- [ ] Verification finale : scenario de demo complet en < 10 minutes sans interruption

---

## Checkpoints de validation

### Apres PHASE 1 (Etapes 1-5) — Backend solide :
- [ ] Models decoupe, tests 100% pass, schemas valides, erreurs propres, logs structures
- [ ] `docker compose exec api pytest -v` → 100% pass

### Apres PHASE 2 (Etapes 6-10) — Frontend solide :
- [ ] TypeScript strict, formulaires valides, data caching, error boundaries, accessibilite
- [ ] `npm run build` → 0 erreur, `npm run test` → pass

### Apres PHASE 3 (Etapes 11-14) — Qualite automatisee :
- [ ] Linting, tests, CI/CD, documentation
- [ ] Push sur main → CI verte

### Apres PHASE 4 (Etapes 15-18) — Securite et donnees :
- [ ] Tokens httpOnly, CSRF, audit Cosium, seed realiste, e2e valide
- [ ] Pret pour une demo client

### Apres PHASE 5 (Etapes 19-22) — Application professionnelle :
- [ ] Performante, coherente, documentee, deployable
- [ ] **Pret pour la production et les premiers clients**
