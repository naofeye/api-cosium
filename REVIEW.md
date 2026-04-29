# Audit Codex — api-cosium

_Genere automatiquement le 2026-04-29. Commit audite : `1e43d83`._

## Resume

Le depot contient plusieurs risques exploitables : secrets et acces production presents dans des fichiers locaux/trackes, transactions SQLAlchemy non commitees sur des routes d'ecriture, et service worker qui met en file/cache des donnees API sensibles. Les priorites sont la rotation des secrets exposes, la correction du modele transactionnel backend, puis la restriction du service worker aux ressources explicitement offline-safe. Les findings moyens portent surtout sur des incoherences d'exploitation, de recherche sur champs chiffres, de backup/deploiement et de dette de maintenance.

## 🔴 Critiques

### 1. Secrets et acces production versionnes dans `.claude-memory`

**Fichier :** `.claude-memory/vps_deployment.md:8`

```markdown
- IP : `<REDACTED>`
- User : `<REDACTED>`
- Sudo password : `<REDACTED>` (necessaire pour chown projet)
```

**Probleme :** Le depot tracke des informations d'acces VPS, un mot de passe sudo, des URLs publiques et des identifiants applicatifs. `.claude-memory/project_test_env.md:7` documente aussi des credentials Cosium en clair. Ces fichiers sont dans `git ls-files`, donc toute copie du repo ou contexte IA peut exfiltrer des acces operationnels.

**Recommandation :** Supprimer ces secrets de l'historique Git, les faire tourner immediatement (sudo/VPS, admin applicatif, Cosium, JWT, chiffrement, S3), ajouter `.claude-memory/` aux exclusions si elle contient de la memoire sensible, et remplacer ces notes par des references vers un gestionnaire de secrets.

**Impact pour Claude :** Un assistant IA risque de relire ces fichiers pour "comprendre le deploiement" et de republier involontairement des secrets dans un rapport, un ticket ou une commande.

### 2. `.env` local contient des secrets production et active le seed au demarrage

**Fichier :** `.env:1`

```dotenv
APP_ENV=production
POSTGRES_PASSWORD=<REDACTED>
JWT_SECRET=<REDACTED>
```

**Probleme :** Le fichier `.env` ignore par Git est present dans le workspace avec des secrets production, `NEXT_PUBLIC_API_BASE_URL` vers une IP publique et `SEED_ON_STARTUP=true`. Meme non versionne, ce fichier est lisible par les outils locaux, les scripts et les assistants, et peut declencher des seeds non souhaites dans un environnement production.

**Recommandation :** Sortir les secrets du workspace, utiliser un secret manager ou des variables injectees par l'orchestrateur, passer le fichier local en droits `0600`, faire tourner tous les secrets exposes, et desactiver explicitement `SEED_ON_STARTUP` hors environnements de demo/test.

**Impact pour Claude :** Comme `.env` n'est pas tracke, un audit purement Git peut le rater ; mais un assistant avec acces filesystem peut l'ingester et propager les valeurs.

### 3. Les routes d'ecriture peuvent repondre succes sans persister les donnees

**Fichier :** `apps/api/app/db/session.py:44`

```python
try:
    yield db
finally:
```

**Probleme :** La dependance `get_db()` ne commit jamais apres une requete reussie. Beaucoup de services creent/modifient via `flush()` puis retournent une reponse sans `db.commit()` explicite, par exemple `client_service.create_client`, `banking_service.create_payment`, `document_service.upload_document` et `extraction_service.create_extraction`. Les tests masquent le probleme parce qu'ils interrogent souvent la meme session non fermee.

**Recommandation :** Definir une frontiere transactionnelle unique : commit automatique apres `yield` si pas d'exception, ou commits explicites et systematiques dans les use-cases d'ecriture. Ajouter des tests qui rouvrent une nouvelle session apres chaque POST/PUT/DELETE critique.

**Impact pour Claude :** L'API semble fonctionner dans les tests et dans la reponse HTTP, mais les donnees disparaissent apres fermeture/rollback de session ; c'est un piege d'audit classique.

