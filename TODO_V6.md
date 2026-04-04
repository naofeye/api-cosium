# TODO V6 — OptiFlow AI : Corrections Audit Securite

> **Contexte** : L'audit ChatGPT Codex du 2026-04-04 a identifie 9 findings.
> 8/9 sont confirmes valides apres verification sur le code reel.
> Cette V6 corrige TOUS les defauts critiques avant toute mise en production.
>
> **Priorite absolue** : P0 (securite) avant P1 (robustesse) avant P2 (qualite).

---

## ETAPE 0 : Health check [ ]

- [ ] Docker 6 services UP, API 200, pytest 247+, vitest 70+, ruff 0, tsc 0

---

## PHASE 1 : SECURITE CRITIQUE — P0 (Etapes 1-3)

### ETAPE 1 : Auth httpOnly only [x]

> **P0.1 confirmé** : Les tokens sont renvoyes dans le JSON ET réécrits en cookies JS.
> Le frontend utilise `js-cookie` pour stocker les tokens, annulant la protection httpOnly.
> C'est le defaut le plus grave du projet.

#### Backend : ne plus exposer les tokens dans le body JSON
- [ ] Creer un nouveau schema `LoginResponse` qui retourne : `role`, `tenant_id`, `tenant_name`, `available_tenants` — SANS `access_token` ni `refresh_token`
- [ ] Modifier `POST /auth/login` : retourner `LoginResponse` au lieu de `TokenResponse`, les tokens ne passent que via `Set-Cookie`
- [ ] Modifier `POST /auth/refresh` : retourner `{"status": "ok"}` — le nouveau access token est dans le cookie
- [ ] Modifier `POST /auth/switch-tenant` : retourner `LoginResponse`
- [ ] Garder `POST /auth/logout` : supprime les cookies (deja fait)
- [ ] `GET /auth/me` existe deja — c'est le seul moyen pour le frontend de connaitre l'utilisateur courant

#### Frontend : supprimer js-cookie pour les tokens
- [ ] Modifier `lib/auth.ts` :
  - Supprimer `setTokens()`, `getToken()`, `getRefreshToken()` — plus besoin
  - `login()` : appeler `POST /auth/login` avec `credentials: "include"`, lire le body pour `role`, `tenant_id`, `available_tenants` (pas les tokens)
  - `refreshAccessToken()` : appeler `POST /auth/refresh` avec `credentials: "include"`, le cookie se renouvelle automatiquement
  - `logout()` : appeler `POST /auth/logout` avec `credentials: "include"`, supprimer les cookies info tenant
  - `isAuthenticated()` : appeler `GET /auth/me` au lieu de verifier le cookie JS
  - Garder `js-cookie` UNIQUEMENT pour les infos non-sensibles (tenant_id, tenant_name, available_tenants)
- [ ] Modifier `lib/api.ts` :
  - Supprimer le header `Authorization: Bearer` — le cookie httpOnly est envoye automatiquement
  - Ajouter `credentials: "include"` sur chaque `fetch()`
  - Le refresh automatique sur 401 doit appeler `POST /auth/refresh` avec `credentials: "include"`
- [ ] Modifier `middleware.ts` :
  - Le middleware Next.js ne peut pas lire les cookies httpOnly — utiliser un appel `GET /auth/me` cote serveur ou verifier un cookie non-httpOnly `optiflow_authenticated=true` (set par le backend en complement)
- [ ] Supprimer les imports et usages de `Cookies.get(TOKEN_KEY)` et `Cookies.get(REFRESH_KEY)` partout dans le frontend
- [ ] Verifier : login → navigation → refresh → logout → redirect fonctionne entierement sans token JS

#### Tests
- [ ] Backend : test que `POST /login` ne retourne PAS de champ `access_token` dans le body
- [ ] Backend : test que les cookies `Set-Cookie` ont `HttpOnly` et `SameSite=Lax`
- [ ] Frontend : verifier que `localStorage` et `js-cookie` ne contiennent aucun token apres login

