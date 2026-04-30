# Audit Codex — api-cosium

_Genere automatiquement le 2026-04-30. Commit audite : `6e5137f`._

## Resume

Le repo est mature sur plusieurs garde-fous applicatifs (tenanting, cookies HttpOnly/SameSite, validations de config production, blacklist JWT, migrations Alembic), mais l'audit remonte des risques bloquants d'exploitation : secrets operationnels versionnes, `.env` production lisible dans le workspace, worker Celery mal branche sur les queues, et export de PII vers Anthropic sans garde-fou metier. `npm audit` root/web est propre et Bandit ne remonte pas de medium/high, mais `pip-audit` signale 2 CVE Python actuellement ignorees en CI. Priorites : rotation/purge secrets, correction Celery, politique IA/RGPD/PWA, puis durcissement CI/docs/env.

## 🔴 Critiques

### 1. Secrets et acces production versionnes dans `.claude-memory`

**Fichier :** `.claude-memory/vps_deployment.md:10`

```markdown
- Cle SSH locale : `<redacted>`
- Sudo password : `<redacted>`
```

**Probleme :** Le dossier `.claude-memory/` est suivi par Git et contient des informations de deploiement production : IP VPS, user SSH, chemin de cle, mot de passe sudo, login applicatif, et consignes demandant explicitement de ne pas nettoyer certains credentials. Les workflows CI/CodeQL/E2E ignorent en plus `.claude-memory/**`, ce qui laisse ces fichiers hors verification sur push.

**Recommandation :** Revoquer/rotater les secrets exposes (sudo, compte admin, credentials Cosium, MinIO/S3, JWT/ENCRYPTION si concernes), purger l'historique Git via `git filter-repo`/BFG, ajouter `.claude-memory/` au `.gitignore`, et faire tourner Gitleaks en CI sur tout le repo et l'historique.

**Impact pour Claude :** Tres eleve : ces fichiers sont precisement des notes qu'un assistant IA lira en priorite, et elles contiennent a la fois des secrets et des instructions anti-remediation.

### 2. `.env` production present localement avec secrets et origine HTTP

**Fichier :** `.env:14`

```dotenv
NEXT_PUBLIC_API_BASE_URL=<redacted>
CORS_ORIGINS=http://187.124.217.73,http://localhost:3000
COSIUM_BASE_URL=https://c1.cosium.biz
```

**Probleme :** Le fichier `.env` non versionne est present dans le workspace avec `APP_ENV=production` et plusieurs secrets applicatifs. En production, `auth_cookies.py:17` force les cookies `Secure`, donc une origine `http://...` empeche les navigateurs de conserver les cookies d'authentification. Le meme fichier expose aussi des credentials a tout script, agent ou commande locale lancee depuis le repo.

**Recommandation :** Sortir les secrets du workspace partage vers un secret manager ou injection runtime, forcer un domaine HTTPS avant `APP_ENV=production`, supprimer `localhost` des CORS production, et rotater les valeurs deja lues par des outils locaux.

**Impact pour Claude :** Eleve : un assistant peut diagnostiquer a tort un bug d'auth backend alors que le blocage vient de la combinaison `APP_ENV=production` + HTTP.

### 3. Le worker Celery ne consomme pas les queues routees

**Fichier :** `docker-compose.yml:155`

```yaml
  worker:
    restart: unless-stopped
    command: celery -A app.tasks worker --loglevel=info --concurrency=2
```

**Probleme :** `app/tasks/__init__.py:25-31` route les familles de taches vers `email`, `sync`, `extraction`, `batch` et `reminder`, mais le worker Docker demarre sans `-Q`. Celery ecoute alors seulement la queue par defaut ; les taches Beat et `.delay()` routees peuvent rester en attente sans erreur applicative visible.

**Recommandation :** Ajouter explicitement `-Q default,email,sync,extraction,batch,reminder` ou separer des workers par queue, puis ajouter un smoke test qui publie une tache par queue et verifie sa consommation.

**Impact pour Claude :** Eleve : les logs Beat peuvent donner l'impression que les jobs sont planifies alors qu'aucun worker ne lit les queues specialisees.

### 4. PII client envoyee a Claude sans consentement ni redaction

**Fichier :** `apps/api/app/services/_ai/context.py:101`

```python
parts = [
    f"DOSSIER #{case.id}",
    f"Client: {case.first_name} {case.last_name}",
```

