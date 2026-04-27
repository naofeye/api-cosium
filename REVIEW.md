# Audit Codex — api-cosium

_Genere automatiquement le 2026-04-27. Commit audite : `9cad443`._

## Resume

Le repo presente une base solide sur les garde-fous de configuration et les tests unitaires, mais plusieurs ecarts concrets restent exploitables. Les deux priorites hautes sont un contournement RBAC sur des routes mutantes et un crash runtime du rate limiter sur les endpoints sensibles en environnement non-test. Cote frontend, le lockfile embarque encore une version vulnerable de `postcss` et la CI ne remonte pas les vulnerabilites moderates. Enfin, la doc de demarrage local est incoherente avec la stack Compose reelle, ce qui cree un angle mort ops au premier boot.

## 🔴 Critiques

### 1. Le rate limiter plante sur les endpoints sensibles en environnement reel

**Fichier :** `apps/api/app/core/rate_limiter.py:55`

```py
def _trusted_proxies_set() -> set[str]:
    return {p.strip() for p in settings.trusted_proxies.split(",") if p.strip()}
```

**Probleme :** `settings.trusted_proxies` est appele depuis `_client_ip()` mais n’existe ni dans `Settings` ni dans `.env.example`. Des qu’une regle de rate-limit s’applique (`/api/v1/auth/login`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/refresh`, etc.), l’appel peut lever `AttributeError` avant tout traitement metier et transformer un endpoint critique en `500` en `local`, `development`, `staging` et `production`. Les tests ne le voient pas car le middleware est desactive en `APP_ENV=test`.

**Recommandation :** Ajouter `trusted_proxies` au schema `Settings` avec une valeur par defaut explicite, le documenter dans `.env.example`, puis ajouter un test d’integration qui execute le middleware hors `APP_ENV=test` sur un endpoint rate-limite.

**Impact pour Claude :** Un assistant qui se fie aux tests actuels peut croire que le rate limiter fonctionne alors que le chemin runtime reel n’est jamais execute en CI.

### 2. Contournement RBAC sur la creation d’operateurs OCAM

**Fichier :** `apps/api/app/api/routers/ocam_operators.py:35`

```py
@router.post("/ocam-operators", ...)
def create_operator(..., tenant_ctx: TenantContext = Depends(get_tenant_context)) -> OcamOperatorResponse:
```

**Probleme :** Cette route mutante n’attache ni `require_permission("create", ...)` ni `require_tenant_role(...)`. Or la matrice RBAC du projet n’autorise `viewer` qu’a `view`. En l’etat, n’importe quel utilisateur authentifie du tenant peut injecter ou modifier le referentiel OCAM utilise par les traitements PEC/mutuelles, ce qui ouvre une elevation de privilege applicative et un risque de corruption metier durable.

**Recommandation :** Ajouter au minimum `Depends(require_permission("create", "ocam_operator"))` ou `Depends(require_tenant_role("admin", "manager"))`, puis couvrir explicitement le cas `viewer/operator -> 403`.

**Impact pour Claude :** Les tests RBAC valident la matrice en isolation, pas son branchement reel sur toutes les routes; un assistant risque donc de conclure a tort que la protection est homogene.

## 🟡 Moyens

### 1. Contournement RBAC sur l’ajout et la suppression de mutuelles client

**Fichier :** `apps/api/app/api/routers/client_mutuelles.py:35`

```py
def add_client_mutuelle(..., tenant_ctx: TenantContext = Depends(get_tenant_context)) -> ClientMutuelleResponse:
    return client_mutuelle_service.add_client_mutuelle(...)
```

**Probleme :** Les endpoints `POST /clients/{client_id}/mutuelles` et `DELETE /clients/{client_id}/mutuelles/{mutuelle_id}` sont ouverts a tout utilisateur authentifie du tenant. Cela contredit directement la matrice RBAC (`viewer` n’a pas `create` ni `delete`) et permet a un role lecture seule de modifier les donnees mutuelle d’un client, avec impact sur la preparation PEC et les rapprochements.

**Recommandation :** Poser des dependances explicites `require_permission("create", "client_mutuelle")` et `require_permission("delete", "client_mutuelle")`, puis ajouter des tests API de non-regression pour `viewer`.

**Impact pour Claude :** La presence d’un endpoint admin voisin (`/admin/detect-mutuelles`) peut faire croire qu’une protection equivalente existe sur tout le module alors que ce n’est pas le cas.

### 2. Le frontend embarque encore un `postcss` vulnerable et la CI ne le voit pas

**Fichier :** `apps/web/package-lock.json:8880`

```json
"node_modules/next": {
  "version": "15.5.15",
  "dependencies": { "postcss": "8.4.31" }
}
```

**Probleme :** `npm audit --omit=dev --json` remonte `GHSA-qx2v-qp2m-jg93` sur `postcss` (`<8.5.10`), ici present en transitif via `next@15.5.15`. La CI frontend utilise `npm audit --audit-level=high`, donc cette faille moderate de type XSS reste silencieuse meme avec un lockfile vulnerable.

**Recommandation :** Mettre a jour `next` vers une version qui ne traine plus `postcss@8.4.31` ou forcer une resolution saine, puis baisser le seuil CI a `--audit-level=moderate` tant que vous consommez du HTML/CSS non trivial.

**Impact pour Claude :** Un assistant qui lit seulement le workflow CI peut supposer qu’un `npm audit` vert signifie “pas de CVE”, ce qui est faux ici.

### 3. La doc de demarrage local ne correspond pas a la stack Compose effective

**Fichier :** `docker-compose.yml:145`

```yml
networks:
  - default
  - interface-ia-net
```

**Probleme :** Le service `web` depend d’un reseau Docker externe `interface-ia-net`, alors que le `README` annonce un simple `docker compose up -d --build` sans precreation de reseau. Sur une machine fraiche, le premier boot echoue avant meme les tests manuels, ce qui rend le runbook de base faux et ralentit l’onboarding/debug local.

**Recommandation :** Soit supprimer ce reseau externe du compose par defaut et le reserver a un override, soit documenter explicitement `docker network create interface-ia-net` dans `README.md` et `scripts/setup.sh`.

**Impact pour Claude :** Ce prerequis n’apparait ni dans le `README` ni dans les scripts de setup, donc un assistant qui reproduit le demarrage “standard” peut diagnostiquer a tort un probleme applicatif.

## 🟢 Nice-to-have

### 1. Le chemin critique du rate limiter n’est pas vraiment teste

**Fichier :** `apps/api/tests/test_security.py:63`

```py
if settings.app_env in ("test", "local"):
    return  # Rate limiter disabled
```

**Probleme :** Le test de rate limiting sort immediatement dans les environnements utilises par la CI, ce qui laisse sans couverture le middleware reel sur les endpoints sensibles. C’est la raison pour laquelle la regression `trusted_proxies` a pu passer sans detection.

**Recommandation :** Ajouter un test cible qui instancie le middleware avec `APP_ENV=development` et un `Settings` complet, sans desactiver la logique de limitation.

**Impact pour Claude :** Sans cette note, un assistant verra “test_login_rate_limiting” et pourra surestimer la couverture securite.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **`TRUSTED_PROXIES` implicite** : le rate limiter depend d’une variable/config absente du schema `Settings`; tant que personne ne fait tourner le middleware hors `test`, la regression reste invisible.
- **RBAC teste mais pas branche partout** : `tests/test_rbac_permissions.py` valide la matrice `_ROLE_PERMISSIONS`, mais pas la presence des dependances `require_permission` sur chaque route mutante.
- **Ordre critique de demarrage DB/migrations** : `app.main._startup_checks()` refuse de booter en `staging/production` si Alembic n’est pas a `head`; `scripts/deploy.sh` lance donc `alembic upgrade head` avant l’API.
- **Reset password et billing derives de `CORS_ORIGINS`** : les URLs d’email de reset et les URLs Stripe sont construites a partir du premier element de `CORS_ORIGINS`; un ordre d’origines mal choisi peut envoyer les utilisateurs vers le mauvais host.
- **Compose par defaut non autonome** : le reseau externe `interface-ia-net` est requis par `docker-compose.yml`, mais la doc de lancement local ne le mentionne pas.

## ✨ Ameliorations proposees

- **Verifier les CVE Python dans le meme rapport** : la CI fait deja `pip-audit`; ajouter sa sortie resumee au runbook ou au rapport de release eviterait de dependre d’un environnement local outille.
- **Ajouter un test “route mutation sans permission”** : un test meta qui scanne les routers pour detecter les `POST/PATCH/DELETE` sans `require_permission` ou `require_tenant_role` fermerait toute une classe de regressions.
- **Centraliser les URLs frontend publiques** : utiliser une variable dediee type `PUBLIC_APP_URL` plutot que `CORS_ORIGINS.split(",")[0]` reduirait les erreurs de configuration sur reset password et Stripe.
- **Sortir `interface-ia-net` du compose de base** : le laisser dans un override d’integration rendrait `docker compose up` conforme au `README` et reduirait le temps d’onboarding.

## Conclusion

Les priorites recommandees sont : 1) corriger immediatement le branchement RBAC sur les routes mutantes identifiees, 2) ajouter `trusted_proxies` au schema de config et couvrir le middleware de rate-limit en environnement non-test, 3) mettre a jour le lockfile frontend ou la politique d’audit CI. Score global subjectif : **6/10**. La base est serieuse, mais ces ecarts montrent encore une difference nette entre la matrice de securite voulue et le comportement runtime effectif.