### 4. Le service worker stocke des corps de requetes sensibles en IndexedDB

**Fichier :** `apps/web/public/sw.js:371`

```javascript
const bodyText = await request.text().catch(() => "");
await enqueueMutation({
  body: bodyText,
```

**Probleme :** Toutes les mutations `POST/PUT/PATCH/DELETE` vers `/api/` sont interceptees et mises en file hors ligne. Cela inclut potentiellement login, reset password, onboarding, tokens ou donnees PII, stockes en clair dans IndexedDB et rejoues plus tard.

**Recommandation :** Remplacer la regle globale par une allowlist stricte d'endpoints offline-safe et idempotents. Exclure explicitement `/api/v1/auth/*`, onboarding, webhooks, paiements, imports et toute route contenant secrets/tokens/PII sensibles ; purger la file existante lors du logout.

**Impact pour Claude :** Ce risque est dans `public/sw.js`, hors routes backend et hors typage TypeScript ; il est facile de l'oublier lors d'une revue API classique.

## 🟡 Moyens

### 1. Cache API global pouvant exposer des donnees d'un utilisateur precedent

**Fichier :** `apps/web/public/sw.js:103`

```javascript
if (url.pathname.startsWith("/api/")) {
  event.respondWith(networkFirstWithTimeout(request, API_CACHE, 5000));
}
```

**Probleme :** Les GET `/api/` sont caches par URL dans le cache du navigateur. La cle ne porte pas le tenant, l'utilisateur ni le token ; en cas de reseau lent/offline, un autre utilisateur du meme profil navigateur peut recevoir une reponse cachee contenant clients, factures ou actions du precedent.

**Recommandation :** Ne pas cacher les GET authentifies. Limiter le cache aux ressources publiques, respecter `Cache-Control: no-store`, purger `API_CACHE` au logout/changement de tenant et ajouter un test navigateur de changement de session.

**Impact pour Claude :** Le backend peut etre correctement autorise tout en laissant fuir des donnees via le cache frontend.

### 2. Upload document : objet S3 cree avant transaction durable

**Fichier :** `apps/api/app/services/document_service.py:82`

```python
storage.upload_file(
    bucket=settings.s3_bucket,
    key=storage_key,
```

**Probleme :** Le fichier est pousse dans S3/MinIO avant que la ligne `Document` soit durablement commitee. Si la transaction est rollbackee ou si l'absence de commit actuelle s'applique, l'objet devient orphelin et l'API peut annoncer un upload absent en base.

**Recommandation :** Committer la ligne DB avant succes final, utiliser un outbox/transactional workflow pour l'upload, ou ajouter une compensation sur toute erreur/rollback. Ajouter un test qui ferme la session puis verifie base et bucket.

**Impact pour Claude :** L'effet externe S3 rend le bug transactionnel plus couteux qu'une simple ligne non persistee.

### 3. Recherche sur numero de securite sociale chiffre impossible en SQL

**Fichier :** `apps/api/app/services/search_service.py:65`

```python
ssn_customers = db.scalars(
    select(Customer).where(
        Customer.social_security_number.ilike(pattern),
```

**Probleme :** `Customer.social_security_number` est un `EncryptedString`. Avec un chiffrement aleatoire type Fernet, la base stocke un ciphertext different et `ILIKE` ne peut pas matcher le plaintext recherche. La fonctionnalite renvoie donc des faux negatifs silencieux.

**Recommandation :** Ajouter un index aveugle/hash normalise pour les recherches exactes ou suffixes autorisees, ou dechiffrer un ensemble candidat reduit cote application. Couvrir ce cas par un test avec une vraie valeur chiffree.

**Impact pour Claude :** Le code SQL parait valide, mais l'invariant de chiffrement rend la requete fonctionnellement fausse.

### 4. Test admin Cosium ignore les credentials tenant sans cookies

**Fichier :** `apps/api/app/api/routers/admin_cosium.py:82`

```python
client.tenant = tenant.cosium_tenant or settings.cosium_tenant or ""
...
client.authenticate()
```