**Probleme :** Les contextes IA incluent nom, telephone, email, factures, paiements, documents et donnees optiques. `claude_provider.py:52-53` transmet ensuite ce contexte tel quel a Anthropic des qu'une `ANTHROPIC_API_KEY` est configuree, sans opt-in tenant, redaction, registre de traitement, ni audit explicite des donnees exportees.

**Recommandation :** Ajouter un flag tenant d'activation IA avec consentement admin, minimiser/redacter les champs sensibles par defaut, journaliser les exports de donnees vers le provider, et documenter les obligations DPA/RGPD avant activation production.

**Impact pour Claude :** Eleve : le nom des fichiers laisse penser a un simple "contexte" interne, alors qu'il devient une divulgation externe de donnees client.

## 🟡 Moyens

### 1. La sync quotidienne marque un tenant comme succes malgre des erreurs par domaine

**Fichier :** `apps/api/app/tasks/sync_tasks/_sync_all.py:174`

```python
except Exception as e:
    results[name] = {"error": str(e)}
    logger.error(
```

**Probleme :** `_sync_single_tenant()` capture les erreurs de chaque domaine et retourne un dict, mais l'appelant `_sync_all_tenants()` ignore ce retour, logge `tenant_sync_done`, incremente `synced`, puis pose la cle Redis d'idempotence. Un tenant peut donc etre marque synchronise pendant 1h alors que `customers`, `invoices` ou `payments` ont echoue.

**Recommandation :** Propager une exception agreggee si un domaine echoue, ou inspecter `results` avant `synced += 1` et avant `setex`. Ajouter un test de regression "un domaine echoue => tenant non marque done".

**Impact pour Claude :** Important : le compteur `synced` et les logs "done" masquent la vraie erreur.

### 2. Endpoint `seed-demo` exposable en prod et sans garde CSRF applicatif

**Fichier :** `apps/api/app/api/routers/sync/_meta.py:15`

```python
@router.post(
    "/seed-demo",
    response_model=SeedDemoResponse,
```

**Probleme :** L'endpoint admin `POST /api/v1/sync/seed-demo` est enregistre avec tous les routers, importe `tests.factories.seed`, et cree des donnees de demonstration. Il n'a pas de garde `APP_ENV in local/test`. Comme plusieurs routes POST state-changing n'ont pas de body obligatoire, SameSite=Strict ne protege pas contre un POST depuis un sous-domaine same-site compromis.

**Recommandation :** Supprimer cet endpoint en production ou le proteger par un flag local explicite, sortir le seed de `tests/` vers une commande CLI dev, et ajouter une verification Origin/Referer ou token CSRF pour toutes les methodes unsafe basees sur cookies.

**Impact pour Claude :** Important : le nom "tests.factories" donne l'impression d'un helper de test, mais il est appele par une route API en production.

### 3. Anonymisation RGPD incomplete sur les tables liees

**Fichier :** `apps/api/app/services/gdpr_service.py:100`

```python
customer.first_name = "ANONYMISE"
customer.last_name = f"CLIENT-{client_id}"
customer.email = None
```

**Probleme :** Le droit a l'oubli anonymise principalement `Customer` et les consentements marketing. Les interactions, sujets/commentaires libres, documents, noms de fichiers, factures/devis/paiements, conversations IA et historiques associes peuvent encore contenir des donnees identifiantes.

**Recommandation :** Definir une matrice RGPD par table, supprimer ou pseudonymiser les relations client, purger les documents stockes, et ajouter des tests qui creent un client complet puis verifient l'absence de PII apres anonymisation.

**Impact pour Claude :** Important : l'export RGPD lit plus de domaines que l'anonymisation n'en efface, ce decalage est facile a rater.

### 4. La queue offline PWA stocke encore des interactions client en clair

**Fichier :** `apps/web/public/sw.js:281`

```javascript
const OFFLINE_QUEUE_ALLOW = [
  // Notes / action items / interactions : pas de PII sensible, idempotent
  "/api/v1/action-items",
```

**Probleme :** Le commentaire affirme que les interactions ne contiennent pas de PII sensible, mais `InteractionCreate` accepte `subject` et `content` libres. Le service worker stocke ensuite le body dans IndexedDB (`sw.js:464-469`) pour rejeu offline, donc des notes client peuvent rester en clair dans le navigateur.

**Recommandation :** Retirer `/api/v1/interactions` de l'allowlist offline, ou chiffrer la queue avec une cle liee a la session et purger strictement au logout/switch tenant. Garder seulement les mutations non sensibles comme "notification lue".

**Impact pour Claude :** Important : les commentaires de securite dans le fichier sont rassurants mais inexacts pour ce endpoint.

