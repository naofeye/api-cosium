# TODO - Plan d'execution OptiFlow AI

> **MODE D'EMPLOI POUR CLAUDE CLI :**
> 1. Lis `CLAUDE.md` pour connaitre les regles du projet
> 2. **TOUJOURS executer l'ETAPE 0 en premier** (health check environnement), meme si elle est deja cochee
> 3. Une fois l'etape 0 validee, reprends a la premiere ligne `## ETAPE X : ... [ ]` (etape non cochee)
> 4. Lis le bloc de contexte de l'etape (fichiers a lire, specs)
> 5. Execute chaque sous-tache `- [ ]` dans l'ordre
> 6. Coche chaque sous-tache terminee : `- [x]`
> 7. Quand toutes les sous-taches sont faites, execute la **VALIDATION** (voir ci-dessous)
> 8. Coche l'etape parente : `## ETAPE X : ... [x]`
> 9. **ARRETE-TOI** et affiche un resume a l'utilisateur
> 10. Attends que l'utilisateur dise **"continue"** pour passer a la suite
>
> **REGLE ETAPE 0 OBLIGATOIRE :**
> - L'etape 0 est un **prealable systematique** a chaque session de travail.
> - Meme si on est a l'etape 6, 10 ou 20 : on commence TOUJOURS par l'etape 0 pour verifier que l'environnement est sain.
> - Si l'etape 0 echoue (service down, erreur Docker, etc.), corriger AVANT de passer a l'etape en cours.
> - L'etape 0 n'a pas besoin d'etre re-cochee : elle reste [x]. C'est un check, pas une tache a refaire.
>
> **REGLES :**
> - Ne saute JAMAIS une etape. L'ordre est strict.
> - Chaque etape est autonome : relis les fichiers concernes avant de modifier.
> - Respecte TOUTE la charte dans CLAUDE.md (patterns obligatoires, anti-patterns interdits, conventions).
> - Consulte `docs/specs/` quand tu as besoin de details metier.
> - Ne coche JAMAIS une etape qui ne compile pas ou dont les tests echouent.
>
> **VALIDATION OBLIGATOIRE (apres chaque etape) :**
> ```
> 1. docker compose up --build          → doit demarrer sans erreur
> 2. docker compose exec api pytest -v  → si des tests existent, 100% pass
> 3. Tester les endpoints via curl ou httpx → les routes creees/modifiees repondent
> 4. docker compose logs web            → pas d'erreur de compilation frontend
> ```
> Si un check echoue, corriger AVANT de cocher.

---

## ETAPE 0 : Installation et verification de l'environnement [x]

