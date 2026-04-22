# Audit Codex — api-cosium

_Genere automatiquement le 2026-04-22. Commit audite : `eaa87a3`._

## Resume

Le repo est riche et couvre beaucoup de surface, mais plusieurs garde-fous de securite sont contournes au niveau HTTP. Les points les plus graves sont des escalades de privilege: le role `viewer` peut ecrire sur des entites coeur metier, et des endpoints tenant-wide sensibles (Cosium, billing) ne sont proteges que par une simple authentification. En second rideau, l'exposition publique de `/api/v1/metrics`, un script de deploiement incompatible avec les startup checks prod, et deux templates `.env` de production divergents augmentent le risque d'incident ou de fuite. La priorite est de verrouiller les endpoints mutateurs avec un RBAC effectif, puis de corriger les chemins d'exploitation/deploiement.

## 🔴 Critiques

### 1. Le role `viewer` peut creer ou modifier des donnees metier malgre la matrice RBAC

**Fichier :** `apps/api/app/api/routers/clients.py:156`

```python
def create_client(
    payload: ClientCreate,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
```

**Probleme :** `docs/RBAC.md:13-32` declare explicitement `viewer` en lecture seule et interdit `POST /clients`, `POST /clients/import`, `POST /devis`, `POST /factures` et les updates. Pourtant les routes HTTP utilisent `Depends(get_tenant_context)` au lieu de `require_tenant_role(...)` ou `require_permission(...)`, ce qui laisse passer n'importe quel utilisateur authentifie du tenant, y compris `viewer`. Le meme pattern est aussi present dans `apps/api/app/api/routers/cases.py:29-36`, `apps/api/app/api/routers/devis.py:21-38`, `apps/api/app/api/routers/factures.py:19-34` et `apps/api/app/api/routers/clients.py:105-188`.

**Recommandation :** remplacer les dependances mutatrices par un controle de permission explicite (`require_permission("create", "client")`, `require_permission("edit", "devis")`, etc.) et ajouter des tests d'integration HTTP qui verifient qu'un `viewer` recoit `403` sur ces endpoints.

**Impact pour Claude :** `test_rbac_permissions.py` et `docs/RBAC.md` donnent une impression de couverture correcte, alors que la faille est au niveau des routers. Un assistant qui ne lit que la matrice RBAC manquera facilement l'escalade.

### 2. N'importe quel compte authentifie peut remplacer les credentials Cosium du tenant et lancer le premier sync

**Fichier :** `apps/api/app/api/routers/onboarding.py:39`

```python
def connect_cosium(
    payload: ConnectCosiumRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
```

**Probleme :** `/api/v1/onboarding/connect-cosium` et `/api/v1/onboarding/first-sync` n'imposent aucun role admin/manager. Un simple `viewer` ou `operator` peut donc ecraser `tenant.cosium_tenant`, `tenant.cosium_login`, `tenant.cosium_password_enc` puis declencher `erp_sync_service.sync_customers()` via `apps/api/app/services/onboarding_service.py:127-160`. C'est un changement tenant-wide sur l'integration ERP, pas une preference utilisateur.

**Recommandation :** limiter ces endpoints a `admin` ou `manager`, journaliser l'ancien et le nouveau tenant/login Cosium dans l'audit, et exiger une confirmation explicite avant un `first-sync` deja configure.

**Impact pour Claude :** la route est rangee sous `onboarding`, ce qui masque le fait qu'elle modifie des secrets de production du tenant. Sans note, un assistant peut la traiter comme une simple etape UX.

### 3. Les operations Stripe du tenant sont accessibles a tout utilisateur connecte

**Fichier :** `apps/api/app/api/routers/billing.py:48`

```python
def create_checkout(
    payload: CheckoutRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
```

**Probleme :** `/api/v1/billing/checkout` et `/api/v1/billing/cancel` utilisent seulement `get_tenant_context`. Un `viewer` peut donc ouvrir un checkout Stripe ou annuler l'abonnement du tenant (`apps/api/app/api/routers/billing.py:93-105`) sans etre admin. Ce sont des actions financieres tenant-wide avec effet externe.

**Recommandation :** reserver ces endpoints a `admin` au minimum, idealement via une permission dediee `manage_billing`, et tracer l'auteur dans un audit log.