---

### ETAPE 2 : Chiffrer credentials Cosium [x]

> **P0.2 confirmé** : `cosium_password_enc` stocke le mot de passe en clair.
> Le nom du champ est trompeur.

- [ ] Ajouter `cryptography` (Fernet) dans `requirements.txt`
- [ ] Creer `core/encryption.py` :
  - `ENCRYPTION_KEY` depuis `settings.encryption_key` (variable env obligatoire)
  - `encrypt(plaintext: str) -> str` : Fernet encrypt + base64
  - `decrypt(ciphertext: str) -> str` : Fernet decrypt
- [ ] Ajouter `ENCRYPTION_KEY` dans `.env.example` et `config.py` (genere avec `Fernet.generate_key()`)
- [ ] Check au startup : si `ENCRYPTION_KEY` est vide en production, refuser de demarrer
- [ ] Modifier `onboarding_service.py:connect_cosium()` : `tenant.cosium_password_enc = encrypt(payload.cosium_password)`
- [ ] Modifier `erp_sync_service.py:_authenticate_connector()` : `password = decrypt(tenant.cosium_password_enc)`
- [ ] Migration Alembic : script one-shot pour chiffrer les passwords existants
- [ ] Tests : chiffrer → dechiffrer → valeur identique, valeur chiffree != valeur originale

---

### ETAPE 3 : Hacher refresh tokens [x]

> **P0.3 confirmé** : Le refresh token est stocke en clair dans la table `refresh_tokens`.

- [ ] Modifier `repositories/refresh_token_repo.py` :
  - `create()` : stocker `hashlib.sha256(token.encode()).hexdigest()` au lieu du token brut
  - `get_by_token()` : chercher par `sha256(token).hexdigest()` au lieu du token brut
  - `revoke()` : idem, chercher par hash
- [ ] Le token en clair est retourne au client (dans le cookie httpOnly) mais JAMAIS stocke en BDD
- [ ] Migration : les anciens tokens en clair seront invalides — forcer une re-connexion (acceptable)
- [ ] Tests : verifier que la valeur en BDD != le token original, que le lookup par hash fonctionne

---

## PHASE 2 : ROBUSTESSE PRODUIT — P1 (Etapes 4-7)

### ETAPE 4 : Change password endpoint [x]

> **P1.1 confirmé** : Le frontend appelle `/auth/change-password` mais l'endpoint n'existe pas.

- [ ] Creer dans `services/auth_service.py` : `change_password(db, user_id, old_password, new_password)`
  - Verifier l'ancien mot de passe
  - Valider la force du nouveau (8+ chars, 1 maj, 1 chiffre — via `ChangePasswordRequest`)
  - Hasher et sauvegarder
  - Revoquer tous les refresh tokens du user (force re-login)
  - Logger l'action dans audit_service
- [ ] Creer l'endpoint `POST /api/v1/auth/change-password` dans `auth.py`
  - Body : `ChangePasswordRequest` (existe deja dans schemas)
  - Auth : `Depends(get_current_user)`
  - Retour : 204
- [ ] Tests : changement OK, ancien password faux → 400, nouveau trop faible → 422

---

### ETAPE 5 : Import bancaire corrige [x]

> **P1.2 confirmé** : `rapprochement/page.tsx:71` utilise `localStorage.getItem("access_token")`.

- [ ] Modifier `rapprochement/page.tsx` : remplacer le `fetch` avec `localStorage` par un appel via `fetchJson` :
  ```tsx
  const formData = new FormData();
  formData.append("file", file);
  await fetchJson("/banking/import-statement", {
    method: "POST",
    body: formData,
    // NE PAS setter Content-Type — le navigateur le fait automatiquement pour FormData
  });
  ```
- [ ] Supprimer l'import `localStorage` et le header Authorization manuel
- [ ] Modifier `lib/api.ts` : ne pas setter `Content-Type: application/json` si le body est un `FormData`
- [ ] Verifier : uploader un CSV → les transactions apparaissent

