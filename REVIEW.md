# Audit Codex — api-cosium

_Genere automatiquement le 2026-04-26. Commit audite : `2d564fd`._

## Resume

Le repo est globalement structuré, mais deux défauts bloquants ressortent immédiatement : le pipeline de déploiement ne peut pas réussir dès qu'une migration Alembic est en attente, et la configuration "production" fournie force des cookies `Secure` alors que le Nginx actif ne sert que du HTTP. Côté sécurité applicative, les garde-fous existent mais certains peuvent être contournés ou mal pilotés par la configuration (`X-Forwarded-For` de confiance, URLs métiers dérivées de `CORS_ORIGINS`). Les priorités sont donc : corriger le bootstrap prod, fiabiliser la chaîne HTTPS/cookies, puis nettoyer les dérives de configuration et les scripts exposant des secrets.

## 🔴 Critiques

### 1. Déploiement prod auto-bloquant avant les migrations

**Fichier :** `scripts/deploy.sh:67`, `apps/api/app/main.py:52`

```bash
docker compose $COMPOSE_FILES up -d
if docker compose $COMPOSE_FILES exec -T api curl -sf http://localhost:8000/health >/dev/null 2>&1; then
docker compose $COMPOSE_FILES exec -T api alembic upgrade head
```

**Probleme :** Le script démarre l'API puis attend qu'elle soit saine avant d'exécuter `alembic upgrade head`. Or le boot FastAPI refuse explicitement de démarrer en `production/staging` si `current_rev != head_rev`. Résultat : toute première mise en prod ou tout déploiement avec migration pendante boucle jusqu'au timeout puis échoue avant même l'étape migrations.

**Recommandation :** Exécuter `alembic upgrade head` dans un conteneur one-shot avant le healthcheck applicatif, ou bien lancer un job migration dédié avant `up -d`.

**Impact pour Claude :** Un assistant IA qui suit `scripts/deploy.sh` à la lettre conclura à une panne applicative, alors que la vraie cause est l'ordre d'exécution du bootstrap.

### 2. Configuration prod fournie incompatible avec les cookies d'authentification

**Fichier :** `apps/api/app/api/routers/auth.py:26`, `config/nginx/nginx.conf:47`

```python
_COOKIE_OPTS: dict = {
    "secure": settings.app_env not in ("local", "development", "test"),
```

**Probleme :** Dès que `APP_ENV=production`, les cookies `optiflow_token` et `optiflow_refresh` passent en `Secure`. Dans le même temps, le seul serveur Nginx actif du repo écoute en clair sur `listen 80;` et le bloc HTTPS reste entièrement commenté. Sur un déploiement "par défaut", le navigateur refusera donc de persister les cookies d'auth, ce qui casse le login et pousse souvent à désactiver `Secure` au lieu d'activer TLS correctement.

**Recommandation :** Livrer une config Nginx prod réellement HTTPS-ready par défaut, ou faire échouer le déploiement tant que TLS n'est pas activé.

**Impact pour Claude :** Le symptôme visible sera "la connexion réussit mais l'utilisateur redevient anonyme", uniquement après bascule de `APP_ENV` en production.

## 🟡 Moyens

### 1. Le rate limiting IP est contournable via `X-Forwarded-For`

**Fichier :** `apps/api/app/core/rate_limiter.py:127`

```python
forwarded = request.headers.get("X-Forwarded-For")
if forwarded:
    ip = forwarded.split(",")[0].strip()
```

**Probleme :** Le middleware fait confiance à n'importe quel header `X-Forwarded-For` envoyé par le client. Si l'API est accessible sans Nginx de confiance en frontal, un attaquant peut changer l'IP à chaque requête et contourner les limites sur `/auth/login`, `/forgot-password`, `/signup`, `/sync`, etc.

**Recommandation :** N'accepter `X-Forwarded-For` que depuis des proxies explicitement trusted, sinon utiliser `request.client.host`.

**Impact pour Claude :** Une revue superficielle verra "rate limiting Redis en place" et ratera que la clé IP est triviale à falsifier.

