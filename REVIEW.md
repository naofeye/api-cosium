# Audit Codex — api-cosium

_Genere automatiquement le 2026-04-26. Commit audite : `af9fb81`._

## Resume

Le repo est dense et couvre beaucoup de surface metier, mais plusieurs points restent a corriger avant de considerer l'ensemble robuste en production. Les deux priorites sont: 1) supprimer le basculement silencieux en mode `local` sur un deploiement incomplet, et 2) invalider aussi les access tokens lors des operations de securite sensibles. J'ai aussi releve une regression fonctionnelle importante sur l'onboarding web, une faiblesse MFA sur les backup codes, une dependance frontend avec advisory connue, et plusieurs derives de config/observabilite qui vont ralentir le diagnostic en exploitation.

## 🔴 Critiques

### 1. Un deploiement partiellement configure retombe silencieusement en mode `local`

**Fichier :** `apps/api/app/core/config.py:12`

```python
app_env: str = "local"
database_url: str = _DEV_DB_URL
jwt_secret: str = _DEV_JWT_SECRET
```

**Probleme :** Si `APP_ENV` est absent ou mal renseigne sur un serveur, l'application demarre en mode `local` avec les defaults dev. Cela desactive toutes les validations "production/staging", laisse `SEED_ON_STARTUP=true` actif, garde les cookies auth en `secure=False` via `auth.py`, re-expose la doc Swagger via `main.py`, et peut recreer un compte seed `admin@optiflow.com` / `Admin123` via `seed.py`. Le script de deploiement ne verifie meme pas `APP_ENV` (`scripts/deploy.sh` ne controle que `JWT_SECRET` et `ENCRYPTION_KEY`).

**Recommandation :** Rendre `APP_ENV` obligatoire hors tests, supprimer les secrets par defaut au runtime, refuser tout boot si `APP_ENV` n'est pas explicitement `local|development|test|production|staging`, et faire echouer `scripts/deploy.sh` si `APP_ENV=production` n'est pas present.

**Impact pour Claude :** Un assistant IA peut croire qu'un deploiement "a l'air sain" car l'app boote, alors qu'elle tourne en fait en mode dev avec des gardes de production court-circuites.

### 2. Changer le mot de passe ou faire `logout-all` ne coupe pas les access tokens deja emis

**Fichier :** `apps/api/app/services/auth_service.py:225`

```python
user.password_hash = hash_password(new_password)
refresh_token_repo.revoke_all_for_user(db, user_id)
db.commit()
```

**Probleme :** Les flows `change_password` et `reset_password` ne revoquent que les refresh tokens. Les access tokens JWT deja emis restent valides jusqu'a leur expiration (30 min par defaut). Meme probleme sur `POST /api/v1/auth/logout-all` qui efface les cookies et revoque les refresh tokens, mais ne blackliste pas l'access token en cours. Un token vole conserve donc l'acces apres un changement de mot de passe ou une deconnexion globale.

**Recommandation :** Ajouter un mecanisme d'invalidation des access tokens (`jti` + blacklist, ou `token_version` sur l'utilisateur/tenant verifie a chaque requete) et l'utiliser sur `change-password`, `reset-password`, `logout-all`, et idealement `switch-tenant`.

**Impact pour Claude :** Les tests existants couvrent surtout la rotation des refresh tokens; ils ne revelent pas la reutilisation d'un bearer vole apres un evenement de securite.

## 🟡 Moyens

### 1. Le signup d'onboarding n'installe pas la session navigateur, donc le flow web ne peut pas continuer

**Fichier :** `apps/api/app/api/routers/onboarding.py:20`

```python
@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return onboarding_service.signup(db, payload=payload)
```

**Probleme :** Contrairement a `/api/v1/auth/login`, le signup ne pose aucun cookie `optiflow_token` / `optiflow_refresh`. Cote frontend, `StepAccount` appelle pourtant `fetchJson(..., { credentials: "include" })` puis passe a `StepCosium`, qui tape des routes protegees. Le middleware Next redirige aussi `/actions` vers `/login` si le cookie `optiflow_token` manque. Resultat: l'onboarding API "reussit", mais le parcours navigateur est casse.

