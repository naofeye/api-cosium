# TODO V7 — OptiFlow AI : Pre-Cosium — Derniers bugs et preparation connexion reelle

> **Contexte** : Audit global complet du 2026-04-04. 247 tests passent, 0 lint.
> Mais des bugs reels trouvees + le connecteur Cosium n'est pas assez robuste pour la prod.
> Cette V7 corrige les vrais bugs et prepare la connexion Cosium reelle.

---

## ETAPE 0 : Health check + re-seed [ ]

- [ ] `docker compose down -v && docker compose up --build -d` — reset BDD propre
- [ ] Attendre 15s, puis verifier que `admin@optiflow.local` / `Admin123` fonctionne (nouveau seed)
- [ ] pytest 247+, vitest 70+, ruff 0, tsc 0

---

## PHASE 1 : BUGS REELS (Etapes 1-3)

### ETAPE 1 : Corriger le conftest.py pour le flux httpOnly [ ]

> Le conftest extrait le token du cookie et le met dans le header Authorization.
> Ca marche mais ne teste pas le vrai flux cookie. Le TestClient envoie deja les cookies auto.

- [ ] Modifier `tests/conftest.py` : la fixture `auth_headers` doit retourner `{}` (dict vide)
  - Le TestClient de Starlette conserve les cookies de session automatiquement
  - Les tests qui utilisent `auth_headers` continueront de fonctionner car le cookie est envoye
- [ ] Verifier que TOUS les 247 tests passent avec `auth_headers = {}`
- [ ] Si certains tests echouent : c'est qu'ils sont dans un contexte ou le TestClient ne forward pas les cookies — les corriger au cas par cas

---

### ETAPE 2 : Corriger l'upload rapprochement bancaire [ ]

> L'upload CSV utilise `fetch()` brut au lieu de `fetchJson()`. Pas de refresh auto sur 401.

- [ ] Modifier `rapprochement/page.tsx` : remplacer le `fetch()` brut par `fetchJson()` avec `FormData`
- [ ] `fetchJson` gere deja `credentials: "include"` et le refresh sur 401
- [ ] Attention : ne pas setter `Content-Type` manuellement (le navigateur le fait pour FormData)
- [ ] Verifier : upload un CSV → les transactions apparaissent

---

### ETAPE 3 : Filtrer les warnings pytest [ ]

> 3071 warnings polluent la sortie des tests.

- [ ] Ajouter dans `pyproject.toml` section `[tool.pytest.ini_options]` :
  ```toml
  filterwarnings = [
      "ignore::DeprecationWarning:botocore",
      "ignore::DeprecationWarning:sqlalchemy",
      "ignore::DeprecationWarning:fastapi",
  ]
  ```
- [ ] Verifier : `pytest -q` affiche < 50 warnings au lieu de 3071

---

## PHASE 2 : ROBUSTESSE CONNECTEUR COSIUM (Etapes 4-6)

### ETAPE 4 : Ajouter retry + timeout + logging au CosiumClient [ ]

> Actuellement : 1 seul essai, crash si timeout. Pas de log des erreurs reseau.

- [ ] Modifier `integrations/cosium/client.py` :
  - `authenticate()` : ajouter retry (3 tentatives, backoff 1s/2s/4s) avec `tenacity` ou boucle manuelle
  - `get()` : ajouter retry (2 tentatives) sur erreurs reseau (ConnectionError, TimeoutError)
  - `get_paginated()` : augmenter `max_pages` default de 10 a 50 (couvrir les gros magasins)
  - Ajouter un logger structlog avec contexte (tenant, endpoint, attempt)
  - Timeout configurable via `settings.cosium_timeout` (default 30s)
- [ ] Ajouter `COSIUM_TIMEOUT=30` dans `.env.example` et `config.py`
- [ ] Tests : mock un timeout → verifier que le retry fonctionne, puis echoue proprement apres 3 tentatives

---

### ETAPE 5 : Ameliorer le parsing HAL et la gestion des donnees manquantes [ ]

> Si Cosium change un nom de champ ou envoie des donnees partielles, echec silencieux.

- [ ] Modifier `integrations/cosium/adapter.py` :
  - Ajouter des logs `warning` pour chaque champ manquant critique (nom, prenom, email)
  - Retourner `None` au lieu de crasher si un champ obligatoire manque
  - Ajouter un compteur de warnings dans le resultat de sync