### 2. Les URLs critiques dépendent de l'ordre de `CORS_ORIGINS`

**Fichier :** `apps/api/app/services/auth_service.py:258`, `apps/api/app/services/billing_service.py:62`

```python
frontend_origin = settings.cors_origins.split(",")[0].strip()
success_url=f"{settings.cors_origins.split(',')[0].strip()}/billing/success",
```

**Probleme :** Le lien de reset password et les retours Stripe sont construits à partir de la première entrée de `CORS_ORIGINS`. Cette variable mélange pourtant une politique de sécurité navigateur et le canonical frontend origin. Une inversion d'ordre, un `localhost` laissé en tête ou une origine HTTP non finale enverra des emails et des redirections de paiement vers le mauvais hôte.

**Recommandation :** Introduire une variable dédiée (`FRONTEND_BASE_URL`) et arrêter de dériver des URLs métier depuis `CORS_ORIGINS`.

**Impact pour Claude :** Le bug n'apparaît qu'en environnement multi-origine et sera souvent diagnostiqué à tort comme un problème email/Stripe.

### 3. Deux templates de prod divergents maintiennent des vérités concurrentes

**Fichier :** `.env.prod.example:25`, `.env.production.example:27`

```dotenv
ACCESS_TOKEN_EXPIRE_MINUTES=30
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

**Probleme :** Le repo expose à la fois `.env.prod.example` et `.env.production.example`, avec des différences réelles sur `SEED_ON_STARTUP`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `AI_MODEL`, `NEXT_PUBLIC_SENTRY_DSN`, les variables backup/monitoring et plusieurs flags runtime. Deux opérateurs peuvent donc déployer deux "productions" différentes en suivant chacun un fichier officiellement présent.

**Recommandation :** Conserver un seul template prod canonique et faire référencer explicitement celui-ci dans la doc et les scripts.

**Impact pour Claude :** Un agent va souvent modifier le mauvais template, puis "corriger" l'autre plus tard en introduisant encore plus de dérive.

### 4. Le script d'off-site backup injecte les secrets S3 dans la ligne de commande

**Fichier :** `scripts/backup_offsite.sh:39`

```bash
MC="docker run --rm -e MC_HOST_offsite=${OFFSITE_ENDPOINT/https:\/\//https://${OFFSITE_ACCESS_KEY}:${OFFSITE_SECRET_KEY}@} -v ${PWD}/${BACKUP_DIR}:/data minio/mc"
```

**Probleme :** En fallback Docker, le secret d'accès distant est interpolé directement dans la commande shell. Il devient visible dans l'historique de process (`ps`, outils d'observabilité, crash dumps) et peut fuiter dans des logs d'exécution.

**Recommandation :** Passer les variables via `--env-file`/`-e OFFSITE_*` sans les concaténer dans l'URL, ou utiliser `mc alias set` dans un conteneur lancé avec variables d'environnement standard.

**Impact pour Claude :** Le script semble "sans hardcode", mais la fuite arrive au runtime, pas dans Git.

### 5. Le worker Celery ne bascule jamais sur le timeout SQL prévu pour les workers

**Fichier :** `apps/api/app/core/config.py:76`, `apps/api/app/db/session.py:11`, `docker-compose.yml:153`

```python
celery_worker: bool = False
_statement_timeout = 120000 if settings.celery_worker else 30000
```

**Probleme :** Le code prévoit 120s de `statement_timeout` pour les workers Celery, mais le service `worker` démarre seulement avec `env_file: [.env]` et aucun `CELERY_WORKER=true`. En pratique, les tâches de sync/export utilisent donc aussi 30s, contrairement au commentaire et à l'intention du code.

**Recommandation :** Définir `CELERY_WORKER=true` pour `worker` et `beat`, ou déduire le mode worker autrement que par une variable fragile.

**Impact pour Claude :** Les timeouts SQL paraîtront "aléatoires" sur les tâches longues alors que le code semble déjà configuré pour les éviter.

## 🟢 Nice-to-have

### 1. Le frontend garde des dépendances avec advisories npm modérées

**Fichier :** `apps/web/package.json:20`

```json
"@sentry/nextjs": "^10.47.0",
"next": "15.5.15",
"postcss": "^8.5.8",
```

**Probleme :** `npm audit --audit-level=high --json` remonte encore des advisories modérées transitives : `postcss` (<8.5.10 via `next@15.5.15`) et `uuid` (<14 via `@sentry/webpack-plugin@5.1.1`). Ce n'est pas bloquant côté prod immédiate, mais le frontend reste en dette sécurité.

**Recommandation :** Planifier une montée de version `next`/`@sentry/nextjs` validée par build et tests e2e, puis verrouiller un `npm audit` sans findings modérés connus.

**Impact pour Claude :** Un assistant qui ne relance pas `npm audit` croira que le build CI "vert" signifie absence d'avisories.

### 2. Le garde-fou qualité CI accepte encore 45% de couverture backend

**Fichier :** `.github/workflows/ci.yml:61`, `apps/api/pyproject.toml:57`

```yaml
--cov-fail-under=45
fail_under = 45
```

**Probleme :** Le seuil minimal accepté par CI reste très bas pour une base aussi métier, ce qui laisse passer facilement des régressions sur les cas d'erreur, les migrations et les flux d'auth/configuration.

**Recommandation :** Monter le seuil progressivement par lots, en commençant par les zones à plus fort risque opérationnel : auth, deploy, billing, sync.

**Impact pour Claude :** Un patch "testé" peut sembler suffisant alors qu'il n'a couvert qu'une fraction des branches critiques.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **Réseau Docker externe obligatoire** : `docker-compose.yml:145` attache `web` à `interface-ia-net` déclaré `external: true`, mais `README.md` n'explique pas qu'il faut créer ce réseau avant `docker compose up`.
- **HTTPS requis pour le login prod** : `auth.py` active `secure=True` dès `APP_ENV=production`; tant que le bloc 443 de `config/nginx/nginx.conf` reste commenté, les cookies d'auth ne tiennent pas côté navigateur.
- **Ordre migrations > boot API** : `main.py` refuse le démarrage si Alembic est en retard. Toute automatisation doit migrer avant de considérer l'API "healthy".
- **`CORS_ORIGINS` est utilisé comme URL applicative** : la première origine pilote les emails de reset et les redirections Stripe, donc l'ordre des valeurs a un impact fonctionnel caché.
- **Flag worker implicite manquant** : `CELERY_WORKER=true` n'est pas injecté par Compose, donc les workers héritent de timeouts API plus stricts que prévu.

## ✨ Ameliorations proposees

Non bloquant mais gain qualite / DX :

- **Introduire `FRONTEND_BASE_URL`** : séparer les URLs absolues métier des politiques CORS évite les redirections cassées et simplifie les déploiements multi-origine.
- **Fusionner les templates d'env prod** : un seul fichier de référence réduira fortement les erreurs d'exploitation et les corrections "dans le mauvais fichier".
- **Déplacer les migrations dans un job dédié** : cela rend le déploiement idempotent et supprime la dépendance implicite entre état du schéma et healthcheck.
- **Normaliser la confiance proxy** : une petite couche de "trusted proxies" durcit à la fois rate limiting, logs IP et futures règles anti-abus.
- **Éviter les secrets dans les scripts shell** : encapsuler les accès off-site via variables d'environnement dédiées ou profils `mc` rend les opérations beaucoup moins fuyantes.

## Conclusion

Les priorités sont nettes : 1) rendre le déploiement réellement exécutable avec migrations pendantes, 2) aligner la stack prod sur HTTPS avant tout usage de cookies `Secure`, 3) découpler les URLs frontend de `CORS_ORIGINS`, puis 4) nettoyer les dérives d'exploitation autour des templates d'env et des scripts. Score global subjectif : **6/10** — base prometteuse, mais plusieurs défauts d'intégration prod restent assez concrets pour provoquer panne, contournement ou incident opérationnel.