**Recommandation :** Faire du signup un flow symetrique au login: injecter `Response`, poser les cookies d'auth depuis le backend, et ajouter un test Playwright couvrant `signup -> connect-cosium -> /actions`.

**Impact pour Claude :** Les tests backend masquent le bug parce qu'ils reutilisent directement `resp.json()["access_token"]` en header Bearer au lieu de reproduire le comportement d'un navigateur.

### 2. La desactivation MFA laisse les backup codes en base

**Fichier :** `apps/api/app/services/mfa_service.py:80`

```python
user.totp_enabled = False
user.totp_secret_enc = None
user.totp_last_used_at = None
```

**Probleme :** `disable_mfa()` efface le secret TOTP mais ne remet pas `totp_backup_codes_hash_json` a `None`. Si l'utilisateur reactive le MFA plus tard, ses anciens backup codes restent potentiellement valides, alors qu'ils auraient du etre invalides avec l'ancienne configuration MFA.

**Recommandation :** Purger explicitement `totp_backup_codes_hash_json` dans `disable_mfa()` et ajouter un test de regression "disable -> re-enable -> old backup code rejected".

**Impact pour Claude :** Le flux parait correct tant que l'on ne teste pas un cycle complet de reenrolement MFA.

### 3. Le bundle frontend embarque un `postcss` avec advisory XSS connu

**Fichier :** `apps/web/package-lock.json:8889`

```json
"@swc/helpers": "0.5.15",
"caniuse-lite": "^1.0.30001579",
"postcss": "8.4.31",
```

**Probleme :** `npm audit` remonte actuellement une advisory moderee sur `postcss` ("PostCSS has XSS via Unescaped </style> in its CSS Stringify Output", GHSA-qx2v-qp2m-jg93) pour les versions `<8.5.10`. La CI ne la bloque pas car elle n'echoue qu'a partir de `high`.

**Recommandation :** Mettre a jour la chaine `next`/`postcss` vers une resolution non vuln, puis abaisser la politique CI ou ajouter un gate specifique sur les advisories moderees web-exposed.

**Impact pour Claude :** Le pipeline vert peut faire croire que le frontend est sain alors qu'une vuln moderement exploitable reste livree.

### 4. La config nginx des metrics est incoherente et bloque toute exposition

**Fichier :** `config/nginx/nginx.conf:73`

```nginx
location /api/v1/metrics {
    allow 127.0.0.1;
    deny all;
    return 403;
}
```

**Probleme :** Le commentaire annonce un endpoint "localhost only", mais la directive `return 403;` court-circuite tout et rend la location inutilisable meme depuis loopback. En pratique, Prometheus scrape `api:8000` directement. La doc/nginx/la stack de monitoring racontent donc trois histoires differentes pour le meme endpoint.

**Recommandation :** Soit supprimer cette location morte, soit la faire vraiment proxifier `http://api/api/v1/metrics` avec `allow 127.0.0.1`, et aligner `config/prometheus/prometheus.yml` sur le chemin retenu.

**Impact pour Claude :** Un incident d'observabilite risque d'etre cherche du mauvais cote (Prometheus ou API) alors que le probleme vient de la config reverse proxy.

## 🟢 Nice-to-have

### 1. Deux templates de prod divergent deja entre eux

**Fichier :** `.env.production.example:27`

```dotenv
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
AI_MODEL=claude-sonnet-4-20250514
```