- [ ] Modifier `integrations/cosium/cosium_connector.py` :
  - Logger le nombre de clients/factures skippees et la raison
  - Ajouter un `total_pages` dans les logs pour savoir combien de pages ont ete fetchees
- [ ] Modifier `services/erp_sync_service.py` :
  - Retourner `warnings` dans le resultat de sync : `{"created": X, "updated": Y, "skipped": Z, "warnings": ["Client #42 sans nom ignore", ...]}`
- [ ] Tests : sync avec donnees partielles → pas de crash, warnings retournes

---

### ETAPE 6 : Auto-refresh du token Cosium [ ]

> Le token Cosium est stocke en memoire. Si il expire, les requetes echouent.

- [ ] Modifier `integrations/cosium/client.py` :
  - Stocker `self._token_expires_at` (estimee : current time + 30 min ou lue depuis la reponse)
  - Avant chaque `get()` : si le token a expire, re-authentifier automatiquement
  - Ajouter un log `info` quand le token est rafraichi
- [ ] Alternative simple : re-authentifier au debut de chaque sync (le sync ne dure que quelques minutes)
- [ ] Tests : mock un token expire → verifier que la re-auth se fait automatiquement

---

## PHASE 3 : QUALITE POUR PRODUCTION (Etapes 7-9)

### ETAPE 7 : Corriger les user_id=0 critiques [ ]

> 35 fonctions de service ont `user_id: int = 0` en default. Quand user_id=0, l'audit est silencieusement ignore.

- [ ] Identifier les 5 fonctions les plus critiques :
  - `devis_service.create_devis()` — creation de devis sans trace
  - `facture_service.create_from_devis()` — creation facture sans trace
  - `banking_service.create_payment()` — paiement sans trace
  - `pec_service.create_pec()` — PEC sans trace
  - `marketing_service.send_campaign()` — campagne envoyee sans trace
- [ ] Pour ces 5 fonctions : changer `user_id: int = 0` en `user_id: int` (sans default — force le passage)
- [ ] Mettre a jour les routers qui appellent ces fonctions pour toujours passer `tenant_ctx.user_id`
- [ ] Pour les fonctions moins critiques : garder le default mais ajouter un `logger.warning` quand `user_id=0`

---

### ETAPE 8 : Ajouter le Content-Security-Policy [ ]

> Le header CSP manque dans next.config.ts et nginx.conf.

- [ ] Ajouter dans `next.config.ts` headers :
  ```
  { key: "Content-Security-Policy", value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' http://localhost:8000" }
  ```
- [ ] Ajouter le meme header dans `nginx.conf` pour le reverse proxy prod
- [ ] Verifier : le frontend fonctionne toujours (pas de blocage CSP)

---

### ETAPE 9 : Verification finale pre-Cosium [ ]

- [ ] Re-seed la BDD propre : `docker compose down -v && docker compose up --build`
- [ ] Login avec `Admin123` → OK
- [ ] `pytest -q` → 247+ pass, < 50 warnings
- [ ] `vitest run` → 70 pass
- [ ] `ruff check` + `tsc --noEmit` + `prettier --check` → 0 erreur
- [ ] Tester manuellement :
  - Login → Dashboard → KPIs affichees
  - Recherche globale → resultats
  - Creer un client → OK
  - Creer un dossier → OK
  - Creer un devis avec lignes → calculs corrects
  - Signer devis → generer facture → OK
  - Telecharger PDF devis et facture → PDFs valides
  - Changer le mot de passe → re-login OK
- [ ] Preparer les credentials Cosium reels dans `.env` :
  ```
  COSIUM_BASE_URL=https://c1.cosium.biz
  COSIUM_TENANT=ton-code-site
  COSIUM_LOGIN=ton-login
  COSIUM_PASSWORD=ton-mot-de-passe
  ```
- [ ] **Pret pour le test de connexion Cosium reel**

---

## Checkpoints

### Apres PHASE 1 (Etapes 1-3) :
- [ ] 0 bug dans le flow auth
- [ ] Tests propres (< 50 warnings)

### Apres PHASE 2 (Etapes 4-6) :
- [ ] Connecteur Cosium robuste (retry, timeout, logging, auto-refresh)
- [ ] Sync tolerant aux donnees manquantes
- [ ] Pret pour des gros volumes (max_pages=50)

### Apres PHASE 3 (Etapes 7-9) :
- [ ] Audit trail fiable sur les 5 operations critiques
- [ ] CSP header en place
- [ ] **Application prete pour le test Cosium reel**