### 5. Politique de mot de passe admin plus faible que reset/signup

**Fichier :** `apps/api/app/domain/schemas/admin_users.py:12`

```python
email: str = Field(..., min_length=1, max_length=255)
password: str = Field(..., min_length=8, max_length=128)
role: str = Field(default="operator", max_length=30)
```

**Probleme :** `AdminUserCreate` accepte 8 caracteres avec majuscule et chiffre seulement. `PasswordMixin` impose 10 caracteres, minuscule, chiffre et caractere special pour reset/signup. Un admin peut donc creer des comptes plus faibles que ceux exiges par les autres flux.

**Recommandation :** Reutiliser `PasswordMixin` ou un validateur central pour tous les points de creation/changement de mot de passe, et ajouter un test qui compare les politiques.

**Impact pour Claude :** Moyen : le nom `strong_password` dans `admin_users.py` masque l'incoherence avec le validateur central.

### 6. Champs PII chiffres sans max input coherent avec la taille DB

**Fichier :** `apps/api/app/models/client.py:22`

```python
address: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)
street_number: Mapped[str | None] = mapped_column(EncryptedString(200), nullable=True)
street_name: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)
```

**Probleme :** `EncryptedString` indique lui-meme un overhead Fernet d'environ 2-3x, mais `ClientCreate`/`ClientUpdate` ne posent pas de `max_length` sur `address`, `social_security_number` ou `notes`. Une entree acceptee par Pydantic peut depasser le `VARCHAR` apres chiffrement et produire une erreur DB 500.

**Recommandation :** Passer les champs chiffres longs en `Text`, ou definir des `max_length` Pydantic calcules avec marge Fernet. Ajouter un test avec valeurs proches des limites.

**Impact pour Claude :** Moyen : la migration "encrypt_customer_pii" donne l'impression que la taille a ete reglee, mais le contrat API reste plus large que la colonne chiffree.

### 7. Deux CVE Python sont ignorees en CI sans echeance de remediation

**Fichier :** `.github/workflows/ci.yml:101`

```yaml
- run: |
    cd apps/api && pip-audit -r requirements.txt --strict \
      --ignore-vuln CVE-2025-71176 \
```

**Probleme :** `pip-audit` remonte `pytest==8.4.2` (CVE-2025-71176, fix 9.0.3) et `starlette==0.47.3` via FastAPI (CVE-2025-62727, fix 0.49.1). Le risque Starlette est surtout latent ici car aucune utilisation directe de `FileResponse`/`StaticFiles` n'a ete trouvee, mais tout ajout futur de download statique rendrait l'ignore dangereux.

**Recommandation :** Creer un ticket date pour upgrader pytest et FastAPI/Starlette, limiter l'ignore avec commentaire d'expiration, et ajouter un test/grep CI qui refuse `FileResponse` tant que Starlette reste vulnerable.

**Impact pour Claude :** Moyen : la CI "security" reste verte, donc un agent peut conclure a tort que les dependances sont clean.

### 8. Script backup off-site expose les credentials dans argv/env-file temporaire

**Fichier :** `scripts/backup_offsite.sh:51`

```bash
{
    printf 'MC_HOST_offsite=%s\n' "${OFFSITE_ENDPOINT/https:\/\//https://${OFFSITE_ACCESS_KEY}:${OFFSITE_SECRET_KEY}@}"
} > "$MC_ENV_FILE"
```

**Probleme :** Le script injecte les credentials dans une URL d'env-file temporaire, puis appelle `mc alias set offsite "$OFFSITE_ENDPOINT" "$OFFSITE_ACCESS_KEY" "$OFFSITE_SECRET_KEY"`. Les secrets peuvent apparaitre dans `ps`, traces Docker ou fichiers temporaires pendant l'execution.

**Recommandation :** Utiliser un fichier de config `mc` pre-provisionne avec permissions strictes, Docker secrets, ou une methode stdin/config non visible dans argv. Auditer les logs et snapshots existants.

**Impact pour Claude :** Moyen : le `chmod 600` et le `trap cleanup` donnent une impression de securite, mais ne couvrent pas l'exposition via arguments de processus.

### 9. Emails utilisateurs non normalises avant lookup et creation

**Fichier :** `apps/api/app/repositories/user_repo.py:7`

```python
def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(User.email == email)).first()
```

**Probleme :** Les emails sont compares et stockes tels quels. PostgreSQL applique une unicite case-sensitive sauf index specifique, donc `Admin@x` et `admin@x` peuvent coexister, avec risques de confusion login, reset password et audit.