**Probleme :** Si aucun cookie tenant Cosium n'existe, `client.authenticate()` retombe sur les credentials globaux des settings au lieu d'utiliser `tenant.cosium_login` et `tenant.cosium_password_enc`. Un tenant avec credentials Basic dedies peut etre declare en echec alors que sa configuration est correcte.

**Recommandation :** Reutiliser le flux centralise `erp_auth_service._authenticate_connector` ou decrypter explicitement les credentials tenant pour ce test. Ajouter un test tenant sans cookies mais avec login/password chiffres.

**Impact pour Claude :** L'ordre de priorite cookies > settings > tenant n'est pas intuitif et contredit le modele multi-tenant attendu.

### 5. Secrets offsite exposes dans la ligne de commande Docker

**Fichier :** `scripts/backup_offsite.sh:39`

```bash
MC="docker run --rm -e MC_HOST_offsite=${OFFSITE_ENDPOINT/https:\/\//https://${OFFSITE_ACCESS_KEY}:${OFFSITE_SECRET_KEY}@} -v ${PWD}/${BACKUP_DIR}:/data minio/mc"
```

**Probleme :** La cle offsite est inseree dans une URL passee en argument de commande. Elle peut apparaitre dans `ps`, les logs de shell, l'historique ou les traces CI.

**Recommandation :** Passer les credentials via `--env-file`, Docker secrets ou un fichier de config temporaire a permissions strictes. Eviter toute URL contenant `access_key:secret_key@host`.

**Impact pour Claude :** Un assistant qui propose de relancer le script peut copier la commande et divulguer les credentials.

### 6. Workers Celery ne forcent pas le mode timeout long

**Fichier :** `apps/api/app/db/session.py:9`

```python
# Increase statement timeout for Celery workers executing long-running sync jobs.
_statement_timeout = 120000 if settings.celery_worker else 30000
```

**Probleme :** Le code prevoit 120s pour les workers, mais `docker-compose.yml` ne force pas `CELERY_WORKER=true` sur le service `worker`, et `.env.example` documente `CELERY_WORKER=false`. Les jobs longs peuvent donc heriter du timeout API de 30s.

**Recommandation :** Ajouter `CELERY_WORKER=true` dans l'environnement du service worker, documenter la variable dans tous les exemples prod, et couvrir un test/config check qui distingue API et worker.

**Impact pour Claude :** La variable est optionnelle dans la doc mais devient obligatoire pour les jobs de synchronisation longs.

### 7. CVEs connues ignorees dans la CI sans garde de revalidation

**Fichier :** `.github/workflows/ci.yml:102`

```yaml
pip-audit -r requirements.txt --strict \
  --ignore-vuln CVE-2025-71176 \
  --ignore-vuln CVE-2025-62727
```

**Probleme :** `pip-audit` detecte `pytest 8.4.2` vulnerable a `CVE-2025-71176` et `starlette 0.47.3` vulnerable a `CVE-2025-62727`. La CI les ignore de maniere permanente ; la CVE Starlette est moins exploitable ici si aucun `FileResponse/StaticFiles` n'est expose, mais l'ignore-list peut devenir obsolette sans alerte.

**Recommandation :** Planifier l'upgrade vers les versions corrigees (`pytest>=9.0.3`, `starlette>=0.49.1` quand compatible FastAPI), ajouter une date d'expiration/commentaire owner sur chaque ignore, et echouer la CI si l'ignore depasse cette date.

**Impact pour Claude :** Un audit qui lit seulement le badge CI verra un pipeline vert malgre des CVEs connues.

### 8. Backup de deploiement peut viser les mauvais identifiants DB

**Fichier :** `scripts/deploy.sh:49`

```bash
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U "${POSTGRES_USER:-optiflow}" -Fc "${POSTGRES_DB:-optiflow}" > "$BACKUP_DIR/pre-deploy-$TS.dump"
```

**Probleme :** Le script n'exporte pas `.env` dans le shell et utilise `docker-compose.yml` seul pour l'etape backup, alors que le deploiement utilise `COMPOSE_FILES`. Si les variables ne sont pas dans l'environnement courant, le backup retombe sur `optiflow` et peut echouer ou sauvegarder la mauvaise base.

