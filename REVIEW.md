# Audit Codex — api-cosium

_Genere automatiquement le 2026-04-26. Commit audite : `dae6413`._

## Resume

Le repo est solide sur plusieurs bases (Pydantic, chiffrement Fernet, rate limiting, tests nombreux), mais il reste un défaut d'authentification critique : la voie d'autorisation tenant-scoped n'applique pas la blacklist des JWT revoqués. J'ai aussi relevé plusieurs incohérences de déploiement et d'intégration qui cassent soit la prod (`.env.production.example` incomplet), soit des features annoncées (OIDC Cosium, Web Vitals, notifications admins). Les priorités sont donc : corriger la révocation effective des access tokens, fiabiliser le contrat de configuration prod, puis remettre en cohérence les chemins d'intégration Cosium et frontend.

## 🔴 Critiques

### 1. Les JWT revoques restent acceptes sur la plupart des routes protegees

**Fichier :** `apps/api/app/core/tenant_context.py:28`

```py
if not token:
    token = request.cookies.get("optiflow_token")
if not token:
```

**Probleme :** `get_tenant_context()` decode le JWT mais ne verifie jamais `is_token_blacklisted()`, contrairement a `get_current_user()`. Or `require_tenant_role()` et `require_permission()` reposent sur `get_tenant_context()`, donc un token vole puis revoque via `/api/v1/auth/logout` reste exploitable jusqu'a son expiration sur la majorite des endpoints metier. Le probleme est renforce par `apps/api/app/api/routers/auth.py:155-164`, qui blackliste bien le cookie d'access token au logout, mais cette blacklist est ensuite ignoree par la voie tenant-scoped.

**Recommandation :** centraliser la validation d'access token dans un helper unique qui applique decode + blacklist + verification d'appartenance tenant, puis faire consommer ce helper par `get_current_user()` et `get_tenant_context()`. Ajouter un test de regression : `login -> logout -> appel d'une route protegee par require_tenant_role -> 401`.

**Impact pour Claude :** le chemin d'auth tenant-scoped n'est pas le meme que `get_current_user()`. Corriger un seul des deux chemins laissera encore des routes ouvertes.

## 🟡 Moyens

### 1. L'exemple d'environnement production ne permet pas de demarrer une prod valide

**Fichier :** `.env.production.example:24`

```dotenv
JWT_SECRET=CHANGE_ME_GENERATE_WITH_openssl_rand_hex_64
ACCESS_TOKEN_EXPIRE_MINUTES=60

```

**Probleme :** `.env.production.example` n'inclut pas `ENCRYPTION_KEY`, `CORS_ORIGINS`, `REFRESH_TOKEN_EXPIRE_DAYS`, `SENTRY_DSN`, `MAX_UPLOAD_SIZE_MB` ni les variables Stripe pourtant consommees par `apps/api/app/core/config.py:21-96`. En production/staging, `Settings._validate_production_secrets()` refuse explicitement l'absence de `ENCRYPTION_KEY` et un `CORS_ORIGINS` mal renseigne. Suivre le fichier d'exemple tel quel produit donc soit un boot failure, soit une prod partiellement configuree.

**Recommandation :** generer les fichiers `.env*.example` a partir du schema `Settings`, ou ajouter une CI qui compare automatiquement `config.py` aux exemples d'env. Documenter clairement quelles variables sont obligatoires selon les features actives.

**Impact pour Claude :** le contrat de boot prod n'est pas lisible depuis un seul endroit ; il faut croiser `config.py`, les `.env*.example` et la doc.

### 2. La documentation OIDC Cosium ne correspond pas a l'implementation reelle

**Fichier :** `apps/api/app/integrations/cosium/client.py:103`

```py
data={
    "grant_type": "password",
    "client_id": settings.cosium_oidc_client_id,
    "username": login,
```

**Probleme :** le runtime implemente un password grant sans `client_secret`, alors que `docs/COSIUM_AUTH.md:35-53` documente un flux `client_credentials` avec `COSIUM_OIDC_CLIENT_SECRET`. Le champ `cosium_oidc_client_secret` n'existe meme pas dans `apps/api/app/core/config.py`. Une equipe qui suit la doc pour un SSO entreprise arrivera sur une configuration impossible a faire fonctionner.

**Recommandation :** choisir un seul contrat et l'aligner partout. Soit implementer reellement le flux documente (`client_credentials` + secret + settings associes), soit corriger la doc et les exemples pour decrire le password grant actuellement code.