---

### ETAPE 6 : Health check restreint [x]

> **P1.3 partiellement confirmé** : Les messages d'erreur detailles ne devraient pas etre publics.

- [ ] Modifier `admin_health.py:health_check` : ne retourner que `{"status": "ok/error"}` pour chaque service, PAS le message d'erreur ni le temps de reponse
- [ ] Creer un endpoint separe `GET /api/v1/admin/health/detailed` avec `Depends(require_tenant_role("admin"))` qui retourne les details (temps de reponse, erreurs)
- [ ] Garder `/health` (racine, pas `/api/v1/admin/health`) comme endpoint minimaliste pour Docker/load balancer
- [ ] Tests : `/admin/health` sans auth retourne `{status: ok/degraded}` sans details

---

### ETAPE 7 : Upload durci [x]

> **P1.4 confirmé** : Aucune limite de taille ni validation de type fichier.

- [ ] Ajouter dans `config.py` : `max_upload_size_mb: int = 20`
- [ ] Modifier `document_service.py:upload_document` :
  - Verifier la taille AVANT de lire le fichier : `file.size` ou lire par chunks
  - Valider l'extension : liste blanche (`pdf`, `jpg`, `jpeg`, `png`, `docx`, `xlsx`, `csv`)
  - Valider le MIME type : `file.content_type` dans une liste blanche
  - Si invalide : lever `ValidationError`
- [ ] Modifier le endpoint `documents.py` : ajouter `File(max_length=20*1024*1024)` si FastAPI le supporte, sinon valider dans le service
- [ ] Tests : fichier > 20MB → erreur, fichier .exe → erreur, fichier .pdf → OK

---

## PHASE 3 : QUALITE — P2 (Etapes 8-9)

### ETAPE 8 : README aligne [x]

> **P2.1 confirmé** : README dit `Admin123`, seed fait `admin123`.

- [ ] Modifier `seed.py:49` : changer `admin123` en `Admin123` (ajouter la majuscule pour matcher le README et satisfaire la validation de force du password)
- [ ] OU modifier `README.md:21` : corriger en `admin123`
- [ ] Choisir UNE option et l'appliquer coheremment
- [ ] Mettre a jour les chiffres dans README.md : `247 tests backend`, `70 tests frontend`, etc.
- [ ] Verifier : copier-coller le password du README → login fonctionne

---

### ETAPE 9 : Verification finale [x]

- [ ] `pytest -v --cov` → 250+ pass, couverture > 85%
- [ ] `vitest run` → 70+ pass
- [ ] `ruff check` → 0 erreur
- [ ] `tsc --noEmit` → 0 erreur
- [ ] Login complet sans token JS visible (DevTools → Application → Cookies : pas de `optiflow_token` visible en JS)
- [ ] Credentials Cosium chiffres en BDD (verifier avec `SELECT cosium_password_enc FROM tenants`)
- [ ] Refresh tokens haches en BDD (verifier avec `SELECT token FROM refresh_tokens`)
- [ ] Change password fonctionnel
- [ ] Import bancaire CSV fonctionnel
- [ ] Health check ne fuit pas d'erreurs detaillees
- [ ] Upload rejette les fichiers > 20MB et les .exe

---

## Checkpoints

### Apres PHASE 1 (Etapes 1-3) — Securite resolue :
- [ ] Aucun token visible en JS (cookies httpOnly only)
- [ ] Credentials Cosium chiffres avec Fernet
- [ ] Refresh tokens haches en BDD

### Apres PHASE 2 (Etapes 4-7) — Robustesse :
- [ ] Change password fonctionnel
- [ ] Import bancaire fonctionne
- [ ] Health check minimaliste en public
- [ ] Upload durci

### Apres PHASE 3 (Etapes 8-9) — Qualite :
- [ ] README aligne avec la realite
- [ ] Tous les tests passent
- [ ] **Audit Codex : 0 finding ouvert**