**Recommandation :** Charger explicitement `.env` avant le backup, utiliser la meme pile `COMPOSE_FILES`, ou recuperer `POSTGRES_USER/POSTGRES_DB` depuis le conteneur. Faire echouer le deploy si `pg_dump` ne cible pas la base attendue.

**Impact pour Claude :** L'ordre "backup puis migrate" semble sain, mais la source des variables d'environnement change entre Compose et Bash.

### 9. `logout-all` ne revoke pas l'access token courant

**Fichier :** `apps/api/app/api/routers/auth.py:136`

```python
refresh_token_repo.revoke_all_for_user(db, current_user.id)
db.commit()
_clear_auth_cookies(response)
```

**Probleme :** La route revoque tous les refresh tokens mais l'access token deja emis reste valide jusqu'a son expiration. Sur incident de session, l'utilisateur pense avoir coupe toutes les sessions alors qu'un bearer token vole peut encore appeler l'API pendant la fenetre de vie restante.

**Recommandation :** Ajouter une blacklist courte duree par `jti`/version de session, ou incrementer un `token_version` utilisateur compare au moment de valider l'access token.

**Impact pour Claude :** Le nom de route "logout-all" peut faire supposer une revocation totale alors que seule la rotation refresh est couverte.

## 🟢 Nice-to-have

### 1. Variables d'environnement de settings absentes des exemples

**Fichier :** `apps/api/app/core/config.py:17`

```python
database_pool_size: int = 10
database_max_overflow: int = 20
database_pool_recycle_seconds: int = 1800
```

**Probleme :** Les variables `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_RECYCLE_SECONDS` et `DATABASE_POOL_TIMEOUT_SECONDS` existent dans les settings mais ne sont pas documentees dans les exemples d'environnement. `.env.production.example` omet aussi des variables Cosium/OIDC et `SEED_ON_STARTUP`.

**Recommandation :** Generer ou verifier automatiquement les exemples `.env*` depuis `Settings`, avec une CI qui liste les variables manquantes/surnumeraires.

**Impact pour Claude :** Les assistants s'appuient souvent sur `.env.example` pour configurer un run local ; des defaults caches changent le comportement sans signal.

### 2. Images Docker non epinglees a une version immutable

**Fichier :** `docker-compose.yml:52`

```yaml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
```

**Probleme :** Plusieurs services utilisent `latest` (`minio`, `mailhog`, prometheus/grafana dans le compose monitoring). Un redeploiement peut changer de version sans revue ni reproductibilite.

**Recommandation :** Epinger des tags versions ou digests, puis gerer les mises a jour via Dependabot/Renovate et changelog.

**Impact pour Claude :** Une erreur apparue "sans changement de code" peut venir d'une image tiree differente.

### 3. Fonctions longues difficiles a auditer

**Fichier :** `apps/api/app/services/client_import_service.py:143`

```python
def import_from_file(
    db: Session, *, tenant_id: UUID, file_bytes: bytes, filename: str
) -> ImportResult:
```

**Probleme :** `import_from_file` depasse 100 lignes et concentre detection de format, parsing, validation, deduplication et persistance. D'autres fonctions longues existent (`merge_clients`, `sync_invoices`, `generate_fec`), ce qui augmente le risque de branches non testees.

**Recommandation :** Extraire parsing, validation et persistance en fonctions testables separees, puis ajouter des tests de cas limites par format/fichier vide/doublons.

**Impact pour Claude :** Les longues fonctions metier favorisent les corrections partielles qui cassent un chemin secondaire.

### 4. Le retry apres refresh token perd le timeout d'origine

**Fichier :** `apps/web/src/lib/api.ts:28`

```typescript
clearTimeout(timeout);
const refreshed = await refreshAccessToken();
response = await fetch(`${API_BASE}${path}`, {
```

**Probleme :** Le premier appel API utilise un `AbortController` avec timeout, mais le retry apres refresh token relance `fetch` sans signal ni nouveau timeout. Un appel reseau bloque peut donc rester suspendu.