**Recommandation :** Normaliser `strip().lower()` a l'entree, utiliser `EmailStr` pour `LoginRequest`/admin create, et ajouter une contrainte unique sur `lower(email)`.

**Impact pour Claude :** Faible a moyen : les tests seed utilisent toujours la casse attendue, donc le cas limite n'apparait pas naturellement.

## 🟢 Nice-to-have

### 1. Deploiement par `git reset --hard` destructif

**Fichier :** `scripts/deploy.sh:66`

```bash
# 1. Pull latest code (idempotent : fetch + reset au lieu de pull, evite les conflits merge)
echo "[1/6] Fetch + reset sur $DEPLOY_BRANCH..."
git fetch origin "$DEPLOY_BRANCH"
```

**Probleme :** Le script efface tout changement local serveur avant de reconstruire. C'est pratique pour un VPS jetable, mais dangereux si un hotfix, un fichier de diagnostic ou une correction manuelle non poussee existe.

**Recommandation :** Refuser le deploiement si `git status --porcelain` n'est pas vide, sauvegarder le diff avant reset, ou deployer uniquement des artefacts immuables.

**Impact pour Claude :** Moyen : les notes `.claude-memory` recommandent aussi le reset hard, ce qui peut faire disparaitre des indices de prod.

### 2. Nginx prod reste en catch-all HTTP avec HTTPS commente

**Fichier :** `config/nginx/nginx.conf:55`

```nginx
server {
    listen 80;
    # Dev/staging : "_" catch-all accepte tout Host header (utile pour CI E2E).
```

**Probleme :** Le fichier prod monte par `docker-compose.prod.yml` contient encore `server_name _;` et un bloc HTTPS entierement commente. Les commentaires signalent le risque Host-header, mais aucune garde ne force le remplacement avant production.

**Recommandation :** Templater `server_name` depuis l'environnement, refuser le boot si le placeholder reste actif en prod, et activer TLS/HSTS au reverse-proxy effectif.

**Impact pour Claude :** Moyen : selon le deploiement Caddy/nginx, le point d'entree reel peut differer du compose, donc il faut verifier la chaine proxy effective.

### 3. Documentation Celery obsolete par rapport au code actuel

**Fichier :** `docs/CELERY.md:7`

```markdown
- **Worker** : `celery -A app.tasks worker --loglevel=info`
- **Beat** : `celery -A app.tasks beat --schedule=/tmp/celerybeat-schedule`
```

**Probleme :** La doc indique un worker sans queues et un schedule Beat `/tmp`, alors que le code route des queues dediees et `docker-compose.yml` persiste le schedule dans `/app/celery-schedule/schedule.db`.

**Recommandation :** Mettre `docs/CELERY.md` a jour avec `-Q default,email,sync,extraction,batch,reminder`, le volume `celerybeat_schedule`, et les commandes de diagnostic par queue.

**Impact pour Claude :** Eleve : suivre la doc actuelle reproduit le bug critique Celery.

### 4. Variables d'environnement runtime absentes des exemples

**Fichier :** `apps/api/app/core/config.py:23`

```python
database_pool_size: int = 20
database_max_overflow: int = 30
database_pool_recycle_seconds: int = 1800
```

**Probleme :** Plusieurs variables lues par le code ne sont pas dans `.env.example` ou `.env.prod.example` : `DATABASE_POOL_*`, `FRONTEND_BASE_URL`, `BACKEND_INTERNAL_URL`, `ANALYZE`, `E2E_*`, `LOAD_TEST_*`. Les defauts marchent, mais les comportements production (liens email, pooling, proxy Next) deviennent implicites.

**Recommandation :** Generer une matrice env depuis `Settings` + usages frontend/scripts, et faire echouer la CI si une variable runtime documentable manque aux exemples.

**Impact pour Claude :** Moyen : un agent peut modifier le code en ajoutant une variable sans penser aux exemples, car il n'existe pas de check.

### 5. Lint frontend degrade des erreurs utiles en warnings

**Fichier :** `apps/web/eslint.config.mjs:13`

```javascript
"@typescript-eslint/no-explicit-any": "warn",
"@typescript-eslint/no-require-imports": "warn",
"react-hooks/exhaustive-deps": "warn",
```

**Probleme :** La CI lint passe meme avec `any`, imports CommonJS ou dependances hooks incompletes. C'est acceptable pendant migration Next 16, mais ca laisse passer des regressions de types et d'effets React.

**Recommandation :** Ajouter un budget de warnings ou remonter progressivement les regles critiques (`exhaustive-deps`, `no-explicit-any`) en erreur sur les dossiers touches.