**Impact pour Claude :** la feature "OIDC Cosium" n'est pas autoportante ; la doc, le schema d'env et le client HTTP divergent.

### 3. Les credentials ERP en clair continuent a etre acceptes silencieusement

**Fichier :** `apps/api/app/services/erp_auth_service.py:66`

```py
raw_password = tenant.cosium_password_enc or settings.cosium_password or ""
try:
    password = decrypt(raw_password) if raw_password else ""
```

**Probleme :** en cas d'echec du decrypt, le code bascule sur `password = raw_password` (`apps/api/app/services/erp_auth_service.py:69-76`). En parallele, `EncryptedString.process_result_value()` renvoie aussi la valeur en clair sur erreur de decrypt (`apps/api/app/core/encryption.py:64-72`). Resultat : des secrets supposes chiffres peuvent rester durablement en clair en base sans casser l'app, donc sans forcer leur remediation.

**Recommandation :** faire une migration one-shot qui detecte et rechiffre les lignes legacy, exposer un compteur/alerte des secrets non decryptables, puis supprimer le fallback en production pour que toute derive soit visible.

**Impact pour Claude :** le suffixe `_enc` n'est pas une garantie de chiffrement effectif ; il faut verifier le comportement de fallback avant de supposer un secret protege.

### 4. La collecte Web Vitals pointe vers une URL invalide en configuration standard

**Fichier :** `apps/web/src/components/layout/WebVitals.tsx:23`