**Recommandation :** Creer un helper de fetch avec timeout reutilisable pour l'appel initial et le retry, ou recreer un `AbortController` dedie au retry.

**Impact pour Claude :** Le timeout est visible en haut de fonction, mais pas applique a tous les chemins.

### 5. Seuil de couverture backend faible pour un domaine sensible

**Fichier :** `apps/api/pyproject.toml:44`

```toml
fail_under = 45
```

**Probleme :** Un seuil global de 45% laisse passer des regressions sur transactions, auth, chiffrement, paiements et exports. Les bugs critiques identifies montrent que la couverture actuelle ne valide pas toujours la persistance reelle.

**Recommandation :** Monter progressivement le seuil par module critique, ajouter des tests d'integration post-commit et imposer une couverture minimale sur `services/`, `api/routers/` et `security.py`.

**Impact pour Claude :** Un pipeline vert ne signifie pas que les invariants metier et securite sont suffisamment couverts.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **Secrets hors Git mais lisibles** : `.env` est ignore par Git mais present dans le workspace avec `APP_ENV=production`, secrets applicatifs et `SEED_ON_STARTUP=true`.
- **Memoire IA versionnee** : `.claude-memory/` contient des notes d'exploitation et secrets ; c'est un endroit atypique que les scans classiques de code ignorent.
- **Transactions masquees par les tests** : les services utilisent `flush()` et les tests reutilisent souvent la meme session, ce qui cache l'absence de `commit()` apres succes HTTP.
- **Service worker hors surface backend** : `apps/web/public/sw.js` peut stocker ou servir des donnees sensibles sans passer par les middlewares FastAPI.
- **Worker Celery depend d'une variable implicite** : `CELERY_WORKER=true` est necessaire pour le timeout DB long, mais n'est pas force dans le service worker Compose.
- **Ordre de deploiement critique** : `apps/api/start.prod.sh` lance `alembic upgrade head`, tandis que `apps/api/app/main.py` refuse prod/staging si la base n'est pas a jour ; tout changement d'entrypoint doit conserver cet ordre.
- **Credentials Cosium multi-sources** : cookies tenant, settings globaux, credentials tenant et access tokens n'ont pas tous la meme priorite selon les routes admin et services.
- **Volumes operationnels sensibles aux permissions** : la memoire de deploiement indique que le volume `celerybeat_schedule` doit etre owned par l'UID applicatif, sinon beat peut echouer au runtime.

## ✨ Ameliorations proposees

Non bloquant mais gain qualite / DX :

- **Rotation et hygiene secrets** : nettoyer l'historique, installer un scanner type Gitleaks/TruffleHog en CI, et bannir les secrets dans `.claude-memory`, `.env` local partage et docs.
- **Transaction manager explicite** : centraliser commit/rollback par requete ou use-case, puis interdire les services qui retournent apres `flush()` sans commit via tests/regles de revue.
- **Politique offline explicite** : documenter et tester une allowlist PWA ; toutes les routes auth, paiement, import, webhook et PII doivent etre `network-only`.
- **Env examples verifies** : ajouter un script CI qui compare `Settings` aux `.env*.example`, avec categories required/optional/prod-only.
- **Audit dependances automatise** : separer prod/dev dans `requirements`, dater les ignores CVE et ouvrir automatiquement des PRs d'upgrade compatibles.
- **Tests de persistance reelle** : pour chaque route d'ecriture critique, verifier la donnee avec une nouvelle session DB et, si applicable, l'effet externe S3/Celery.
- **Pinning infra** : epingler images Docker et versions de tooling pour rendre les deploys et reproductions d'incidents deterministes.

## Conclusion

Priorite P0 : rotation des secrets exposes et retrait des fichiers sensibles du depot/contexte IA. Priorite P1 : corriger la frontiere transactionnelle backend et neutraliser le service worker pour les donnees authentifiees/sensibles. Une fois ces points traites, le projet semble maintenable mais avec une dette de tests et de configuration significative ; score global subjectif : 5/10 tant que secrets et commits ne sont pas corriges, 7/10 apres remediation des critiques.