**Probleme :** Le repo maintient a la fois `.env.production.example` et `.env.prod.example`, avec des valeurs divergentes (`ACCESS_TOKEN_EXPIRE_MINUTES=60` vs `30`, `AI_MODEL` different, variables additionnelles presentes d'un seul cote). Cela introduit une derive de configuration tres probable entre docs, CI et serveurs.

**Recommandation :** Garder une seule source de verite pour la prod, ou generer les deux fichiers depuis un template unique documente.

**Impact pour Claude :** Un assistant IA peut corriger le "mauvais" template et laisser l'autre continuer a diffuser une config obsolete.

### 2. Le seed local cree un compte admin a mot de passe constant

**Fichier :** `apps/api/app/seed.py:48`

```python
if db.query(User).count() == 0:
    user = User(email="admin@optiflow.com", password_hash=hash_password("Admin123"), role="admin")
```

**Probleme :** Le seed est assume "dev only", mais il s'appuie sur une cred hardcodee triviale. Pris isolément ce n'est pas dramatique; combine au fallback `APP_ENV=local`, cela devient une voie d'entree immediate.

**Recommandation :** Soit exiger un mot de passe seed via variable d'environnement explicite, soit generer un secret aleatoire et l'afficher une seule fois au bootstrap local.

**Impact pour Claude :** Ce detail parait anodin tant qu'on ne le recroise pas avec les defaults de configuration.

### 3. La couverture de tests ne reproduit pas le vrai parcours navigateur de l'onboarding

**Fichier :** `apps/api/tests/test_onboarding.py:76`

```python
token = resp.json()["access_token"]
status = client.get("/api/v1/onboarding/status", headers={"Authorization": f"Bearer {token}"})
```

**Probleme :** La suite de tests valide surtout un onboarding "API-first" alors que le produit reel repose sur des cookies navigateur. C'est exactement pour cela que la regression de session du signup est passee.

**Recommandation :** Ajouter un test E2E Playwright qui s'interdit tout header Bearer injecte a la main et verifie la presence des `Set-Cookie` sur signup.

**Impact pour Claude :** Les tests donnent une fausse impression de couverture sur un chemin utilisateur pourtant casse.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **`APP_ENV` est quasi obligatoire** : si la variable manque, le backend tombe en `local` avec docs actives, cookies non `Secure`, seed local actif et validations prod desactivees (`apps/api/app/core/config.py`, `apps/api/app/main.py`, `apps/api/app/api/routers/auth.py`).
- **Le reseau `interface-ia-net` doit exister** : `docker-compose.yml` reference un reseau Docker externe pour `web`; un `docker compose up` sur une machine neuve echoue tant que ce reseau n'a pas ete cree.
- **Redis indisponible change les garanties fonctionnelles** : rate limiting et certains verrous retombent en memoire process (`apps/api/app/core/rate_limiter.py`, `apps/api/app/core/redis_cache.py`). Avec `uvicorn --workers 2`, les compteurs et locks ne sont alors plus globaux.
- **Le script de deploiement est destructif** : `scripts/deploy.sh` execute `git reset --hard origin/$DEPLOY_BRANCH`; toute correction manuelle non commitee sur le serveur est perdue.
- **Le scrape monitoring reel ne passe pas par nginx** : Prometheus pointe `api:8000/api/v1/metrics`, alors que nginx renvoie 403 sur la meme route. Sans cette note, on peut debugger le mauvais composant.

## ✨ Ameliorations proposees

Non bloquant mais gain qualite / DX :

- **Token versioning** : ajouter `token_version` ou `session_epoch` sur l'utilisateur et l'injecter dans les JWT pour invalider proprement tous les access tokens sur `change-password`, `reset-password`, `logout-all`, `disable-mfa`.
- **Signup browser-safe** : aligner `POST /api/v1/onboarding/signup` sur `POST /api/v1/auth/login` avec `Set-Cookie` systematique et regression E2E dediee.
- **Unifier la config prod** : fusionner `.env.production.example` et `.env.prod.example`, puis valider `APP_ENV`, `SEED_ON_STARTUP`, `NEXT_PUBLIC_API_BASE_URL` et les secrets critiques dans `scripts/deploy.sh`.
- **Durcir la CI frontend** : faire echouer la pipeline sur les advisories `moderate` exposees au navigateur, ou au minimum ajouter une allowlist explicite et revue periodiquement.
- **Regression MFA complete** : couvrir le cycle `setup -> enable -> backup codes -> disable -> re-enable` pour verifier que rien de l'ancien enrollement n'est reutilisable.

## Conclusion

Les priorites recommandees sont claires: verrouiller le boot mode (`APP_ENV` obligatoire), corriger l'invalidation des access tokens, puis reparer le signup web pour qu'il cree une vraie session navigateur. Une fois ces points traites, le repo remonte nettement en fiabilite, mais il reste encore du travail sur la hygiene de config et la couverture E2E. Score global subjectif a ce stade: **6/10**.
