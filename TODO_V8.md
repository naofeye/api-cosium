# TODO V8 — OptiFlow AI : Nettoyage final avant connexion Cosium

> **Contexte** : V1-V7 terminees. 247 tests, 0 lint, securite OK.
> Le scan V8 revele : 63 `datetime.utcnow()` depreces, 26 `user_id=0` restants,
> 1 fichier dead code, et 1 formulaire non migre.
> Cette V8 nettoie tout ca pour un code 100% propre.

---

## ETAPE 0 : Health check [ ]

- [ ] Docker UP, pytest 247+, vitest 70, ruff 0, tsc 0

---

## PHASE 1 : DEAD CODE ET DEPRECATIONS (Etapes 1-2)

### ETAPE 1 : Supprimer le dead code et migrer datetime.utcnow [ ]

> `cache.py` est 100% orphelin (0 import, 0 usage). `datetime.utcnow()` est deprece en Python 3.12.

- [ ] Supprimer `backend/app/core/cache.py` — fichier entierement inutilise
- [ ] Remplacer les 63 instances de `datetime.utcnow()` par `datetime.now(UTC)` dans tout le backend :
  - Ajouter `from datetime import UTC` ou `from datetime import timezone` selon le fichier
  - Pattern : `datetime.utcnow()` → `datetime.now(UTC)`
  - Fichiers concernes : tous les modeles (16 fichiers), repositories (banking, facture, marketing, reminder, renewal), services (analytics, erp_sync, gdpr, reminder), routers (admin_health), seed_demo.py
- [ ] Verifier : `pytest -q` passe, 0 warnings `datetime.utcnow` restants
- [ ] Bonus : `grep -rn "utcnow" backend/app/` retourne 0

---

### ETAPE 2 : Corriger les user_id=0 restants [ ]

> V7 a corrige les 5 plus critiques. Il reste 26 fonctions avec `user_id: int = 0`.
> Pour les fonctions moins critiques, ajouter un log warning au lieu de forcer le parametre.

- [ ] Pour les fonctions appelees depuis les routers (toujours avec tenant_ctx.user_id) : retirer le default
  - `case_service.create_case()`, `document_service.upload_document()`, `consent_service.upsert_consent()`
  - `gdpr_service.get_client_data()`, `gdpr_service.anonymize_client()`, `gdpr_service.export_client_data()`
  - `notification_service.notify()` (garder le default ici — appele aussi par event_service)
- [ ] Pour les fonctions appelees par des taches automatiques (Celery, event_service) : garder `user_id: int = 0` mais ajouter :
  ```python
  if not user_id:
      logger.warning("operation_without_user", action="create", entity="devis")
  ```
- [ ] Verifier : `pytest -q` passe, `grep -c "user_id.*= 0" backend/app/services/*.py` diminue significativement

---

## PHASE 2 : TESTS ET COUVERTURE (Etapes 3-4)

### ETAPE 3 : Tests pour les modules a faible couverture [ ]

> RAG (28%), cosium_connector (33%), collection_prioritizer (38%), billing_service (42%)

- [ ] `tests/test_rag.py` :
  - Test `search_docs("monture")` avec un dossier mock de pages Cosium → retourne du contenu
  - Test `search_docs("")` → retourne vide
  - Test avec 0 fichiers dans le dossier → retourne vide sans crash
- [ ] `tests/test_collection_prioritizer.py` (enrichir les tests existants) :
  - Test avec 0 items → retourne liste vide
  - Test que le score augmente avec le montant
  - Test que le score augmente avec l'anciennete
  - Test le tri par score decroissant
- [ ] `tests/test_cosium_connector.py` (enrichir) :
  - Test `get_customers()` avec mock retournant des donnees partielles (pas de email, pas de phone)
  - Test `get_customers()` avec mock retournant une liste vide
  - Test que `get_paginated()` s'arrete quand il n'y a plus de pages
- [ ] Objectif : couverture > 88%

---

### ETAPE 4 : Migrer StepAccount.tsx vers React Hook Form [ ]

> Dernier formulaire a migrer — le signup onboarding utilise encore useState brut.

- [ ] Le schema Zod `signupSchema` existe deja dans `lib/schemas/onboarding.ts`
- [ ] Modifier `onboarding/steps/StepAccount.tsx` :
  - Remplacer les 6 `useState` (company_name, owner_email, etc.) par `useForm<SignupFormData>`
  - Utiliser `zodResolver(signupSchema)`
  - Utiliser `register()` sur les inputs
  - Utiliser `errors.fieldName?.message` pour les erreurs
  - Utiliser `isSubmitting` au lieu de `loading`
  - Garder `showPassword` et `apiError` en useState (pas des champs du formulaire)
- [ ] Verifier : `tsc --noEmit` passe, le wizard d'onboarding fonctionne

---

## PHASE 3 : PREPARATION COSIUM (Etapes 5-6)

### ETAPE 5 : Test de connexion Cosium dry-run [ ]

> Verifier que le code est pret AVANT de brancher les vrais credentials.

- [ ] Creer `tests/test_cosium_dry_run.py` :
  - Test que `CosiumClient` peut etre instancie sans crash
  - Test que `authenticate()` avec des faux credentials retourne une erreur claire (pas un crash)
  - Test que le retry fonctionne (mock un timeout suivi d'un succes)
  - Test que `_ensure_token_valid()` re-authentifie quand le token est expire
  - Test que `get_paginated()` s'arrete proprement apres max_pages
  - Test que le `CosiumConnector` retourne des listes vides si aucune donnee (pas de crash)
- [ ] Creer `tests/test_encryption.py` :
  - Test `encrypt("hello")` → resultat != "hello"
  - Test `decrypt(encrypt("hello"))` → "hello"
  - Test `decrypt("invalid")` → erreur propre

---

### ETAPE 6 : Verification finale pre-Cosium [ ]

- [ ] `pytest -v --cov=app` → 255+ pass, couverture > 88%, 0 `datetime.utcnow` warnings
- [ ] `vitest run` → 70+ pass
- [ ] `ruff check` + `tsc --noEmit` + `prettier --check` → 0 erreur
- [ ] `grep -rn "utcnow" backend/app/` → 0 resultats
- [ ] `grep -rn "getToken\|setTokens\|localStorage" frontend/src/` → 0 resultats
- [ ] Login `Admin123` → OK
- [ ] Recherche globale → OK
- [ ] PDF devis/facture → OK
- [ ] Change password → OK
- [ ] Preparer `.env` avec credentials Cosium :
  ```
  COSIUM_BASE_URL=https://c1.cosium.biz
  COSIUM_TENANT=<ton-code-site>
  COSIUM_LOGIN=<ton-login>
  COSIUM_PASSWORD=<ton-mot-de-passe>
  ENCRYPTION_KEY=<generer avec: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
  ```
- [ ] **Lancer le test Cosium reel** : `POST /api/v1/sync/customers` depuis l'interface admin

---

## Checkpoints

### Apres PHASE 1 (Etapes 1-2) :
- [ ] 0 dead code, 0 `datetime.utcnow()`, user_id=0 reduit de 26 a < 10

### Apres PHASE 2 (Etapes 3-4) :
- [ ] Couverture > 88%, dernier formulaire migre RHF

### Apres PHASE 3 (Etapes 5-6) :
- [ ] Dry-run Cosium teste, encryption testee
- [ ] **Pret pour la connexion reelle**