```tsx
const endpoint = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/web-vitals`;
if (navigator.sendBeacon) {
```

**Probleme :** `NEXT_PUBLIC_API_BASE_URL` vaut deja `http://localhost:8000/api/v1` par defaut (`apps/web/src/lib/config.ts:1`). Le composant envoie donc vers `.../api/v1/api/v1/web-vitals`, ce qui casse la collecte des metrics frontend en production et rend l'observabilite trompeusement "silencieuse".

**Recommandation :** reutiliser `API_BASE` ou envoyer vers un chemin relatif (`/api/v1/web-vitals`) quand le frontend et l'API sont serves en same-origin.

**Impact pour Claude :** le projet n'a pas une convention uniforme sur ce que contient `NEXT_PUBLIC_API_BASE_URL` ; certaines callsites attendent l'origine, d'autres le prefixe API complet.

### 5. Les admins crees dans un tenant peuvent ne jamais recevoir les notifications d'evenement

**Fichier :** `apps/api/app/services/event_service.py:138`

```py
select(User)
.join(TenantUser, TenantUser.user_id == User.id)
.where(
```

**Probleme :** le filtre de destinataires s'appuie sur `User.role.in_(["admin", "owner"])` (`apps/api/app/services/event_service.py:141-143`), alors que les droits reels sont portes par `TenantUser.role`. Or `admin_user_service.create_user()` cree les nouveaux comptes avec le role global `"user"` (`apps/api/app/services/admin_user_service.py:68-71`). Un admin de tenant fraichement cree peut donc administrer le magasin mais ne jamais recevoir les notifications destinees aux admins.

**Recommandation :** filtrer sur `TenantUser.role` et `TenantUser.is_active`, pas sur `User.role`. Ajouter un test d'integration qui cree un admin de tenant puis verifie la reception d'une notification metier.

**Impact pour Claude :** dans ce repo, les autorisations metier vivent surtout dans `TenantUser.role`, pas dans `User.role`.

### 6. La stack monitoring garde des credentials faibles par defaut

**Fichier :** `docker-compose.monitoring.yml:19`

```yaml
GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
GF_USERS_ALLOW_SIGN_UP: "false"
```

**Probleme :** Grafana demarre avec `admin/admin` si rien n'est fourni, et `postgres-exporter` retombe aussi sur `optiflow/optiflow` via `DATA_SOURCE_NAME` (`docker-compose.monitoring.yml:33-34`). Le bind local reduit l'exposition, mais dans la pratique ce fichier finit souvent derriere un tunnel SSH, un reverse proxy ou un runner self-hosted : les mots de passe faibles persistent alors trop facilement.

**Recommandation :** rendre ces variables obligatoires (`${VAR:?missing}`), ou basculer la stack monitoring derriere un profil explicitement non-prod si les secrets ne sont pas fournis.

**Impact pour Claude :** "bind sur 127.0.0.1" n'est pas une frontiere de securite suffisante des qu'un tunnel, un bastion ou un proxy entre en jeu.

## 🟢 Nice-to-have

### 1. Le frontend embarque encore des dependances avec advisories moderees connues

**Fichier :** `apps/web/package.json:20`

```json
"@sentry/nextjs": "^10.47.0",
"next": "15.5.15",
"postcss": "^8.5.8",
```

**Probleme :** `npm audit --json` remonte 5 vulnerabilites moderees dans l'arbre frontend, dont `GHSA-qx2v-qp2m-jg93` sur `postcss` via `next`. Ce n'est pas bloquant au meme niveau que le bypass d'auth, mais laisser le lockfile en l'etat maintient une dette securite evitable.

**Recommandation :** regenerer le lockfile avec des versions patchees compatibles, puis faire echouer la CI tant que `npm audit --audit-level=moderate` ne repasse pas au vert.

### 2. Le seuil de couverture autorise encore de grosses regressions sur du code sensible

**Fichier :** `.github/workflows/ci.yml:61`

```yaml
python -m pytest tests/ -v --tb=short \
  --cov=app --cov-report=xml --cov-report=term \
  --cov-fail-under=45
```

**Probleme :** la CI n'exige que 45% de couverture backend, seuil egalement fige dans `apps/api/pyproject.toml:53-57`. C'est trop bas pour un monorepo avec auth multi-tenant, chiffrement, refresh tokens et synchronisations ERP. Le bypass de blacklist sur `get_tenant_context()` est typiquement le genre de regression qui passe sous ce niveau de garde-fou.

**Recommandation :** remonter progressivement le seuil (60 puis 70), et cibler d'abord des tests de regression sur logout/revocation, OIDC Cosium, Web Vitals et notifications d'admins tenant.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **Redis est critique pour la revocation en prod** : `app.security.is_token_blacklisted()` fail-close hors env local/test ; si Redis tombe, les tokens revoques deviennent indeterministes et certains parcours d'auth peuvent tous refuser.
- **Les roles utiles sont tenant-scopes** : la plupart des permissions vivent dans `TenantUser.role`, pas dans `User.role`. Se baser sur `User.role` donne vite de faux positifs ou faux negatifs.
- **`NEXT_PUBLIC_API_BASE_URL` contient deja `/api/v1`** : concatener encore `/api/v1/...` casse les appels. Il faut reutiliser `API_BASE` ou des chemins relatifs.
- **`ENCRYPTION_KEY` devient obligatoire des que `APP_ENV` vaut `production` ou `staging`** : oublier cette variable provoque un refus de demarrage ou des erreurs de decrypt.
- **Les cookies d'auth sont `secure=True` en prod** : si le bloc HTTPS de `config/nginx/nginx.conf` reste commente, le login semblera "casse" car les cookies ne partiront pas sur HTTP.
- **Le mode cookie Cosium n'est pas juste un detail dev** : l'UI admin peut persister des cookies navigateur en base pour un tenant ; leur rotation et leur reveil post-expiration doivent etre traites comme un sujet ops.

## ✨ Ameliorations proposees

Non bloquant mais gain qualite / DX :

- **Centraliser la validation JWT** : fusionner `get_current_user()` et `get_tenant_context()` autour d'un validateur commun reduira le risque de divergence future sur blacklist, issuer/audience ou controles tenant.
- **Contrat d'env verifiable en CI** : un script qui compare `Settings` avec `.env.example` et `.env.production.example` evitera de reintroduire des variables fantomes ou manquantes.
- **Tests de parcours revocation** : ajouter un test qui appelle une route protegee par `require_tenant_role()` apres logout couvrira exactement le trou le plus dangereux de ce commit.
- **Verifier les secrets legacy au boot** : un startup check qui compte les valeurs ERP non decryptables permettrait de sortir du mode "fallback silencieux" sans attendre un incident.
- **Ratchet CVE frontend** : automatiser une PR dependabot + `npm audit` avec politique de blocage sur moderate pour garder `next/postcss` propres.

## Conclusion

La priorite immediate est de corriger la validation des tokens revoques sur les routes tenant-scoped, car c'est le seul finding directement exploitable pour conserver un acces apres logout. Ensuite viennent la remise a plat du contrat de configuration prod et l'alignement de l'integration Cosium/OIDC, qui sont aujourd'hui des sources de faux demarrages et de features "documentees mais non livrables". Score global subjectif : 6/10, avec de bonnes fondations mais encore trop de divergences entre securite theorique, runtime effectif et documentation.