**Impact pour Claude :** l'absence de matrice RBAC sur le module billing peut faire croire qu'il s'agit de simples endpoints d'information, alors qu'ils pilotent un abonnement reel.

## 🟡 Moyens

### 1. `/api/v1/metrics` fuit des compteurs globaux et financiers sur Internet

**Fichier :** `apps/api/app/api/routers/metrics.py:32`

```python
@router.get(
    "/metrics",
    description="Expose les compteurs business pour scraping Prometheus. Pas d'auth (bind 127.0.0.1).",
```

**Probleme :** le commentaire indique un endpoint protege par un bind local, mais `config/nginx/nginx.conf:72-86` proxyfie publiquement tout `/api/` vers l'API. En l'etat, un client externe peut lire `optiflow_tenants_total`, `optiflow_users_total`, `optiflow_outstanding_balance_eur` et d'autres metriques globales multi-tenant sans authentification.

**Recommandation :** soit retirer completement la route publique et exporter les metriques sur un port/reseau dedie, soit bloquer explicitement `/api/v1/metrics` dans Nginx avec `allow 127.0.0.1; deny all;`.

**Impact pour Claude :** les commentaires code/docs affirment que l'endpoint est local-only; un assistant risque donc de le juger "safe" sans verifier la couche reverse proxy.

### 2. Le script de deploiement demarre l'API avant les migrations, en contradiction avec les startup checks prod

**Fichier :** `scripts/deploy.sh:54`

```bash
# 3. Run migrations BEFORE switching
echo "[3/6] Demarrage des services..."
docker compose $COMPOSE_FILES up -d
```

**Probleme :** le commentaire annonce l'inverse du comportement reel. Les migrations sont lancees seulement en etape 5, alors que `apps/api/app/main.py:39-65` fait echouer le boot en `production/staging` si `current_rev != head_rev`. Resultat: un deploy avec migration pendante peut ne jamais rendre l'API healthy. En plus, `git reset --hard "origin/$DEPLOY_BRANCH"` efface silencieusement tout changement local non committe.

**Recommandation :** executer `alembic upgrade head` via une commande one-shot avant de monter l'API, puis supprimer le `reset --hard` du chemin nominal ou le proteger derriere une validation explicite.

**Impact pour Claude :** sans lire a la fois `scripts/deploy.sh` et `main.py`, il est facile de diagnostiquer un faux "container down" au lieu d'un ordre de deploiement invalide.

### 3. Les templates de configuration prod sont divergents et l'un d'eux oublie des variables critiques

**Fichier :** `.env.production.example:24`

```env
JWT_SECRET=CHANGE_ME_GENERATE_WITH_openssl_rand_hex_64
ACCESS_TOKEN_EXPIRE_MINUTES=60
NEXT_PUBLIC_API_BASE_URL=https://your-domain.com/api/v1
```

**Probleme :** `.env.production.example` est incomplet pour un demarrage prod securise: il n'inclut pas `ENCRYPTION_KEY`, `CORS_ORIGINS`, `REFRESH_TOKEN_EXPIRE_DAYS`, `SENTRY_DSN`, `STRIPE_*` ni `MAX_UPLOAD_SIZE_MB`, alors que `.env.prod.example:16-92` les declare. Les deux fichiers se contredisent aussi sur le nom du fichier cible (`.env` vs `.env.prod`) et sur les valeurs de prod attendues.

**Recommandation :** conserver un seul template de production versionne, documenter clairement le fichier cible reel, et faire verifier ce template par CI contre `app/core/config.py`.

**Impact pour Claude :** si un assistant choisit le mauvais template, il peut proposer un deploiement "correct" qui echoue au boot ou demarre sans certaines protections attendues.

### 4. La stack monitoring demarre Grafana avec `admin/admin` par defaut

**Fichier :** `docker-compose.monitoring.yml:20`

```yaml
GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
GF_USERS_ALLOW_SIGN_UP: "false"
```

**Probleme :** si la stack monitoring est demarree sans variables d'environnement explicites, Grafana est accessible avec des credentials triviaux. `docs/PRODUCTION_CHECKLIST.md` le mentionne bien, mais le compose reste vulnerable par defaut.