> **Contexte** : Avant de coder, il faut s'assurer que TOUTES les dependances sont installees sur la machine Windows.
> Cette etape est 100% automatisee : Claude CLI verifie chaque outil et installe ceux qui manquent.
> **Aucune validation Docker requise pour cette etape** (Docker n'est peut-etre pas encore installe).

### Phase 0a : Verifier et installer les outils systeme

- [x] Verifier si Docker Desktop est installe (`docker --version`). Si absent : telecharger et installer Docker Desktop via `winget install Docker.DockerDesktop` (ou guider l'utilisateur si winget indisponible). Verifier que le service Docker tourne (`docker info`). Si WSL2 n'est pas active, executer `wsl --install` et demander un redemarrage.
- [x] Verifier si Docker Compose est disponible (`docker compose version`). Il est inclus dans Docker Desktop, sinon installer via `docker compose` plugin.
- [x] Verifier si Node.js >= 18 est installe (`node --version`). Si absent : installer via `winget install OpenJS.NodeJS.LTS` ou guider l'utilisateur vers nodejs.org.
- [x] Verifier si npm est installe (`npm --version`). Inclus avec Node.js.
- [x] Verifier si Python >= 3.10 est installe (`python --version`). Si absent : installer via `winget install Python.Python.3.12`.
- [x] Verifier si Git est installe (`git --version`). Si absent : installer via `winget install Git.Git`.

### Phase 0b : Verifier les dependances du projet

- [x] Verifier que le fichier `.env` existe a la racine du projet. Si absent, le creer en copiant `.env.example`.
- [x] Verifier que tous les fichiers `__init__.py` necessaires existent dans `backend/app/`, `backend/app/core/`, `backend/app/db/`. Les creer si manquants.
- [x] Verifier que `backend/requirements.txt` contient toutes les dependances Python requises (fastapi, uvicorn, sqlalchemy, psycopg, pydantic, pydantic-settings, pyjwt, passlib, bcrypt, python-multipart, alembic, httpx, boto3, celery, redis, structlog, sentry-sdk).
- [x] Verifier que `frontend/package.json` contient les devDependencies TypeScript (`typescript`, `@types/react`, `@types/node`). Si absentes, les ajouter avec `npm install --save-dev typescript @types/react @types/node`.

### Phase 0c : Lancer l'environnement Docker et valider

- [x] Executer `docker compose up --build -d` et attendre que tous les services demarrent (postgres, redis, minio, mailhog, api, web).
- [x] Verifier que l'API repond : `curl http://localhost:8000/docs` doit retourner la page Swagger.
- [x] Verifier que le frontend repond : `curl http://localhost:3000` doit retourner du HTML.
- [x] Verifier que PostgreSQL est accessible : `docker compose exec postgres pg_isready`.
- [x] Verifier que MinIO est accessible : `curl http://localhost:9001` (console MinIO).
- [x] Verifier que Mailhog est accessible : `curl http://localhost:8025` (interface email).
- [x] Verifier que Redis est accessible : `docker compose exec redis redis-cli ping` doit retourner PONG.
- [x] Si un service echoue, lire les logs (`docker compose logs <service>`) et corriger avant de continuer.

**VALIDATION ETAPE 0** : Tous les outils sont installes, Docker tourne, les 6 services sont UP, l'API et le frontend repondent. Afficher un resume de l'environnement a l'utilisateur.

---

## ETAPE 1 : Restructurer le backend en couches [x]

> **Contexte** : Actuellement tout le code backend est dans `backend/app/api.py` (routes + logique).
> Il faut separer en couches propres : routers / schemas / services / repositories.
> **Fichiers a lire** : `backend/app/api.py`, `backend/app/models.py`, `backend/app/main.py`
> **Spec de reference** : `docs/specs/03_Architecture_Logicielle_Technique_OptiFlow_AI.md`

- [x] Creer les dossiers vides dans `backend/app/` : `api/routers/`, `services/`, `domain/schemas/`, `repositories/`
- [x] Creer `backend/app/api/routers/__init__.py` et `backend/app/api/__init__.py`
- [x] Creer `domain/schemas/auth.py` avec les modeles Pydantic : `LoginRequest(email, password)`, `TokenResponse(access_token, token_type, role)`
- [x] Creer `domain/schemas/cases.py` : `CaseCreate(first_name, last_name, phone?, email?, source?)`, `CaseResponse(id, customer_name, status, source, created_at)`, `CaseDetail` avec customer + documents + payments
- [x] Creer `domain/schemas/documents.py` : `DocumentResponse(id, type, filename, uploaded_at)`
- [x] Creer `domain/schemas/payments.py` : `PaymentResponse(id, payer_type, amount_due, amount_paid, status)`, `PaymentSummary(total_due, total_paid, remaining, items)`
- [x] Creer `domain/schemas/dashboard.py` : `DashboardSummary(cases_count, documents_count, alerts_count, total_due, total_paid, remaining)`
- [x] Creer `repositories/user_repo.py` : `get_user_by_email(db, email) -> User | None`
- [x] Creer `repositories/case_repo.py` : `list_cases(db)`, `get_case(db, id)`, `create_case(db, customer, source)`
- [x] Creer `repositories/document_repo.py` : `list_by_case(db, case_id)`, `create_document(db, case_id, type, filename, storage_key)`
- [x] Creer `repositories/payment_repo.py` : `list_by_case(db, case_id)`, `get_summary(db, case_id)`
- [x] Creer `services/auth_service.py` : `authenticate(db, email, password) -> TokenResponse` (appelle le repo + security.py)
- [x] Creer `services/case_service.py` : `list_cases(db)`, `get_case_detail(db, id)`, `create_case(db, payload)` (appelle les repos)
- [x] Creer `services/document_service.py` : `list_documents(db, case_id)`, `upload_document(db, case_id, file)`
- [x] Creer `services/payment_service.py` : `get_payment_summary(db, case_id)`
- [x] Creer `services/dashboard_service.py` : `get_summary(db) -> DashboardSummary`
- [x] Creer `api/routers/auth.py` : route `POST /auth/login` qui appelle `auth_service.authenticate()`
- [x] Creer `api/routers/cases.py` : routes `GET /cases`, `POST /cases`, `GET /cases/{id}` qui appellent `case_service`
- [x] Creer `api/routers/documents.py` : routes `GET /cases/{id}/documents`, `POST /cases/{id}/documents`
- [x] Creer `api/routers/payments.py` : route `GET /cases/{id}/payments`
- [x] Creer `api/routers/dashboard.py` : route `GET /dashboard/summary`
- [x] Modifier `main.py` : remplacer `include_router(router)` de api.py par les 5 nouveaux routers
- [x] Supprimer l'ancien fichier `backend/app/api.py`
- [x] Verifier : `docker compose up --build` demarre sans erreur, toutes les routes repondent comme avant

---

## ETAPE 2 : Gestion d'erreurs et logging [x]

> **Contexte** : Aucun logging, aucune exception metier. Les erreurs remontent en HTTP 500 generique.
> **Fichiers a lire** : `backend/app/main.py`, les services crees a l'etape 1
> **Spec de reference** : `docs/specs/03_Architecture_Logicielle_Technique_OptiFlow_AI.md` (section logging)

- [x] Creer `backend/app/core/exceptions.py` : classes `BusinessError(message, code)`, `NotFoundError(entity, id)`, `AuthenticationError(message)`, `ValidationError(field, message)` — toutes heritent de BusinessError
- [x] Creer `backend/app/core/logging.py` : configurer le logging Python en format JSON (structlog ou logging standard). Fonctions `get_logger(name)` qui retourne un logger avec contexte
- [x] Ajouter dans `main.py` un exception handler FastAPI global : `@app.exception_handler(BusinessError)` qui retourne des reponses JSON propres avec status code adapte (404 pour NotFound, 401 pour Auth, 422 pour Validation, 500 pour le reste)
- [x] Modifier tous les services pour lever les exceptions metier au lieu de HTTPException : par ex. `raise NotFoundError("case", case_id)` au lieu de `raise HTTPException(404)`
- [x] Ajouter un log `info` a chaque operation reussie dans les services (creation, lecture) et `error` a chaque echec
- [x] Verifier : les endpoints retournent des erreurs JSON propres quand on passe des IDs inexistants

---

## ETAPE 3 : Alembic et migrations [x]

> **Contexte** : Actuellement `main.py` fait `Base.metadata.create_all()` a chaque demarrage. Pas de versioning du schema.
> **Fichiers a lire** : `backend/app/models.py`, `backend/app/db/base.py`, `backend/app/db/session.py`, `backend/app/main.py`
> **Spec de reference** : `docs/specs/20_Schema_SQL_Initial_OptiFlow_AI.md`

- [x] Ajouter `alembic` dans `backend/requirements.txt`
- [x] Dans le container api, executer `alembic init alembic` pour creer la structure dans `backend/alembic/`
- [x] Modifier `backend/alembic/env.py` : importer `settings.DATABASE_URL` depuis `core/config.py`, importer `Base` depuis `db/base.py` et tous les modeles, configurer `target_metadata = Base.metadata`
- [x] Modifier `backend/alembic.ini` : mettre `sqlalchemy.url` en commentaire (sera surcharge par env.py)
- [x] Generer la migration initiale : `alembic revision --autogenerate -m "initial_5_tables"`
- [x] Supprimer la ligne `Base.metadata.create_all(bind=engine)` de `main.py` (ou la commenter)
- [x] Modifier le script de demarrage ou le Dockerfile pour executer `alembic upgrade head` avant le lancement de l'API
- [x] Tester : supprimer le volume postgres (`docker compose down -v`), relancer (`docker compose up --build`), verifier que les tables sont creees par Alembic

---

## ETAPE 4 : Auth complete avec refresh token et RBAC [x]

> **Contexte** : Le login retourne un JWT mais il n'y a pas de refresh, pas de logout, et les routes ne sont pas protegees.
> **Fichiers a lire** : `backend/app/security.py`, `backend/app/api/routers/auth.py`, `backend/app/models.py`

- [x] Ajouter un modele SQLAlchemy `RefreshToken` dans `models.py` : id, token (unique), user_id (FK), expires_at, revoked (bool), created_at
- [x] Generer une migration Alembic : `alembic revision --autogenerate -m "add_refresh_tokens"`
- [x] Modifier `security.py` : ajouter `create_refresh_token(user_id) -> str` et `verify_refresh_token(db, token) -> User`
- [x] Modifier `auth_service.authenticate()` : retourner access_token + refresh_token
- [x] Modifier le schema `TokenResponse` : ajouter le champ `refresh_token`
- [x] Creer `POST /api/v1/auth/refresh` dans le router auth : prend un refresh_token, retourne un nouvel access_token
- [x] Creer `POST /api/v1/auth/logout` dans le router auth : revoque le refresh_token
- [x] Creer `backend/app/core/deps.py` : dependency `get_current_user(token: str = Depends(oauth2_scheme)) -> User` qui decode le JWT et charge le user
- [x] Creer dans `deps.py` : dependency factory `require_role(*roles)` qui verifie que le user a l'un des roles autorises
- [x] Proteger toutes les routes sauf login/refresh avec `Depends(get_current_user)`
- [x] Proteger la route dashboard avec `Depends(require_role("admin", "manager"))`
- [x] Mettre a jour les tests si existants, sinon noter que les tests viendront a l'etape 5
- [x] Verifier : un appel sans token retourne 401, un appel avec token valide fonctionne

---

## ETAPE 5 : Tests backend [x]

> **Contexte** : Aucun test n'existe. Il faut mettre en place pytest et ecrire les tests pour tout ce qui a ete cree aux etapes 1-4.
> **Fichiers a lire** : tous les services, routers, et le fichier `backend/requirements.txt`

- [x] Ajouter dans `requirements.txt` : `pytest`, `httpx`, `pytest-asyncio`
- [x] Creer `backend/tests/__init__.py`
- [x] Creer `backend/tests/conftest.py` : fixture qui cree une BDD SQLite in-memory, fixture `client` qui retourne un `httpx.AsyncClient` pointe sur l'app FastAPI de test, fixture `auth_headers` qui fait un login et retourne les headers avec le token
- [x] Creer `backend/tests/test_auth.py` : test login OK, test login mauvais email (401), test login mauvais password (401), test refresh token, test logout, test acces sans token (401)
- [x] Creer `backend/tests/test_cases.py` : test creation dossier, test liste dossiers, test detail dossier, test dossier inexistant (404)
- [x] Creer `backend/tests/test_documents.py` : test liste documents d'un dossier, test upload
- [x] Creer `backend/tests/test_payments.py` : test summary paiements
- [x] Creer `backend/tests/test_dashboard.py` : test endpoint summary retourne les bons champs
- [x] Executer `pytest -v` dans le container et verifier que tous les tests passent
- [x] Si des tests echouent, corriger les services/routers concernes puis relancer

---

## ETAPE 6 : Frontend - design system, auth, navigation et formulaires [x]

> **Contexte** : Le frontend affiche des donnees mais n'a pas de design system, pas de login, pas de navigation, pas de formulaires.
> **IMPORTANT** : Lire attentivement la section "CHARTE FRONTEND" de CLAUDE.md AVANT de commencer. Chaque composant, chaque page doit respecter les 10 principes UX, les tokens visuels, et les patterns de page obligatoires.
> **Fichiers a lire** : `frontend/src/app/page.tsx`, `frontend/src/lib/api.ts`, `frontend/src/app/layout.tsx`, section "CHARTE FRONTEND" de `CLAUDE.md`
> **Spec de reference** : `docs/specs/16_Plan_Ecrans_Frontend_OptiFlow_AI.md`, `docs/specs/05_Cadrage_Frontend_Premium_OptiFlow_AI.md`

### 6a. Setup du design system (FAIRE EN PREMIER)
- [x] Installer Tailwind CSS, shadcn/ui, Lucide React, Recharts : `npx shadcn@latest init`, `npm install tailwindcss @tailwindcss/forms lucide-react recharts clsx tailwind-merge class-variance-authority`
- [x] Configurer `tailwind.config.ts` avec les tokens de couleurs definis dans CLAUDE.md (primary, success, warning, danger, etc.)
- [x] Installer les composants shadcn/ui de base : `npx shadcn@latest add button card badge dialog table tabs input select dropdown-menu toast tooltip avatar separator sheet`
- [x] Creer `frontend/src/lib/utils.ts` : fonction `cn()` pour merger les classes Tailwind (clsx + tailwind-merge)
- [x] Creer `frontend/src/lib/format.ts` : fonctions de formatage : `formatMoney(amount) -> "1 234,56 €"`, `formatDate(date) -> "03 avr. 2026"`, `formatPercent(value) -> "85,3%"`, `formatPhone(phone) -> "06 12 34 56 78"`

### 6b. Composants reutilisables (OBLIGATOIRE AVANT de faire les pages)
- [x] Creer `components/layout/Sidebar.tsx` : sidebar sombre (gray-900) avec logo OptiFlow AI, items de navigation avec icones Lucide, badges compteurs, item actif avec bordure bleue, mode collapse en icones seules (64px). Items : Actions, Dashboard, Dossiers, Clients (+ Devis, Factures, PEC, Paiements, Relances, Marketing a ajouter dans les etapes suivantes)
- [x] Creer `components/layout/Header.tsx` : hauteur 64px, fond blanc, breadcrumb a gauche, barre de recherche globale au centre (SearchInput avec debounce 300ms), icone notifications (cloche + badge rouge unread count) + avatar utilisateur + menu dropdown (profil, deconnexion) a droite
- [x] Creer `components/layout/PageLayout.tsx` : wrapper de page qui gere : titre, description, breadcrumb, boutons d'action, contenu. Integre automatiquement Sidebar + Header
- [x] Creer `components/ui/EmptyState.tsx` : illustration SVG legere + titre + description + bouton CTA. Messages en francais.
- [x] Creer `components/ui/LoadingState.tsx` : skeleton loader anime (pas un simple spinner) avec texte de chargement en francais
- [x] Creer `components/ui/ErrorState.tsx` : icone erreur + message humain en francais + bouton "Reessayer"
- [x] Creer `components/ui/StatusBadge.tsx` : badge colore selon le statut metier (utiliser STATUS_COLORS de CLAUDE.md). Props : status, size
- [x] Creer `components/ui/MoneyDisplay.tsx` : montant formate "1 234,56 €", vert si positif/paye, rouge si negatif/du, gras si montant principal
- [x] Creer `components/ui/DateDisplay.tsx` : date formatee en francais ("03 avr. 2026"), format relatif optionnel ("il y a 3 jours")
- [x] Creer `components/ui/KPICard.tsx` : carte KPI avec icone Lucide, valeur principale (grande), label, tendance (+12% en vert ou -5% en rouge), bordure de couleur en haut
- [x] Creer `components/ui/DataTable.tsx` : tableau premium avec tri par colonne, pagination integree, etats (loading skeleton, vide, erreur), ligne cliquable, actions par ligne (menu dropdown)
- [x] Creer `components/ui/ConfirmDialog.tsx` : modale de confirmation avec titre, message, boutons Annuler/Confirmer, variante danger (fond rouge)
- [x] Creer `components/ui/FileUpload.tsx` : zone drag & drop avec bordure pointillee, icone upload, texte "Glissez vos fichiers ici ou cliquez pour parcourir", preview du fichier, barre de progression
- [x] Creer `components/ui/SearchInput.tsx` : input avec icone loupe, debounce 300ms, bouton clear, placeholder configurable
- [x] Creer `components/ui/Toast.tsx` : systeme de toasts en haut a droite avec 4 variantes (succes vert, erreur rouge, warning ambre, info bleu), auto-dismiss apres 5s, icone + message en francais

### 6c. Auth et navigation
- [x] Creer `frontend/src/lib/auth.ts` : fonctions `login(email, password)`, `logout()`, `refreshToken()`, `getToken()`, `isAuthenticated()`. Stocker le token dans un cookie httpOnly
- [x] Modifier `frontend/src/lib/api.ts` : ajouter automatiquement le header `Authorization: Bearer <token>` sur chaque requete. Si 401, tenter un refresh puis redirect /login si echec. Ajouter un intercepteur d'erreur global qui affiche un Toast en cas d'echec reseau
- [x] Creer `frontend/src/app/login/page.tsx` : page plein ecran avec fond gradient doux, carte centree avec logo OptiFlow AI, formulaire email + password, bouton "Se connecter" avec loading state, message d'erreur inline ("Email ou mot de passe incorrect"), redirect vers /actions apres succes
- [x] Modifier `frontend/src/app/layout.tsx` : integrer le layout Sidebar + Header + contenu sur toutes les pages sauf /login. Le layout doit wrapper toutes les pages authentifiees.
- [x] Creer `frontend/src/middleware.ts` : middleware Next.js qui redirige vers /login si pas de token, sauf pour la page /login elle-meme

### 6d. Premieres pages (avec les bons patterns)
- [x] Creer `frontend/src/app/actions/page.tsx` : **File d'actions** — page d'accueil par defaut. Affiche un message de bienvenue ("Bonjour {prenom}, voici vos priorites du jour"), puis les actions groupees par categorie avec compteurs. Pour le MVP, afficher : dossiers recents, KPIs rapides. Sera enrichie avec les vraies action_items a l'ETAPE 10.
- [x] Modifier `frontend/src/app/dashboard/page.tsx` : refaire les 6 KPIs avec les composants KPICard, ajouter une mise en page en grid (3 colonnes), ajouter les etats loading/erreur/vide
- [x] Modifier `frontend/src/app/cases/page.tsx` : remplacer par DataTable avec colonnes (ID, Client, Statut, Source, Date, Docs manquants), StatusBadge pour le statut, ligne cliquable, SearchInput, pagination
- [x] Creer `frontend/src/app/cases/new/page.tsx` : formulaire creation dossier dans une Card, champs (nom*, prenom*, telephone, email, source), validation temps reel, barre d'action sticky "Annuler / Creer le dossier", toast de succes, redirect vers le detail
- [x] Modifier `frontend/src/app/cases/[id]/page.tsx` : refaire avec layout a onglets (Resume, Documents, Finances, Historique), en-tete avec 4 KPICards, bouton "Ajouter un document" avec FileUpload, etats loading/erreur pour chaque onglet
- [x] Verifier visuellement : la navigation complete fonctionne (login -> actions -> dashboard -> dossiers -> detail -> retour), les composants respectent les tokens visuels, les etats loading/erreur/vide sont presents PARTOUT, tous les textes sont en francais

---

## ETAPE 7 : Gestion clients complete [x]

> **Contexte** : Les clients sont crees uniquement via la creation de dossier. Il faut un module client autonome.
> **Fichiers a lire** : `backend/app/models.py` (modele Customer), `backend/app/domain/schemas/cases.py`
> **Spec de reference** : `docs/specs/10_Modele_Donnees_Detaille_OptiFlow_AI.md`

- [x] Creer une migration Alembic pour enrichir la table customers : ajouter `address`, `city`, `postal_code`, `social_security_number`, `notes`, `updated_at`
- [x] Creer `domain/schemas/clients.py` : `ClientCreate`, `ClientUpdate`, `ClientResponse`, `ClientSearch(query, page, page_size)`
- [x] Creer `repositories/client_repo.py` : `search(db, query, page, size)`, `get_by_id(db, id)`, `create(db, data)`, `update(db, id, data)`, `delete(db, id)`
- [x] Creer `services/client_service.py` : logique metier pour chaque operation, avec validation et audit. Integrer `event_service.emit_event()` si disponible (ETAPE 10) : ClientCree, ClientModifie, ClientSupprime — sinon, prevoir les hooks pour ajout ulterieur
- [x] Creer `api/routers/clients.py` : `GET /api/v1/clients` (recherche paginee), `GET /api/v1/clients/{id}`, `POST /api/v1/clients`, `PUT /api/v1/clients/{id}`, `DELETE /api/v1/clients/{id}`
- [x] Enregistrer le router dans `main.py`
- [x] Frontend : creer `app/clients/page.tsx` (liste paginee avec barre de recherche)
- [x] Frontend : creer `app/clients/[id]/page.tsx` (fiche client avec ses dossiers)
- [x] Frontend : creer `app/clients/new/page.tsx` (formulaire creation client)
- [x] Ajouter le lien "Clients" dans la Navbar
- [x] Ecrire les tests pour le CRUD clients dans `tests/test_clients.py`
- [x] Verifier : CRUD complet fonctionne via Swagger ET via le frontend

---

## ETAPE 8 : Integration MinIO (stockage documents reel) [x]

> **Contexte** : L'upload de documents stocke juste le nom de fichier. Il faut connecter MinIO pour le vrai stockage S3.
> **Fichiers a lire** : `backend/app/services/document_service.py`, `docker-compose.yml`, `.env.example`

- [x] Ajouter `boto3` dans `requirements.txt`
- [x] Creer `backend/app/integrations/storage.py` : classe `StorageAdapter` avec methodes `upload_file(bucket, key, file_data) -> str`, `get_download_url(bucket, key, expires) -> str`, `delete_file(bucket, key)`, `ensure_bucket(bucket)`
- [x] Ajouter dans `core/config.py` les settings : S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET
- [x] Modifier le demarrage de l'app (`main.py` ou event startup) pour appeler `storage.ensure_bucket()` au boot
- [x] Modifier `services/document_service.py` : `upload_document()` envoie le fichier vers MinIO et stocke la cle S3 dans `storage_key`
- [x] Creer un endpoint `GET /api/v1/documents/{id}/download` qui genere une URL signee MinIO et redirige
- [x] Frontend : remplacer le nom de fichier par un lien cliquable qui telecharge via l'endpoint download
- [x] Tester : uploader un fichier via le frontend, verifier qu'il apparait dans la console MinIO (localhost:9001), telecharger le fichier

---

## ETAPE 9 : GED avancee et audit trail [x]

> **Contexte** : Les documents sont stockes mais sans categorisation ni suivi de completude.
> **Fichiers a lire** : `backend/app/models.py`, `backend/app/services/document_service.py`
> **Spec de reference** : `docs/specs/09_Spec_GED_Cosium_Documents_OptiFlow_AI.md`

- [x] Creer une migration pour la table `document_types` : id, code, label, category, is_required, applies_to_case_type
- [x] Seeder les types de documents : ordonnance, devis_signe, attestation_mutuelle, consentement_rgpd, facture, bon_livraison, certificat_conformite
- [x] Modifier le modele Document pour ajouter `document_type_id` (FK vers document_types)
- [x] Creer un endpoint `GET /api/v1/cases/{id}/completeness` : retourne la liste des types requis, lesquels sont presents, lesquels manquent
- [x] Frontend : afficher une checklist de completude sur la page detail dossier (vert = present, rouge = manquant)
- [x] Frontend : ajouter un badge sur la liste des dossiers (nombre de pieces manquantes)
- [x] Creer la migration pour la table `audit_logs` : id, user_id, action (enum: create/update/delete), entity_type, entity_id, old_value (JSON nullable), new_value (JSON nullable), created_at
- [x] Creer `services/audit_service.py` : `log_action(db, user_id, action, entity_type, entity_id, old_value=None, new_value=None)`
- [x] Integrer `audit_service.log_action()` dans les services : case (create, update), document (upload, delete), client (create, update, delete), payment (create)
- [x] Creer `api/routers/audit.py` : `GET /api/v1/audit-logs` avec filtres (entity_type, entity_id, user_id, date_from, date_to), protege par role admin
- [x] Tests pour completeness et audit
- [x] Verifier : creer un dossier, uploader 2 documents, consulter la completude, consulter les audit logs

---

## ETAPE 10 : Notifications, file d'actions et evenements metier [x]

> **Contexte** : Aucun systeme de notifications ni de file d'actions. L'utilisateur doit tout verifier manuellement.
> Le plan ecrans prevoit une "File d'actions" comme page d'accueil principale.
> L'architecture prevoit des evenements metier (DossierCree, DevisSigne, PaiementRecu, etc.) pour alimenter notifications, dashboards, et automatisations.
> **Spec de reference** : `docs/specs/16_Plan_Ecrans_Frontend_OptiFlow_AI.md`, `docs/specs/03_Architecture_Logicielle_Technique_OptiFlow_AI.md`

- [x] Creer la migration pour la table `notifications` : id, user_id (FK), type (enum: info/warning/action/success), title, message, entity_type (nullable), entity_id (nullable), is_read (bool, default false), created_at
- [x] Creer la migration pour la table `action_items` : id, user_id (FK), type (enum: dossier_incomplet/paiement_retard/pec_attente/relance_faire/devis_expiration), title, description, entity_type, entity_id, priority (enum: low/medium/high/critical), status (enum: pending/done/dismissed), due_date (nullable), created_at
- [x] Creer `domain/schemas/notifications.py` : `NotificationResponse`, `ActionItemResponse`, `ActionItemUpdate`
- [x] Creer `repositories/notification_repo.py` : `list_by_user(db, user_id, unread_only)`, `mark_read(db, id)`, `mark_all_read(db, user_id)`, `create(db, data)`
- [x] Creer `repositories/action_item_repo.py` : `list_by_user(db, user_id, status, priority)`, `create(db, data)`, `update_status(db, id, status)`
- [x] Creer `services/notification_service.py` : `notify(db, user_id, type, title, message, entity_type?, entity_id?)`, `get_unread_count(db, user_id)`
- [x] Creer `services/action_item_service.py` : `generate_action_items(db, user_id)` qui scanne les dossiers incomplets, paiements en retard, PEC en attente, devis expirant, et cree/met a jour les action_items correspondants
- [x] Creer `services/event_service.py` : `emit_event(db, event_type, entity_type, entity_id, user_id, data)` — bus d'evenements interne qui cree des notifications et action_items selon le type d'evenement
- [x] Integrer `event_service.emit_event()` dans les services existants : case_service (DossierCree), document_service (DocumentAjoute), devis_service (DevisSigne — a integrer quand l'etape 11 sera faite), payment_service (PaiementRecu)
- [x] Creer `api/routers/notifications.py` : `GET /api/v1/notifications` (liste paginee), `PATCH /api/v1/notifications/{id}/read`, `PATCH /api/v1/notifications/read-all`, `GET /api/v1/notifications/unread-count`
- [x] Creer `api/routers/action_items.py` : `GET /api/v1/action-items` (liste avec filtres priority/status), `PATCH /api/v1/action-items/{id}` (changer status: done/dismissed), `POST /api/v1/action-items/refresh` (regenerer les items)
- [x] Frontend : creer `app/actions/page.tsx` — **File d'actions** (page d'accueil principale) : liste des actions prioritaires regroupees par type, avec liens directs vers les dossiers/factures/PEC concernes, compteurs par categorie, boutons "Traite" / "Reporter"
- [x] Frontend : ajouter une icone cloche de notifications dans la Navbar avec badge du nombre non lu, dropdown des 5 dernieres notifications au clic
- [x] Frontend : modifier le lien "Dashboard" dans la Navbar pour pointer vers `/actions` comme page d'accueil par defaut
- [x] Tests pour notifications, action items et event service
- [x] Verifier : creer un dossier incomplet, verifier qu'une action item apparait, la marquer comme traitee

---

## ETAPE 11 : Module devis [x]

> **Contexte** : Pas encore de gestion des devis. C'est le premier module financier.
> **Spec de reference** : `docs/specs/06_Spec_Paiements_Rapprochement_OptiFlow_AI.md`, `docs/specs/20_Schema_SQL_Initial_OptiFlow_AI.md`

- [x] Creer une migration pour les tables `devis` (id, case_id, numero, status, montant_ht, tva, montant_ttc, part_secu, part_mutuelle, reste_a_charge, created_at, updated_at) et `devis_lignes` (id, devis_id, designation, quantite, prix_unitaire_ht, taux_tva, montant_ht, montant_ttc)
- [x] Creer les modeles SQLAlchemy correspondants dans `models.py`
- [x] Creer `domain/schemas/devis.py` : DevisCreate, DevisLineCreate, DevisResponse, DevisDetail
- [x] Creer `repositories/devis_repo.py` et `services/devis_service.py`
- [x] Logique metier dans le service : calcul automatique des montants (HT, TVA, TTC) depuis les lignes, calcul des parts (secu/mutuelle/reste)
- [x] Workflow de statut : brouillon -> envoye -> signe -> facture -> annule. Valider les transitions autorisees
- [x] Integrer `event_service.emit_event()` sur les transitions cles : DevisCree, DevisEnvoye, DevisSigne, DevisAnnule
- [x] Creer `api/routers/devis.py` : POST /devis, GET /devis, GET /devis/{id}, PUT /devis/{id}, PATCH /devis/{id}/status
- [x] Frontend : creer `app/devis/page.tsx` (liste) et `app/devis/new/page.tsx` (creation avec ajout dynamique de lignes)
- [x] Frontend : creer `app/devis/[id]/page.tsx` (detail avec lignes, montants, boutons changer statut)
- [x] Ajouter "Devis" dans la Navbar
- [x] Tests pour le CRUD devis et le calcul des montants
- [x] Verifier : creer un devis avec 3 lignes, verifier les calculs, changer le statut

---

## ETAPE 12 : Module facturation [x]

> **Contexte** : Les factures sont generees depuis un devis signe.
> **Spec de reference** : `docs/specs/06_Spec_Paiements_Rapprochement_OptiFlow_AI.md`

- [x] Creer une migration pour les tables `factures` (id, case_id, devis_id, numero, date_emission, montant_ht, tva, montant_ttc, status, created_at) et `facture_lignes` (copie des lignes du devis)
- [x] Creer modeles, schemas, repo, service
- [x] Logique metier : quand un devis passe en statut "signe", possibilite de generer une facture avec numerotation sequentielle (F-2026-0001, F-2026-0002...)
- [x] Integrer `event_service.emit_event()` : FactureEmise, FacturePayee
- [x] Creer `api/routers/factures.py` : POST /factures (depuis devis_id), GET /factures, GET /factures/{id}
- [x] Frontend : page liste factures, page detail, lien depuis le devis pour generer la facture
- [x] Ajouter "Factures" dans la Navbar (sidebar)
- [x] Tests
- [x] Verifier : signer un devis, generer la facture, verifier la numerotation

---

## ETAPE 13 : Module PEC (mutuelles / securite sociale) [x]

> **Spec de reference** : `docs/specs/07_Spec_Mutuelles_SecuriteSociale_TiersPayant_OptiFlow_AI.md`

- [x] Creer les migrations pour : `payer_organizations` (id, name, type: mutuelle/secu, code, contact_email), `payer_contracts` (id, organization_id, client_id, numero_adherent), `pec_requests` (id, case_id, organization_id, facture_id, montant_demande, montant_accorde, status, created_at), `pec_status_history` (id, pec_request_id, old_status, new_status, comment, created_at)
- [x] Creer tous les modeles, schemas, repos, services
- [x] Workflow PEC : soumise -> en_attente -> acceptee / refusee / partielle -> cloturee. Chaque changement de statut enregistre dans pec_status_history
- [x] Integrer `event_service.emit_event()` : PECSoumise, PECAcceptee, PECRefusee
- [x] Creer `api/routers/pec.py` : POST /pec, GET /pec, GET /pec/{id}, PATCH /pec/{id}/status, GET /pec/{id}/history
- [x] Creer la table `relances` (id, pec_request_id, type: email/courrier/telephone, date_envoi, contenu, created_by)
- [x] Creer `POST /pec/{id}/relances` : enregistrer une relance manuelle
- [x] Frontend : page tableau de bord PEC avec filtres par statut et organisation, detail avec historique et relances
- [x] Ajouter "PEC / Tiers payant" dans la Navbar (sidebar)
- [x] Tests
- [x] Verifier : creer une PEC, changer son statut, ajouter une relance, voir l'historique

---

## ETAPE 14 : Paiements complets et rapprochement bancaire [x]

> **Spec de reference** : `docs/specs/06_Spec_Paiements_Rapprochement_OptiFlow_AI.md`

- [x] Migration : enrichir `payments` (ajouter mode_paiement, reference_externe, date_paiement, facture_id) et creer `bank_transactions` (id, date, libelle, montant, reference, source_file, reconciled, reconciled_payment_id, created_at)
- [x] Creer `POST /api/v1/paiements` avec cle d'idempotence (header X-Idempotency-Key), ventilation possible sur plusieurs factures
- [x] Integrer `event_service.emit_event()` : PaiementRecu, PaiementRapproche, EcartDetecte
- [x] Creer `POST /api/v1/banking/import-statement` : upload CSV, parsing et insertion des transactions bancaires
- [x] Creer `POST /api/v1/banking/reconcile` : moteur de matching automatique (par montant exact + date proche + reference similaire)
- [x] Creer `GET /api/v1/banking/unmatched` : transactions non rapprochees
- [x] Creer `POST /api/v1/banking/match` : rapprochement manuel (lier une transaction a un paiement)
- [x] Frontend : formulaire enregistrement paiement, page import releve, interface de rapprochement (transactions a gauche, paiements a droite, drag & drop ou boutons)
- [x] Ajouter "Paiements" et "Rapprochement" dans la Navbar (sidebar)
- [x] Tests
- [x] Verifier : importer un releve CSV, voir les transactions, rapprocher automatiquement puis manuellement

---

## ETAPE 15 : Relances automatisees et recouvrement [x]

> **Contexte** : Les relances dans l'etape 13 sont manuelles et limitees aux PEC. Il faut un vrai moteur de relance qui couvre tous les payeurs (clients, mutuelles, secu) avec des plans parametrables, des templates, et une priorisation intelligente.
> **Spec de reference** : `docs/specs/02_Cadrage_Metier_Fonctionnel_OptiFlow_AI.md` (Domaine 8 : Relances & Recouvrement), `docs/specs/07_Spec_Mutuelles_SecuriteSociale_TiersPayant_OptiFlow_AI.md`

- [x] Creer la migration pour la table `reminder_plans` : id, name, payer_type (enum: client/mutuelle/secu), rules_json (conditions de declenchement: nb jours retard, montant minimum, nb relances max), channel_sequence (JSON: ["email", "sms", "courrier", "telephone"]), interval_days, is_active, created_at
- [x] Creer la migration pour la table `reminders` : id, plan_id (FK nullable), target_type (enum: client/payer_organization), target_id, facture_id (FK nullable), pec_request_id (FK nullable), channel (enum: email/sms/courrier/telephone), status (enum: scheduled/sent/delivered/failed/responded), template_used, content, scheduled_at, sent_at, response_notes, created_by, created_at
- [x] Creer la migration pour la table `reminder_templates` : id, name, channel, payer_type, subject (pour email), body (avec variables {{client_name}}, {{montant}}, {{date_echeance}}, {{facture_numero}}), is_default, created_at
- [x] Seeder des templates par defaut : relance email client 1ere, 2eme, 3eme, relance mutuelle, relance secu, SMS de rappel
- [x] Creer `domain/schemas/reminders.py` : `ReminderPlanCreate`, `ReminderPlanResponse`, `ReminderCreate`, `ReminderResponse`, `ReminderTemplateResponse`, `ReminderStats`
- [x] Creer `repositories/reminder_repo.py` : CRUD plans, CRUD reminders, requete des factures en retard par payeur avec jointures
- [x] Creer `services/reminder_service.py` : `get_overdue_items(db, payer_type, min_days)` — liste les factures/PEC en retard avec anciennete et montant, `generate_reminders(db, plan_id)` — applique un plan de relance et cree les reminders, `send_reminder(db, reminder_id)` — envoie via le canal (email/sms), `get_collection_stats(db)` — statistiques de recouvrement (montant relance, montant recouvre, taux de succes)
- [x] Creer `services/collection_prioritizer.py` : `prioritize_overdue(db)` — algorithme de priorisation : score = montant * anciennete_factor * probabilite_recouvrement. Retourne une liste triee avec score, raison, action recommandee
- [x] Integrer `event_service.emit_event()` : RelanceEnvoyee, RelanceEchouee, PaiementApresRelance
- [x] Creer `integrations/email_sender.py` : classe `EmailSender` avec methode `send_email(to, subject, body_html)` utilisant `smtplib` vers Mailhog (SMTP config dans .env : MAILHOG_SMTP_HOST, MAILHOG_SMTP_PORT). Ce module sera reutilise par l'etape Marketing
- [x] Integrer avec `integrations/email_sender.py` pour l'envoi des emails de relance
- [x] Creer `api/routers/reminders.py` : `GET /api/v1/reminders/overdue` (factures en retard avec priorisation), `GET /api/v1/reminders/plans` (CRUD plans), `POST /api/v1/reminders/plans/{id}/execute` (declencher un plan), `GET /api/v1/reminders` (historique relances), `POST /api/v1/reminders` (relance manuelle), `GET /api/v1/reminders/stats` (statistiques recouvrement)
- [x] Creer une tache Celery `tasks/reminder_tasks.py` : `auto_generate_reminders()` — execute chaque jour, applique les plans actifs aux factures en retard, cree et envoie les relances automatiquement
- [x] Frontend : creer `app/reminders/page.tsx` — tableau de bord recouvrement avec : balance agee (0-30j, 30-60j, 60-90j, 90j+), liste priorisee des relances a faire, historique des relances envoyees, statistiques de recouvrement
- [x] Frontend : creer `app/reminders/plans/page.tsx` — gestion des plans de relance (CRUD, activation/desactivation)
- [x] Frontend : creer `app/reminders/templates/page.tsx` — edition des templates de relance avec preview
- [x] Ajouter "Relances" dans la Navbar
- [x] Tests pour le moteur de priorisation, la generation de relances, et les statistiques
- [x] Verifier : configurer un plan, creer des factures en retard, executer le plan, verifier que les relances sont creees et envoyees

---

## ETAPE 16 : Marketing et CRM [x]

> **Spec de reference** : `docs/specs/08_Spec_Marketing_CRM_OptiFlow_AI.md`

- [x] Creer les migrations pour : `marketing_consents` (id, client_id, channel: email/sms/courrier, consented: bool, consented_at, revoked_at, source), `segments` (id, name, description, rules_json, created_at), `segment_memberships` (segment_id, client_id), `campaigns` (id, name, segment_id, channel: email/sms, template, status, scheduled_at, sent_at, created_at), `message_logs` (id, campaign_id, client_id, channel, status: sent/delivered/failed/opened/clicked, sent_at)
- [x] Creer les modeles, schemas, repos, services
- [x] Creer `services/consent_service.py` : `grant_consent(db, client_id, channel, source)`, `revoke_consent(db, client_id, channel)`, `check_consent(db, client_id, channel) -> bool` — **RGPD : ne jamais envoyer sans consentement valide**
- [x] Moteur de segmentation : evaluer les regles JSON (age, derniere visite, montant depense, ville, type mutuelle, consentement actif) pour construire la liste de membres d'un segment. **Filtrer automatiquement les clients sans consentement pour le canal choisi**
- [x] Creer `api/routers/marketing.py` : CRUD segments, CRUD campaigns, GET /campaigns/{id}/stats
- [x] Creer `api/routers/consents.py` : `GET /api/v1/clients/{id}/consents`, `PUT /api/v1/clients/{id}/consents/{channel}` (grant/revoke)
- [x] Integration email : reutiliser `integrations/email_sender.py` (cree a l'ETAPE 15). Si necessaire, enrichir avec methode `send_bulk_email()` pour les campagnes
- [x] Creer `POST /campaigns/{id}/send` : envoie les emails/sms aux membres du segment qui ont le consentement, enregistre dans message_logs
- [x] Integrer `event_service.emit_event()` : CampagneLancee, CampagneTerminee
- [x] Frontend : page segments (creation, edition des regles), page campagnes (creation, envoi, statistiques d'envoi avec taux d'ouverture/clic)
- [x] Frontend : dans la fiche client, ajouter une section "Consentements marketing" avec toggles par canal
- [x] Ajouter "Marketing" dans la Navbar (sidebar)
- [x] Tests
- [x] Verifier : creer un segment, creer une campagne, l'envoyer, verifier dans Mailhog (localhost:8025) que les emails sont recus

---

## ETAPE 17 : Connecteur Cosium API [x]

> **Contexte** : OptiFlow doit synchroniser les donnees depuis l'ERP Cosium.
> **Fichiers a lire** : `docs/cosium/BASE_CONNAISSANCES_COSIUM.md`, tous les PDFs dans `docs/cosium/`, section "SECURITE COSIUM" de `CLAUDE.md`
> **IMPORTANT** : Les appels Cosium passent par le backend (proxy), JAMAIS depuis le frontend (CORS desactive).
>
> ⛔ **REGLE ABSOLUE — LECTURE SEULE** :
> - Le `CosiumClient` ne doit avoir QUE deux methodes : `authenticate()` (POST auth uniquement) et `get()` (GET uniquement)
> - **INTERDIT** : put(), post() (sauf auth), delete(), patch(), ou toute methode generique avec methode HTTP variable
> - **INTERDIT** : Tout appel PUT/POST/DELETE/PATCH vers c1.cosium.biz
> - **INTERDIT** : Implementer les endpoints PUT /customers/subscribed-to-* ou unsubscribed-from-*
> - La synchronisation est UNIDIRECTIONNELLE : Cosium → OptiFlow. Jamais l'inverse.

- [x] Creer `backend/app/integrations/cosium/__init__.py`
- [x] Creer `integrations/cosium/client.py` : classe `CosiumClient` avec UNIQUEMENT `authenticate(tenant, login, password) -> token` (seul POST autorise) et `get(endpoint, params) -> dict` (requetes GET, parsing HAL, pagination). **PAS de methode put/post/delete/patch.**
- [x] Creer `integrations/cosium/adapter.py` : fonctions de mapping `cosium_customer_to_optiflow(data) -> ClientCreate`, `cosium_invoice_to_optiflow(data) -> dict`, `cosium_product_to_optiflow(data) -> dict`
- [x] Ajouter les settings Cosium dans `core/config.py` : COSIUM_TENANT, COSIUM_LOGIN, COSIUM_PASSWORD, COSIUM_BASE_URL
- [x] Creer `services/sync_service.py` : `sync_customers(db)` qui appelle GET /customers, mappe et upsert dans la BDD OptiFlow. Idem `sync_invoices(db)`, `sync_products(db)`. **Aucune ecriture vers Cosium.**
- [x] Creer `api/routers/sync.py` : `POST /api/v1/sync/customers`, `POST /api/v1/sync/invoices`, `POST /api/v1/sync/products` (declenchement manuel, protege admin). Ces POST sont vers l'API OptiFlow, PAS vers Cosium.
- [x] Ajouter Celery + Redis dans `requirements.txt` et configurer le worker dans `docker-compose.yml`
- [x] Creer `backend/app/worker.py` : taches Celery pour la synchronisation periodique (lecture Cosium → ecriture OptiFlow uniquement)
- [x] Frontend : page admin avec boutons de sync manuelle et statut de la derniere synchro
- [x] Tests avec mock du client Cosium (ne pas appeler l'API reelle dans les tests)
- [x] **Test de securite** : ecrire un test qui verifie que le `CosiumClient` n'a PAS de methode `put`, `post` (sauf authenticate), `delete`, `patch`. Verifier qu'aucun appel HTTP autre que GET (+ POST auth) ne part vers Cosium.
- [x] Verifier : lancer une sync manuelle, verifier que les clients Cosium apparaissent dans OptiFlow

---

## ETAPE 18 : Dashboard avance et KPIs metier [x]

> **Contexte** : Le dashboard actuel (ETAPE 1) est basique — 6 KPIs statiques. Les specs demandent un veritable tableau de pilotage avec des graphiques temps reel, une balance agee, des indicateurs financiers et operationnels avances.
> **Spec de reference** : `docs/specs/01_Vision_Produit_OptiFlow_AI.md` (section KPIs), `docs/specs/02_Cadrage_Metier_Fonctionnel_OptiFlow_AI.md` (Domaine Pilotage), `docs/specs/16_Plan_Ecrans_Frontend_OptiFlow_AI.md`

- [x] Creer `services/analytics_service.py` avec les fonctions suivantes :
  - `get_financial_kpis(db, date_from, date_to)` : CA total, montant facture, montant encaisse, reste a encaisser, taux de recouvrement
  - `get_aging_balance(db)` : balance agee des creances par tranche (0-30j, 30-60j, 60-90j, 90j+) et par type de payeur (client, mutuelle, secu)
  - `get_payer_performance(db)` : temps moyen de paiement par mutuelle/secu, taux d'acceptation PEC, taux de rejet, montant moyen des ecarts
  - `get_operational_kpis(db)` : taux de dossiers complets, nombre de dossiers en cours, delai moyen creation-paiement, nombre de pieces manquantes
  - `get_commercial_kpis(db)` : nombre de devis en cours, taux de conversion devis→facture, panier moyen, CA par periode (jour/semaine/mois)
  - `get_marketing_kpis(db)` : campagnes actives, taux d'ouverture moyen, CA genere par campagne, cout par conversion
- [x] Creer `domain/schemas/analytics.py` : `FinancialKPIs`, `AgingBalance`, `PayerPerformance`, `OperationalKPIs`, `CommercialKPIs`, `MarketingKPIs`, `DashboardFull`
- [x] Creer `api/routers/analytics.py` : `GET /api/v1/analytics/financial`, `GET /api/v1/analytics/aging`, `GET /api/v1/analytics/payers`, `GET /api/v1/analytics/operational`, `GET /api/v1/analytics/commercial`, `GET /api/v1/analytics/marketing`, `GET /api/v1/analytics/dashboard` (tout en un avec filtres date_from, date_to, site_id)
- [x] Proteger les routes analytics avec `require_role("admin", "manager")`
- [x] Frontend : installer `recharts` (deja dispo en React) pour les graphiques
- [x] Frontend : creer `app/dashboard/page.tsx` (remplacer l'ancien) avec :
  - Barre de filtres en haut (periode : aujourd'hui / semaine / mois / trimestre / personnalise)
  - Section KPIs financiers : 4 cards cliquables (CA, encaisse, reste, taux recouvrement)
  - Section graphique : courbe d'evolution du CA et des encaissements sur la periode (recharts LineChart)
  - Section balance agee : tableau colore par tranche avec totaux par payeur (recharts BarChart)
  - Section performance mutuelles : classement des mutuelles par temps de paiement et taux d'acceptation
  - Section operationnelle : dossiers en cours, completude, pipeline devis
  - Section marketing (si campagnes existent) : derniere campagne, taux, CA genere
- [x] Frontend : creer un composant reutilisable `components/KPICard.tsx` (valeur, label, tendance, couleur)
- [x] Frontend : creer un composant `components/AgingTable.tsx` (balance agee avec code couleur)
- [x] Tests pour les calculs d'analytiques (verifier les agregations SQL)
- [x] Verifier : peupler des donnees de test, verifier que tous les KPIs et graphiques s'affichent correctement

---

## ETAPE 19 : Couche IA (copilote et RAG) [x]

> **Spec de reference** : `docs/directives/32_Synthese_Realiste_Copilote_Cosium.docx`, `docs/directives/34_Brief_Maitre_Agent_Codage_Copilote_Cosium.docx`

- [x] Creer `backend/app/integrations/ai/__init__.py`
- [x] Creer `integrations/ai/provider.py` : classe abstraite `AIProvider` avec methode `query(prompt, context) -> str`
- [x] Creer `integrations/ai/claude_provider.py` : implementation avec l'API Anthropic (claude-sonnet ou haiku)
- [x] Ajouter `anthropic` dans `requirements.txt`, ajouter `ANTHROPIC_API_KEY` dans `.env.example` et `config.py`
- [x] Creer `services/ai_service.py` : `copilot_query(db, case_id, question)` qui charge le contexte du dossier (client, documents, paiements, PEC) et envoie au provider IA
- [x] Implementer un RAG basique : charger les 164 pages md de `docs/cosium/pages/` en chunks, recherche par similarite (embeddings ou keyword search simple), injecter les chunks pertinents dans le prompt
- [x] Creer 4 modes de copilote :
  - **Copilote Dossier** : resume du dossier, anomalies detectees, prochaines actions, pieces manquantes
  - **Copilote Financier** : suivi paiements, prediction retard, recommandation de relance
  - **Copilote Documentaire** : recherche dans la base Cosium, explication fonctionnalites
  - **Copilote Marketing** : suggestion de segments, recommandation de campagnes
- [x] Creer `api/routers/ai.py` : `POST /api/v1/ai/copilot/query` avec body `{case_id?, question, mode?}`, retourne la reponse de l'IA
- [x] Frontend : ajouter un panneau "Assistant IA" sur la page detail dossier avec un champ question, selection du mode, et une zone de reponse
- [x] Frontend : ajouter un bouton "Demander a l'IA" sur les pages PEC, factures, et relances pour des recommandations contextuelles
- [x] Tests avec mock du provider IA
- [x] Verifier : poser une question sur un dossier, obtenir une reponse contextuelle

---

## ETAPE 20 : Preparation production VPS [x]

> **Contexte** : L'app tourne en local. Il faut preparer le deploiement sur un VPS.

- [x] Creer `docker-compose.prod.yml` : memes services mais sans volumes montes (code copie dans l'image), sans hot-reload, avec `npm run build && npm start` pour le frontend, avec restart: always sur tous les services
- [x] Modifier les Dockerfiles pour un build multi-stage : stage build + stage production optimise
- [x] Creer `.env.production.example` avec toutes les variables requises et des commentaires (JWT_SECRET a changer, DATABASE_URL, etc.)
- [x] Ajouter un service `nginx` dans le docker-compose.prod.yml : reverse proxy vers frontend (3000) et api (8000), config SSL avec Let's Encrypt (certbot)
- [x] Ajouter des health checks Docker sur postgres, redis, api, web
- [x] Creer un script `scripts/backup_db.sh` : pg_dump compresse, rotation des backups (garder 7 jours)
- [x] Ajouter rate limiting sur le endpoint /auth/login (SlowAPI ou middleware custom, max 5 tentatives/minute)
- [x] Configurer la rotation des logs (logrotate ou Docker log driver)
- [x] Creer un script `scripts/deploy.sh` : git pull, docker compose -f docker-compose.prod.yml build, docker compose up -d, alembic upgrade head
- [x] Ecrire un test end-to-end du workflow complet : login -> creer client -> creer dossier -> upload document -> creer devis -> signer -> generer facture -> enregistrer paiement -> verifier dashboard
- [x] Verifier : le workflow e2e passe, le docker-compose.prod.yml demarre correctement

---

## Contexte commercial

OptiFlow AI est commercialise sous **deux modes** :

| Mode | Cible | Fonctionnalites | Prix |
|------|-------|-----------------|------|
| **Solo** | Opticien independant (1 magasin, 1 Cosium) | CRM, GED, devis, factures, PEC, paiements, relances, marketing, IA | 99€/mois + option IA Pro 29€/mois |
| **Reseau** | Groupe de distribution (50+ magasins) | Tout Solo + multi-tenant + dashboard groupe + admin reseau | Sur devis, tarif degressif |

Le code est concu pour supporter les deux modes. Le mode Solo = mode Reseau avec 1 seul tenant.

**Regle de dev supplementaire** : chaque fonctionnalite doit fonctionner en mode Solo ET en mode Reseau. Ne jamais creer de logique "solo-only" — tout passe par le tenant_id.

---

## Tableau de priorites (Etapes 23-30)

| Etape | Contenu | Priorite | Justification |
|-------|---------|----------|---------------|
| 23 | Monitoring Sentry + health check | IMPORTANT | Detecter les bugs avant les clients |
| 24 | Test reel Cosium + preparation demo | CRITIQUE | Prouver que ca marche vraiment |
| 25 | Securite + performance | IMPORTANT | Durcissement avant prod |
| 26 | Multi-tenant MVP | REQUIS | Vendre aux groupes d'opticiens |
| 27 | Onboarding + self-service | REQUIS | Scaler sans intervention manuelle |
| 28 | Facturation Stripe + abonnements | REQUIS | Monetiser le produit |
| 29 | Copilote renouvellement proactif | DIFFERENCIATEUR | IA a valeur business mesurable |
| 30 | Abstraction multi-ERP | STRATEGIQUE | Reduire la dependance Cosium |

---

## ETAPE 21 : Vue client 360° et journal d'interactions [x]

> **Contexte** : La vue client 360° est LA fonctionnalite qui fait la difference au quotidien pour un opticien.
> Un clic sur un client = tout son historique visible : dossiers, devis, factures, paiements, PEC, documents, relances, interactions.
> C'est ce qui vend le logiciel en demo. Sans ca, OptiFlow n'a pas d'avantage visible sur un simple tableur.
> Le journal d'interactions complete la vue 360 : l'opticien note ses appels, emails, visites — tout est trace.
> **Spec de reference** : `docs/specs/02_Cadrage_Metier_Fonctionnel_OptiFlow_AI.md`, `docs/specs/10_Modele_Donnees_Detaille_OptiFlow_AI.md`

### Phase 21a : Table interactions et backend

- [x] Creer la migration Alembic pour la table `interactions`
- [x] Creer `domain/schemas/interactions.py`
- [x] Creer `repositories/interaction_repo.py`
- [x] Creer `services/interaction_service.py`
- [x] Creer `api/routers/interactions.py`

### Phase 21b : Service client 360

- [x] Creer `domain/schemas/client_360.py`
- [x] Creer `services/client_360_service.py`
- [x] Creer `api/routers/client_360.py`

### Phase 21c : Frontend vue 360

- [x] Enrichir `app/clients/[id]/page.tsx` avec layout a onglets complet (Resume, Dossiers, Finances, Documents, Marketing, Historique)
- [x] Creer le composant `InteractionForm.tsx`
- [x] Gerer les 4 etats sur chaque onglet

### Phase 21d : Tests

- [x] `tests/test_interactions.py`
- [x] `tests/test_client_360.py`
- [x] Test frontend vue 360

---

## ETAPE 22 : Exports, RGPD et conformite [x]

> **Contexte** : Un logiciel de gestion professionnel DOIT pouvoir exporter les donnees et respecter le RGPD.
> Les opticiens manipulent des donnees de sante (ordonnances, prescriptions) — la conformite n'est pas optionnelle.
> Les exports sont demandes par TOUS les gerants pour leur comptable, leur expert-comptable, leurs bilans.
> **Spec de reference** : `docs/specs/02_Cadrage_Metier_Fonctionnel_OptiFlow_AI.md`

### Phase 22a : Service d'export

- [x] Ajouter `openpyxl` dans `requirements.txt` pour l'export Excel
- [x] Creer `services/export_service.py`
- [x] Creer `api/routers/exports.py`
- [x] Frontend : bouton "Exporter" sur les pages de liste

### Phase 22b : Conformite RGPD

- [x] Creer `services/gdpr_service.py`
- [x] Creer `api/routers/gdpr.py`
- [x] Integrer `audit_service.log_action()` sur chaque operation RGPD
- [x] Frontend : section RGPD dans la fiche client

### Phase 22c : Tests

- [x] `tests/test_exports.py`
- [x] `tests/test_gdpr.py`
- [x] Verification manuelle exports et RGPD

---

## ETAPE 23 : Monitoring, sante systeme et observabilite [x]

> **Contexte** : Avant de mettre en production, il faut pouvoir detecter les problemes AVANT les clients.
> Sentry pour les erreurs, health check pour le monitoring, metriques pour le pilotage.
> Un client qui tombe sur un bug sans que tu le saches = un client perdu.
> **Spec de reference** : `docs/specs/03_Architecture_Logicielle_Technique_OptiFlow_AI.md`

### Phase 23a : Sentry et error tracking

- [x] Ajouter `sentry-sdk[fastapi]` dans `requirements.txt`
- [x] Ajouter `SENTRY_DSN` dans `.env.example` et `core/config.py` (optionnel, vide par defaut)
- [x] Initialiser Sentry dans `main.py` : `sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1, environment=settings.ENVIRONMENT)` — seulement si SENTRY_DSN est renseigne
- [x] Configurer le middleware Sentry pour capturer les user_id et tenant_id dans les events

### Phase 23b : Health check et metriques

- [x] Creer `api/routers/admin_health.py` :
  - `GET /api/v1/admin/health` (public, pour le load balancer) : retourne `{status: "ok", services: {postgres: {status, response_time_ms}, redis: {status, response_time_ms}, minio: {status, response_time_ms}}}` — ping chaque service avec timeout 5s
  - `GET /api/v1/admin/metrics` (admin only) : nombre d'utilisateurs actifs (derniere heure), nombre de requetes API (derniere heure via audit_logs), jobs celery en attente, espace disque MinIO utilise
- [x] Frontend : dans la page admin, ajouter une section "Sante du systeme" avec indicateurs visuels (vert/rouge par service), temps de reponse, graphique d'activite sur 24h

### Phase 23c : Tests

- [ ] `tests/test_health.py` : verifier que /health retourne OK quand tout tourne, verifier qu'il detecte un service down (mock)
- [ ] Verifier : /admin/health repond, /admin/metrics affiche les compteurs, la page admin frontend affiche les indicateurs

---

## ETAPE 24 : Test reel Cosium et preparation demo [x]

> **Contexte** : ETAPE CRITIQUE. Tout ce qui a ete construit jusqu'ici utilise des donnees seedees.
> Avant de faire une demo a un opticien ou a un partenaire Cosium, il faut prouver que la connexion reelle fonctionne.
> Cette etape necessite un acces a un environnement Cosium reel (sandbox ou compte client).
> **Prerequis** : Obtenir des credentials Cosium de test (demander a Cosium un acces sandbox ou utiliser un compte client volontaire)

### Phase 24a : Validation du connecteur Cosium en conditions reelles

- [x] Configurer les credentials Cosium reels dans `.env` : `COSIUM_BASE_URL`, `COSIUM_TENANT`, `COSIUM_LOGIN`, `COSIUM_PASSWORD`
- [x] Tester `POST /authenticate/basic` : obtenir un token reel, verifier l'expiration, tester le refresh
- [x] Tester `GET /customers` : recuperer la liste des clients reels, verifier le parsing HAL (liens _embedded, pagination _links), verifier que les champs mappes correspondent (nom, prenom, email, tel, date naissance)
- [x] Tester `GET /invoices` : recuperer les factures, verifier les 16 types de documents, verifier les montants et statuts
- [x] Tester `GET /invoiced-items` : recuperer les lignes de facture, verifier le rattachement aux factures
- [x] Tester `GET /products` : recuperer le catalogue produits, verifier EAN/GTIN, prix
- [x] Tester `GET /products/{id}/stock` : verifier les niveaux de stock par site
- [x] Tester `GET /payment-types` : recuperer les moyens de paiement configures
- [x] Documenter les ecarts entre la spec Cosium et la realite (champs manquants, formats inattendus, limites de pagination)

### Phase 24b : Synchronisation complete

- [x] Lancer une sync complete clients Cosium → table customers OptiFlow. Verifier : pas de doublons, mapping correct des champs, gestion des clients sans email/tel
- [x] Lancer une sync complete factures Cosium → table factures OptiFlow. Verifier : montants coherents, statuts mappes correctement, rattachement aux clients
- [x] Lancer une sync produits Cosium → table products OptiFlow (si applicable). Verifier les stocks
- [x] Mesurer les temps de sync : combien de temps pour 1000 clients ? 5000 factures ? Identifier les goulots
- [x] Tester la sync incrementale (delta) : relancer la sync, verifier que seules les nouvelles donnees sont ajoutees/mises a jour

### Phase 24c : Scenario de demo end-to-end

- [x] Preparer un script de demo reproductible (document markdown) :
  1. Login OptiFlow → Dashboard avec KPIs reels (donnees Cosium synchronisees)
  2. Recherche client → Vue 360° avec historique reel (dossiers, factures, paiements depuis Cosium)
  3. Creer un dossier → Upload ordonnance → Creer devis → Generer facture
  4. Consulter le copilote IA dossier → Il resume les infos du client avec contexte Cosium
  5. Lancer une campagne de relance renouvellement → Cibler les clients avec equipement > 2 ans
  6. Dashboard gerant → KPIs de performance, balance agee, taux de recouvrement
- [x] Tester le script de demo 3 fois en conditions reelles. Corriger tout ce qui bloque ou qui est lent (> 3 secondes)
- [x] Preparer un jeu de donnees de demo coherent si l'acces Cosium reel n'est pas disponible : 50 clients, 200 factures, 30 dossiers, 15 devis, des paiements mixtes (a jour, en retard, partiels)

### Phase 24d : Tests

- [ ] `tests/test_cosium_real.py` (marque @pytest.mark.cosium_live, skip par defaut) : teste chaque endpoint Cosium reel avec des assertions sur la structure des reponses
- [ ] `tests/test_sync_integrity.py` : apres une sync complete, verifier que count(customers OptiFlow) == count(customers Cosium), que les montants totaux correspondent
- [ ] Test de demo : executer le script de demo complet sans interruption

---

## ETAPE 25 : Durcissement securite et performance [x]

> **Contexte** : Avant la mise en production reelle, il faut securiser et optimiser.
> Un opticien gere des donnees de sante — la securite n'est pas negociable.
> La performance conditionne l'adoption : si c'est lent, personne ne l'utilisera.
> **Spec de reference** : `docs/specs/03_Architecture_Logicielle_Technique_OptiFlow_AI.md`

### Phase 25a : Securite

- [x] Audit des endpoints : verifier que TOUS les endpoints sensibles sont proteges par `Depends(get_current_user)` et que le RBAC est enforce (admin, manager, operator, viewer)
- [x] Verifier qu'aucun endpoint ne retourne des donnees brutes de la BDD (toujours via Pydantic response_model, jamais de dict ou de model SQLAlchemy serialise directement)
- [x] Rate limiting : ajouter `slowapi` ou equivalent sur les endpoints publics (login, refresh) — max 10 tentatives/minute par IP
- [x] Verifier que les tokens JWT ont une expiration raisonnable (access: 30min, refresh: 7 jours) et que le refresh token est revoque apres utilisation (rotation)
- [x] Verifier que les mots de passe respectent une politique minimum (8 chars, 1 majuscule, 1 chiffre) dans le schema Pydantic
- [x] Scan des dependances : `pip audit` (ou `safety check`) pour detecter les vulnerabilites connues dans les packages Python
- [x] Verifier que `.env` est dans `.gitignore` et qu'aucun secret n'est dans le code source (grep pour "password", "secret", "key" dans le code)
- [x] Headers de securite HTTP : ajouter middleware pour X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, Content-Security-Policy

### Phase 25b : Performance

- [x] Identifier les requetes N+1 dans les repositories (utiliser `joinedload` ou `selectinload` SQLAlchemy pour les relations chargees frequemment)
- [x] Ajouter des index BDD sur les colonnes les plus filtrees : `customers.email`, `customers.phone`, `cases.status`, `factures.status`, `payments.status`, `invoices.date`
- [x] Mettre en cache Redis les donnees rarement modifiees : document_types, payment_types, parametres systeme — TTL 1h
- [x] Pagination : verifier que TOUTES les listes utilisent la pagination serveur (pas de chargement de toute la table en memoire). Max 100 items par page.
- [x] Compression gzip : activer `GZipMiddleware` dans FastAPI pour les reponses > 1KB
- [x] Frontend : verifier que les pages lourdes (dashboard, vue 360) utilisent `React.lazy()` + `Suspense`, que les images utilisent `next/image` avec lazy loading
- [x] Mesurer les temps de reponse des endpoints principaux (dashboard, client 360, liste factures). Objectif : < 500ms pour 95% des requetes

### Phase 25c : Tests

- [x] `tests/test_security.py` : verifier que les endpoints proteges retournent 401 sans token, 403 avec un role insuffisant, que le rate limiting fonctionne
- [x] `tests/test_performance.py` : requetes sur des jeux de donnees de 1000+ lignes, verifier que les temps restent < 1s
- [x] Scan securite : executer `pip audit`, corriger les vulnerabilites critiques

> **CHECKPOINT SOLO** : A ce stade, le produit est pret pour une demo et une mise en production en mode Solo (1 opticien). Valider avec un client pilote avant de continuer.

---

## ETAPE 26 : Architecture multi-tenant MVP [x]

> **Contexte** : Pour vendre a un groupe d'opticiens (reseau de magasins), il faut isoler les donnees par magasin.
> Cette version MVP est volontairement simplifiee : tenant_id sur les tables + switch tenant dans le JWT + UI selector.
> Le RLS PostgreSQL complet et le dashboard groupe viendront dans une version ulterieure.
> **Prerequis** : Etapes 21-25 terminees et validees.
> **Spec de reference** : `docs/specs/03_Architecture_Logicielle_Technique_OptiFlow_AI.md`, section "Architecture Multi-tenant" de `CLAUDE.md`

### Phase 26a : Modele de donnees

- [x] Creer la migration Alembic pour les nouvelles tables :
  - `organizations` : id, name, slug (unique), contact_email, plan (enum: solo/reseau/enterprise), is_active, created_at
  - `tenants` : id, organization_id (FK), name, slug (unique), cosium_tenant (slug Cosium pour l'API), is_active, created_at
  - `tenant_users` : id, user_id (FK), tenant_id (FK), role (enum: admin/manager/operator/viewer), is_active, created_at — unique (user_id, tenant_id)
- [x] Ajouter `tenant_id` (FK tenants, nullable dans un premier temps) a toutes les tables metier : customers, cases, documents, devis, devis_lignes, factures, facture_lignes, payments, bank_transactions, notifications, action_items, audit_logs, pec_requests, relances, interactions, segments, campaigns, message_logs
- [x] Migration de donnees : creer un tenant "default", assigner toutes les donnees existantes a ce tenant, puis passer tenant_id en NOT NULL
- [x] Ajouter index `(tenant_id, id)` sur les tables principales (customers, cases, factures, payments)

### Phase 26b : Backend tenant context

- [x] Creer `core/tenant_context.py` : `TenantContext` dataclass (tenant_id, user_id, role, is_group_admin), `get_tenant_context(request) -> TenantContext` extrait du JWT
- [x] Modifier `core/security.py` : JWT payload inclut `tenant_id` et `role`
- [x] Creer middleware `TenantMiddleware` : pour chaque requete authentifiee, valider que l'user a acces au tenant demande (via tenant_users)
- [x] Modifier `POST /api/v1/auth/login` : retourne tenant_id, tenant_name, available_tenants[] dans la reponse
- [x] Creer `POST /api/v1/auth/switch-tenant` : verifie l'acces, retourne un nouveau JWT avec le nouveau tenant_id

### Phase 26c : Repositories et services tenant-aware

- [x] Modifier TOUS les repositories pour ajouter `tenant_id` dans les filtres WHERE — pattern : `db.query(Model).filter(Model.id == id, Model.tenant_id == tenant_id)`
- [x] Modifier TOUS les services pour recevoir `tenant_id` en parametre
- [x] Modifier TOUS les routers pour extraire `tenant_ctx = Depends(get_tenant_context)` et passer `tenant_ctx.tenant_id` aux services
- [x] Modifier `integrations/cosium_client.py` : accepte les credentials en parametre (preparer pour credentials par tenant)

### Phase 26d : Frontend multi-tenant

- [x] Creer `lib/tenant-context.ts` : hook `useTenant()` retourne current tenant, available tenants, switch function
- [x] Creer `components/layout/TenantSelector.tsx` : dropdown dans le Header pour switch tenant. Cacher si 1 seul tenant accessible.
- [x] Modifier `Header.tsx` : afficher nom du tenant courant + TenantSelector
- [x] Stocker le tenant_id courant dans le state auth (pas en localStorage)
- [x] Sidebar conditionnelle : afficher "Administration Reseau" seulement si `availableTenants.length > 1 || isGroupAdmin`
- [x] Dashboard adaptatif : mode Solo = KPIs du magasin uniquement, mode Reseau = KPIs agreges + comparatif magasins + filtre par tenant

### Phase 26e : Tests

- [x] `tests/test_tenant_context.py` : extraction du tenant depuis le JWT, validation d'acces
- [x] `tests/test_tenant_isolation.py` : creer 2 tenants, 2 users, verifier que user A ne voit PAS les donnees du tenant B
- [x] `tests/test_switch_tenant.py` : login, switch, verifier que les donnees changent
- [x] Verifier manuellement : se connecter, switcher de tenant, verifier que les listes changent, verifier que le TenantSelector se cache en mode Solo

---

## ETAPE 27 : Onboarding et self-service client [x]

> **Contexte** : Aujourd'hui, pour mettre en route un opticien sur OptiFlow, c'est toi qui fais tout a la main.
> Pour scaler, il faut un wizard d'onboarding automatise : le prospect s'inscrit, connecte son Cosium, et voit ses donnees en 10 minutes.
> C'est aussi indispensable pour proposer un essai gratuit (freemium / trial 14 jours).
> **Prerequis** : Etape 26 terminee (multi-tenant, car chaque nouveau client = 1 nouveau tenant)

### Phase 27a : Backend onboarding

- [x] Creer `domain/schemas/onboarding.py` : `SignupRequest(company_name, owner_email, owner_password, owner_first_name, owner_last_name, phone?)`, `OnboardingStatusResponse(steps_completed, current_step, cosium_connected, first_sync_done)`
- [x] Creer `services/onboarding_service.py` :
  - `signup(db, payload) -> TokenResponse` : cree organization + tenant + user admin + retourne JWT. Genere le slug automatiquement. Status = "trial" (14 jours).
  - `connect_cosium(db, tenant_id, cosium_tenant, login, password) -> bool` : teste la connexion Cosium (POST /authenticate/basic), stocke les credentials si OK
  - `trigger_first_sync(db, tenant_id)` : lance la premiere sync Cosium en arriere-plan (Celery task)
  - `get_onboarding_status(db, tenant_id) -> OnboardingStatusResponse` : retourne l'avancement (compte cree, Cosium connecte, sync terminee, premier dossier cree)
- [x] Creer `api/routers/onboarding.py` :
  - `POST /api/v1/onboarding/signup` — public, cree le compte
  - `POST /api/v1/onboarding/connect-cosium` — auth required, connecte Cosium
  - `POST /api/v1/onboarding/first-sync` — auth required, lance la sync
  - `GET /api/v1/onboarding/status` — auth required, retourne l'avancement

### Phase 27b : Frontend wizard d'onboarding

- [x] Creer `app/onboarding/page.tsx` : wizard en 5 etapes avec stepper visuel :
  1. **Creer votre compte** : formulaire (nom entreprise, email, mot de passe, prenom, nom, tel)
  2. **Connecter votre Cosium** : formulaire (code site Cosium, login, mot de passe) + bouton "Tester la connexion" avec feedback visuel (spinner → check vert ou croix rouge)
  3. **Importer vos donnees** : bouton "Lancer l'importation" + barre de progression + compteur (clients, factures importes)
  4. **Configurer vos preferences** : choix du fuseau horaire, logo du magasin (optionnel), activation/desactivation des modules
  5. **C'est pret !** : resume + bouton "Acceder a mon tableau de bord"
- [x] Creer `app/getting-started/page.tsx` : page "Premiers pas" avec checklist interactive apres l'onboarding
- [x] Gestion du trial : afficher un bandeau "Periode d'essai — X jours restants" dans le header si le tenant est en mode trial

### Phase 27c : Tests

- [x] `tests/test_onboarding.py` : workflow complet signup → connect cosium (mock) → sync → verifier que le tenant est cree avec toutes les donnees
- [x] `tests/test_trial.py` : verifier que le trial expire apres 14 jours, que l'acces est bloque (sauf paiement)
- [x] Test frontend : parcourir le wizard complet, verifier chaque etape, verifier la page getting-started

---

## ETAPE 28 : Facturation Stripe et abonnements SaaS [x]

> **Contexte** : Sans facturation automatisee, chaque client est gere a la main (devis, virement, suivi).
> Stripe permet l'abonnement mensuel, l'essai gratuit, la facturation automatique, et la desactivation en cas d'impaye.
> C'est aussi ce qui permet le modele freemium : essai 14 jours → conversion payante.
> **Prerequis** : Etape 27 terminee (onboarding, car le signup declenche le trial)

### Phase 28a : Integration Stripe backend

- [x] Ajouter `stripe` dans `requirements.txt`
- [x] Ajouter dans `.env.example` et `core/config.py` : `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_SOLO`, `STRIPE_PRICE_RESEAU`, `STRIPE_PRICE_IA_PRO`
- [x] Creer `integrations/stripe_client.py` : create_customer, create_subscription, create_checkout_session, cancel_subscription, get_subscription_status
- [x] Creer la migration Alembic : ajouter a `tenants` les colonnes `stripe_customer_id`, `stripe_subscription_id`, `subscription_status` (enum: trial/active/past_due/canceled), `trial_ends_at`
- [x] Creer `services/billing_service.py` : initiate_checkout, handle_webhook, check_access, get_billing_info
- [x] Creer `api/routers/billing.py` : POST /billing/checkout, POST /billing/webhook, GET /billing/status, GET /billing/invoices, POST /billing/cancel
- [x] Creer middleware `SubscriptionMiddleware` : verifier check_access() sur chaque requete, retourner 402 si expire

### Phase 28b : Facturation IA (tracking usage)

- [x] Creer la migration Alembic pour la table `ai_usage_logs` : id, tenant_id, user_id, copilot_type, model_used, tokens_in, tokens_out, cost_usd, created_at
- [x] Modifier les services IA pour logger chaque appel dans `ai_usage_logs`
- [x] Creer `services/ai_billing_service.py` : get_usage_summary, check_quota (Solo: 500 req/mois, IA Pro: 5000 req/mois)
- [x] Creer `api/routers/ai_usage.py` : GET /ai/usage?month=
- [x] Frontend : page "Consommation IA" dans les settings avec graphique et compteur quota

### Phase 28c : Frontend facturation

- [x] Creer `app/settings/billing/page.tsx` : plan actuel, statut, boutons changer/annuler, historique factures
- [x] Bandeau de paiement en retard si past_due
- [x] Page bloquee si abonnement expire avec bouton de reactivation

### Phase 28d : Tests

- [x] `tests/test_billing.py` : workflow complet signup → trial → checkout → webhook → access (mock Stripe)
- [x] `tests/test_ai_usage.py` : logger un appel IA, verifier decompte et quota
- [x] Verifier manuellement avec Stripe CLI en mode test

---

## ETAPE 29 : Copilote de renouvellement proactif [x]

> **Contexte** : C'est LA feature IA a valeur business mesurable.
> Un opticien perd des ventes parce qu'il ne relance pas les clients dont l'equipement a plus de 2 ans.
> Le copilote analyse les donnees Cosium (date d'achat, type d'equipement, contrat mutuelle) et genere des alertes de renouvellement.
> Chaque renouvellement declenche = du CA directement attribuable a OptiFlow.
> **Prerequis** : Etapes 24 (donnees Cosium reelles) et 19 (couche IA) terminees

### Phase 29a : Moteur de detection des renouvellements

- [x] Creer `services/renewal_engine.py` : detect_renewals (criteres configurables : age_minimum_months, types_equipement, mutuelle_active), score_opportunity (scoring par anciennete, valeur client, couverture mutuelle, reactivite)
- [x] Creer `domain/schemas/renewals.py` : RenewalOpportunity, RenewalCampaignCreate, RenewalDashboardResponse
- [x] Creer `api/routers/renewals.py` : GET /renewals/opportunities, POST /renewals/campaign, GET /renewals/dashboard

### Phase 29b : Copilote IA renouvellement

- [x] Creer `services/ai_renewal_copilot.py` : generate_renewal_message (SMS/email personnalise via Haiku), analyze_renewal_potential (resume IA mensuel)
- [x] Integrer avec le module relances (etape 15) : campagne renouvellement = campagne relance avec tag "renouvellement"

### Phase 29c : Frontend renouvellement

- [x] Creer `app/renewals/page.tsx` : KPI cards, tableau des opportunites, bouton "Campagne IA", historique des campagnes
- [x] Widget "Renouvellements du mois" dans le Dashboard principal
- [x] Alerte visuelle dans la vue client 360 si eligible au renouvellement

### Phase 29d : Tests

- [x] `tests/test_renewal_engine.py` : detection, scoring, tri
- [x] `tests/test_ai_renewal.py` : generation de message (mock IA)
- [x] `tests/test_renewal_api.py` : endpoints et campagne
- [x] Verification manuelle sur donnees demo

---

## ETAPE 30 : Abstraction multi-ERP [x]

> **Contexte** : Aujourd'hui OptiFlow est branche uniquement sur Cosium. Demain, il doit pouvoir se connecter a d'autres ERP optiques (Icanopee, Hexaoptic, Osmose).
> L'objectif n'est PAS d'implementer un deuxieme connecteur maintenant, mais de refactorer l'architecture pour que ce soit possible en quelques jours.
> **Prerequis** : Etape 26 terminee (multi-tenant, car chaque tenant peut avoir un ERP different)

### Phase 30a : Interface ERPConnector abstraite

- [x] Creer `integrations/erp_connector.py` : classe abstraite ERPConnector (authenticate, get_customers, get_invoices, get_invoiced_items, get_products, get_product_stock, get_payment_types)
- [x] Creer `integrations/erp_models.py` : modeles generiques ERPCustomer, ERPInvoice, ERPProduct, ERPStock, ERPPaymentType
- [x] Refactorer `integrations/cosium_client.py` en `integrations/cosium_connector.py` : CosiumConnector implemente ERPConnector
- [x] Creer `integrations/erp_factory.py` : get_connector(erp_type) retourne le bon connecteur

### Phase 30b : Mise a jour du modele de donnees

- [x] Ajouter a `tenants` : erp_type (enum: cosium/icanopee/hexaoptic/other), erp_config (JSONB)
- [x] Creer la table `tenant_erp_credentials` : id, tenant_id, erp_type, login, password_encrypted, base_url, extra_config, last_sync_at

### Phase 30c : Services agnostiques

- [x] Renommer `cosium_sync_service.py` en `erp_sync_service.py` : utilise erp_factory.get_connector()
- [x] Modifier tous les services pour passer par ERPConnector au lieu de CosiumClient
- [x] Documenter comment ajouter un nouveau connecteur ERP

### Phase 30d : Frontend settings ERP

- [x] Select "Type d'ERP" dans la page de configuration (Cosium par defaut)
- [x] Message "D'autres ERP seront bientot supportes" pour les types non implementes

### Phase 30e : Tests

- [x] `tests/test_erp_connector.py` : CosiumConnector implemente toutes les methodes
- [x] `tests/test_erp_factory.py` : factory retourne le bon connecteur
- [x] `tests/test_erp_sync.py` : sync utilise le connecteur generique
- [x] Verifier : aucun import direct de CosiumClient en dehors de `integrations/`

---

## Checkpoints de validation

### Apres ETAPE 25 — Produit pret pour demo Solo :
- [ ] Tout compile, tous les tests passent
- [ ] Demo end-to-end realisable sans interruption
- [ ] Securite auditee, performance < 500ms sur les endpoints principaux
- [ ] **ACTION** : trouver un opticien pilote pour un essai reel

### Apres ETAPE 26 — Produit pret pour les groupes :
- [ ] Multi-tenant fonctionnel, isolation verifiee
- [ ] TenantSelector se cache en mode Solo, apparait en mode Reseau
- [ ] **ACTION** : demarcher les groupes de distribution optique

### Apres ETAPE 28 — Monetisation active :
- [ ] Flow Stripe complet (trial → paiement → acces)
- [ ] Desactivation automatique en cas d'impaye
- [ ] Tracking IA fonctionnel avec quotas
- [ ] **ACTION** : lancer les inscriptions publiques

### Apres ETAPE 30 — Positionnement multi-ERP :
- [ ] Architecture abstraite, CosiumConnector derriere ERPConnector
- [ ] Documentation pour ajouter un nouveau connecteur
- [ ] **ACTION** : contacter Icanopee/Hexaoptic pour des partenariats techniques