**Impact pour Claude :** Moyen : un assistant peut croire que `npm run lint` garantit ces invariants alors qu'il ne fait que prevenir.

### 6. TODO/documentation d'etat desynchronises de la stack reelle

**Fichier :** `TODO.md:34`

```markdown
| Frontend (Next 15, SWR, CSP nonces, 0 `any`, PWA base) | 🟡 Bonne, perf client à travailler |
| Sécurité (OWASP, JWT, bcrypt, idempotence, audit logs) | 🟡 MFA et CSRF Strict manquants |
```

**Probleme :** `apps/web/package.json` utilise Next 16, les rules `any` sont en warning, et la couverture CI est a 75% alors que `TODO.md` parle ailleurs d'un alignement a 45%. La doc "source de verite" n'est plus fiable.

**Recommandation :** Regenerer la section etat depuis les manifests/configs, ou supprimer les chiffres/version figes quand ils ne sont pas controles par CI.

**Impact pour Claude :** Moyen : les agents lisent souvent `TODO.md` avant les manifests et peuvent prendre de mauvaises hypotheses de version.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **Memoire IA versionnee** : `.claude-memory/` est suivi par Git et ignore par les workflows ; ce n'est pas un stockage prive.
- **Auth HTTP en prod** : avec `APP_ENV=production`, les cookies sont `Secure`; une URL HTTP donne un symptome de login casse sans bug backend.
- **Queues Celery** : `task_routes` impose de demarrer le worker avec `-Q`; Beat peut scheduler correctement pendant que rien ne consomme.
- **Sync partielle** : `_sync_single_tenant()` transforme les exceptions en dicts, puis l'orchestrateur marque quand meme le tenant done.
- **Seed demo en prod** : `POST /api/v1/sync/seed-demo` importe `tests.factories.seed`; Docker copie `tests/` dans l'image API.
- **Precedence Cosium** : l'auth Cosium essaie cookies tenant, cookies settings, puis OIDC/basic ; des settings globaux peuvent masquer une config tenant incomplete.
- **Cle Fernet stable** : changer `ENCRYPTION_KEY` rend illisibles PII client et credentials Cosium chiffres, sauf migration de rechiffrement.
- **Volume Beat UID 1000** : le volume `celerybeat_schedule` peut necessiter un `chown 1000:1000` au premier deploiement selon les notes VPS.
- **Alembic avant boot** : `start.prod.sh` lance `alembic upgrade head` et `main.py` fail-fast si le schema prod/staging n'est pas a la head.
- **IA externe** : des que `ANTHROPIC_API_KEY` existe, le contexte client construit localement devient un transfert externe de PII.
- **Trusted proxies** : sans `TRUSTED_PROXIES`, le rate limiter peut bucketiser l'IP du reverse-proxy au lieu des clients reels.
- **Deploy destructif** : `scripts/deploy.sh` reset hard sur `origin/main`; toute investigation locale non commitee disparait.

## ✨ Ameliorations proposees

Non bloquant mais gain qualite / DX :

- **Hygiene secrets** : ajouter Gitleaks en CI obligatoire, purger `.claude-memory`, et stocker runbooks sensibles hors Git.
- **Smoke Celery** : tester en CI qu'une tache publiee sur chaque queue est consommee par la config Docker.
- **Privacy-by-design** : unifier IA, PWA offline et RGPD autour d'une classification PII par champ/table.
- **CSRF unsafe methods** : ajouter un middleware Origin/Referer ou double-submit token pour les routes cookie-based state-changing.
- **Normalisation email** : migration `lower(email)` + validators communs pour eviter doublons et bugs de login.
- **Dependances** : planifier upgrade FastAPI/Starlette et pytest 9, puis retirer les `--ignore-vuln`.
- **Env contract** : generer `.env.example`/`.env.prod.example` depuis `Settings` et les usages frontend/scripts.
- **Tests cibles** : ajouter regressions pour sync partielle, anonymisation RGPD multi-table, offline queue sans PII et endpoint seed-demo interdit en prod.
- **Chiffrement PII** : convertir les colonnes Fernet sensibles en `Text` ou appliquer des limites API strictes.

## Conclusion

Priorite recommandee : traiter les secrets et l'exposition operationnelle avant tout, corriger immediatement la config Celery, puis bloquer les exports PII non controles (IA, offline, RGPD). Score global subjectif : 6.5/10 pour une mise en production sans remediation ; le socle applicatif est solide, mais les angles operationnels actuels suffisent a creer des incidents reels.