**Recommandation :** supprimer tout fallback faible (`:?missing GRAFANA_PASSWORD` ou equivalent), ou desactiver le service tant que les secrets ne sont pas fournis.

**Impact pour Claude :** la checklist prod peut faire croire que le risque est deja traite, alors que la configuration executable reste permissive.

## 🟢 Nice-to-have

### 1. Un reseau Docker externe requis n'est documente nulle part dans le parcours d'installation

**Fichier :** `docker-compose.yml:145`

```yaml
networks:
  - default
  - interface-ia-net
```

**Probleme :** `docker-compose.yml:212-214` declare `interface-ia-net` en `external: true`, mais ni `README.md`, ni `docs/VPS_DEPLOYMENT.md`, ni `DEPLOY.md` ne disent qu'il faut creer ce reseau avant `docker compose up`. Sur un environnement vierge, le boot du service `web` echoue immediatement.

**Recommandation :** documenter la commande `docker network create interface-ia-net` ou rendre ce reseau optionnel via profile/override.

**Impact pour Claude :** un assistant peut perdre du temps a debugguer Docker Compose alors que le prerequis manque simplement.

### 2. Les tests RBAC couvrent la matrice en unite, pas l'application effective des roles sur les vraies routes

**Fichier :** `apps/api/tests/test_rbac_permissions.py:97`

```python
class TestViewerRole:
    ALLOWED = ("view",)
    DENIED = ("create", "edit", "delete", "export", "manage")
```

**Probleme :** la suite valide surtout `require_permission()` en isolation. Elle ne protege pas contre les regressions de wiring dans les routers, ce qui explique que des routes `viewer`-read-only soient aujourd'hui mutantes en production.

**Recommandation :** ajouter des tests HTTP parametrises pour `viewer`, `operator`, `manager`, `admin` sur les endpoints critiques (`clients`, `cases`, `devis`, `factures`, `billing`, `onboarding`).

**Impact pour Claude :** un assistant qui voit une suite RBAC verte peut conclure trop vite que le controle d'acces de bout en bout est en place.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **RBAC non branche sur les routers** : la matrice et les tests unitaires existent, mais plusieurs endpoints mutateurs utilisent encore `get_tenant_context` au lieu d'un vrai garde de permission.
- **Migrations avant boot** : en `APP_ENV=production`, l'API refuse de demarrer si Alembic n'est pas a `head`; il faut migrer avant le `up -d`, pas apres.
- **`/metrics` n'est pas local-only** : le commentaire dans le router est faux une fois Nginx en place, car `/api/` est publie tel quel.
- **Template prod a choisir** : `.env.prod.example` est beaucoup plus complet que `.env.production.example`; prendre le mauvais fichier casse le deploiement ou degrade la securite.
- **Reseau Docker externe** : `interface-ia-net` doit exister avant de demarrer la stack standard, sinon `docker compose up` echoue des le service `web`.

## ✨ Ameliorations proposees

- **RBAC centralise** : remplacer les `Depends(get_tenant_context)` mutateurs par `require_permission()` ou `require_tenant_role()` et factoriser un helper par ressource pour eviter les oublis.
- **Tests d'autorisation end-to-end** : ajouter une matrice pytest HTTP `viewer/operator/manager/admin` sur les routes qui modifient l'etat.
- **Deploiement atomique** : separer `alembic upgrade head` dans une etape pre-boot ou un job one-shot, puis verifier la health seulement apres migration reussie.
- **Template prod unique** : fusionner `.env.prod.example` et `.env.production.example`, puis faire echouer la CI si une variable de `Settings` manque dans le template officiel.
- **Monitoring ferme par defaut** : exiger un mot de passe Grafana fourni explicitement plutot que `admin/admin`.

## Conclusion

Les priorites sont claires: 1) corriger immediatement les endpoints mutateurs qui contournent le RBAC (`viewer`, onboarding, billing), 2) fermer `/api/v1/metrics`, 3) remettre a plat le chemin de deploiement prod et les templates `.env`. En l'etat, le socle technique est exploitable pour avancer, mais pas assez verrouille pour une exposition sereine en production. Score global subjectif: **5/10**.
