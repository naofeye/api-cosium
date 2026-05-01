# Audit Codex — api-cosium

_Genere automatiquement le 2026-05-01. Commit audite : `f67e5b0`._

## Resume

Le depot est globalement structure, mais l'audit met en evidence un risque immediat de fuite de secrets versionnes, plusieurs ecarts production/documentation, et des chemins metier sensibles insuffisamment verrouilles. Les priorites sont de purger/rotater les secrets Cosium, corriger l'exposition nginx/TLS production, mettre a jour les dependances avec CVE, puis renforcer les invariants facturation/synchronisation. Les angles morts les plus dangereux pour un assistant IA sont les conventions implicites autour de `.claude-memory`, du boot Alembic, de MinIO, de Celery et des variables d'environnement non documentees.

## 🔴 Critiques

### 1. Secrets Cosium versionnes dans le depot

**Fichier :** `.claude-memory/project_test_env.md:7`

```markdown
Le `.env` contient `COSIUM_LOGIN=<redacted>`, `COSIUM_PASSWORD=<redacted>` et `COSIUM_ACCESS_TOKEN=<redacted>` en clair, committe dans le repo.
```

**Probleme :** un fichier suivi par Git documente explicitement des identifiants et tokens Cosium reels en clair. Le fichier demande aussi aux assistants de ne pas supprimer ni regenerer ces valeurs, ce qui augmente le risque de reutilisation de credentials compromis. Un second export documentaire contient aussi un `client_secret` dans `DOC API/01CONE06488 10_files/content.html:787`.

**Recommandation :** rotater immediatement les identifiants/tokens Cosium concernes, remplacer tous les secrets versionnes par des placeholders, purger l'historique Git si le depot a ete partage, ajouter un secret scanner bloquant en CI, et exclure `.claude-memory/` ou tout fichier de memoire locale contenant des valeurs sensibles.

**Impact pour Claude :** Claude risque de lire ces fichiers comme source d'autorite et de conserver/reutiliser les secrets au lieu de les traiter comme compromis.

### 2. Le proxy production publie 443 mais la configuration active ne sert que HTTP

**Fichier :** `config/nginx/nginx.conf:55`

```nginx
server {
    listen 80;
    server_name _;
```

**Probleme :** `docker-compose.prod.yml` expose `80:80` et `443:443`, mais le bloc SSL actif est absent et le serveur 443 reste commente. La configuration accepte aussi un `server_name _`, ce qui neutralise la defense Host-header attendue en production. Si ce nginx est le point d'entree public, les cookies `secure` de l'API ne fonctionneront pas correctement sans terminaison TLS externe et le trafic peut rester en clair.

**Recommandation :** activer un bloc `listen 443 ssl http2` avec `server_name` explicite, rediriger strictement HTTP vers HTTPS, monter les certificats reels, ou documenter clairement que TLS est termine par un proxy amont et retirer l'exposition 443 locale si elle est trompeuse.

**Impact pour Claude :** un assistant peut croire que la stack production est deja prete pour HTTPS parce que le compose mappe le port 443, alors que la configuration nginx active ne le fait pas.

## 🟡 Moyens

### 1. CVE connues ignorees dans le pipeline API

**Fichier :** `.github/workflows/ci.yml:101`

```yaml
cd apps/api && pip-audit -r requirements.txt --strict \
  --ignore-vuln CVE-2025-71176 \
  --ignore-vuln CVE-2025-62727
```

**Probleme :** `pip-audit` detecte encore `pytest==8.4.2` vulnerable a `CVE-2025-71176` et `starlette==0.47.3` vulnerable a `CVE-2025-62727`. Le workflow les ignore explicitement, dont une dependance runtime via FastAPI/Starlette.

**Recommandation :** mettre a jour `pytest` vers une version corrigee, puis FastAPI/Starlette des qu'une combinaison compatible inclut `starlette>=0.49.1`; retirer les ignores CI apres validation.

**Impact pour Claude :** la CI donne un signal vert alors que l'audit de dependances signale toujours des vulnerabilites.

### 2. Le plan Stripe choisi n'est jamais transmis au webhook

**Fichier :** `apps/api/app/integrations/stripe_client.py:47`

```python
metadata={"tenant_id": str(tenant_id)},
client_reference_id=str(tenant_id),
mode="subscription",
```

**Probleme :** `create_checkout_session` recoit un `plan`, mais ne l'inscrit pas dans les metadata Stripe. Le webhook lit ensuite `data.get("metadata", {}).get("plan", org.plan)`, donc l'organisation peut rester sur son ancien plan apres paiement.

**Recommandation :** ajouter `plan` dans les metadata de session et tester le webhook `checkout.session.completed` avec un changement effectif `trial -> pro` ou `pro -> premium`.

**Impact pour Claude :** l'API semble supporter plusieurs plans parce que le parametre existe, mais l'invariant de propagation Stripe est casse.

### 3. L'idempotence des creations n'est pas atomique

**Fichier :** `apps/api/app/core/idempotency.py:106`

```python
existing = cache_get(ctx._redis_key)
if existing:
    if existing.get("body_hash") != body_hash:
```

**Probleme :** la cle d'idempotence est lue avant l'execution metier puis ecrite apres la reponse. Deux requetes concurrentes avec la meme cle et le meme corps peuvent donc passer toutes les deux avant que Redis ne stocke la premiere reponse.

**Recommandation :** reserver la cle avec une operation atomique `SET NX` ou un etat `pending` avant l'appel service, retourner `409/425` pendant l'execution concurrente, puis remplacer l'etat par la reponse finale.

**Impact pour Claude :** un assistant peut voir la presence d'un middleware d'idempotence et supposer a tort que les doublons concurrentiels sont couverts.

### 4. Les URLs presignees MinIO pointent vers un endpoint Docker interne

**Fichier :** `.env.prod.example:39`

```dotenv
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=your_minio_access_key_here
S3_SECRET_KEY=your_minio_secret_key_here
```

**Probleme :** le service genere des URLs presignees avec ce endpoint, puis `documents.py` redirige directement le navigateur vers cette URL. En production, `http://minio:9000` est un nom Docker interne non resolvable depuis le client et expose aussi un detail d'infrastructure.

**Recommandation :** servir les telechargements via l'API, comme pour les documents Cosium, ou introduire un `S3_PUBLIC_ENDPOINT` HTTPS utilise uniquement pour les URLs presignees publiques.

**Impact pour Claude :** la configuration fonctionne entre conteneurs mais pas necessairement depuis un navigateur externe.

### 5. `FRONTEND_BASE_URL` est utilise mais absent des exemples d'environnement

**Fichier :** `apps/api/app/services/_auth/password.py:53`

```python
frontend_origin = (
    settings.frontend_base_url.strip()
    or settings.cors_origins.split(",")[0].strip()
)
```

**Probleme :** les liens de reset password dependent de `FRONTEND_BASE_URL`, mais `.env.example`, `.env.prod.example` et `docs/ENV.md` ne le documentent pas. En absence de valeur, l'API prend le premier `CORS_ORIGINS`, ce qui peut produire un lien localhost, API-only ou simplement mauvais selon l'ordre configure.

**Recommandation :** documenter `FRONTEND_BASE_URL` partout, le rendre obligatoire en `staging/production`, et tester la generation de reset link avec plusieurs origines CORS.

**Impact pour Claude :** un assistant peut ajouter une origine CORS sans comprendre qu'elle change aussi les liens d'email.

### 6. La regle `cosium_id` unique par tenant n'est pas appliquee en base

**Fichier :** `apps/api/alembic/versions/y0z1a2b3c4d5_add_customer_cosium_id.py:33`

```python
op.add_column("customers", sa.Column("cosium_id", sa.String(length=50), nullable=True))
op.create_index("ix_customers_cosium_id", "customers", ["cosium_id"], unique=False)
```

**Probleme :** `docs/BUSINESS_RULES.md` annonce `cosium_id UNIQUE par tenant`, mais la migration cree un index non unique uniquement sur `cosium_id`. Des doublons Cosium peuvent etre inseres, notamment lors d'import concurrent ou de reprise partielle.

**Recommandation :** nettoyer les doublons existants puis ajouter un index unique partiel `(tenant_id, cosium_id) WHERE cosium_id IS NOT NULL`.

**Impact pour Claude :** la documentation donne un invariant fort que le schema ne garantit pas.

### 7. Duree d'essai contradictoire entre code et regles metier

**Fichier :** `apps/api/app/services/onboarding_service.py:27`

```python
TRIAL_DAYS = 14
DEFAULT_PLAN = "trial"
```

**Probleme :** `docs/BUSINESS_RULES.md:100` indique un trial de 30 jours, alors que le code cree les organisations avec 14 jours. Cela peut fausser les tests, le support client et les promesses commerciales.

**Recommandation :** choisir la valeur officielle, aligner code, documentation et fixtures, puis ajouter un test d'onboarding qui verrouille la date `trial_ends_at`.

**Impact pour Claude :** Claude peut proposer un correctif ou une reponse support basee sur la documentation alors que la production applique 14 jours.

### 8. La frequence de synchronisation Cosium documentee ne correspond pas au Celery beat

**Fichier :** `apps/api/app/tasks/__init__.py:45`

```python
"sync-cosium-daily": {
    "task": "app.tasks.sync_tasks.sync_cosium_daily",
    "schedule": crontab(hour=6, minute=0),
```

**Probleme :** la documentation metier evoque une synchronisation incrementale toutes les heures, mais le beat configure une tache quotidienne a 06:00. Les utilisateurs peuvent donc voir des donnees bien moins fraiches que prevu.

**Recommandation :** aligner la documentation et la planification reelle, ou ajouter une tache incrementale horaire distincte si l'objectif produit est une fraicheur inferieure a une heure.

**Impact pour Claude :** sans lire le beat Celery, un assistant peut surestimer la fraicheur des donnees synchronisees.

### 9. `development` est traite comme production pour le fail-open Redis token blacklist

**Fichier :** `apps/api/app/security.py:107`

```python
fail_closed = settings.app_env not in ("local", "test", "dev")
if fail_closed:
    return True
```

**Probleme :** les environnements valides incluent `development`, pas `dev`. En cas d'indisponibilite Redis, `APP_ENV=development` invalide donc tous les tokens alors que le commentaire annonce un fail-open en dev/test.

**Recommandation :** remplacer `dev` par `development`, centraliser les noms d'environnements valides et ajouter un test parametre sur `local/development/test/staging/production`.

**Impact pour Claude :** le commentaire est plausible mais faux pour l'environnement effectivement documente.

### 10. Le retry frontend apres refresh token perd le timeout

**Fichier :** `apps/web/src/lib/api.ts:33`

```ts
if (refreshed) {
  response = await fetch(`${API_BASE}${path}`, {
    ...options,
```

**Probleme :** la requete initiale utilise un `AbortController`, mais la requete rejouee apres refresh token n'a plus de signal ni de timeout. Une API bloquee apres refresh peut suspendre l'UI jusqu'a resolution reseau.

**Recommandation :** creer un nouveau `AbortController` et un nouveau timer pour le retry, ou factoriser `fetchWithTimeout` afin que chaque tentative ait la meme politique d'annulation.

**Impact pour Claude :** le timeout semble present en haut de fonction, mais ne couvre pas tous les chemins.

### 11. Les mutations cookie-auth reposent uniquement sur SameSite contre le CSRF

**Fichier :** `apps/api/app/core/deps.py:20`

```python
token = credentials.credentials if credentials else access_token
if not token:
    raise HTTPException(status_code=401, detail="Missing authentication token")
```

**Probleme :** l'API accepte un JWT depuis le cookie `optiflow_token` pour les routes authentifiees, et les mutations frontend utilisent `credentials: "include"` sans jeton CSRF dedie. `SameSite=Strict` limite le risque cross-site classique, mais une future relaxation cookie, un sous-domaine compromis ou une mutation appelee same-site gardent une surface CSRF inutile.

**Recommandation :** ajouter un double-submit CSRF token pour les routes state-changing en cookie-auth, ou imposer le bearer token pour les mutations API sensibles.

**Impact pour Claude :** un assistant peut conclure "CSRF OK" en voyant `SameSite=Strict`, sans noter la dependance forte a ce choix de cookie.

### 12. Upload de document possible avec un `case_id` d'un autre tenant

**Fichier :** `apps/api/app/services/document_service.py:37`

```python
key = f"{tenant_id}/{case_id}/{uuid.uuid4()}_{safe_filename}"
storage.upload_fileobj(file.file, bucket, key, content_type=file.content_type)
```

**Probleme :** `upload_document` stocke le document avec `tenant_id` courant et `case_id` fourni, mais ne verifie pas que le dossier appartient au meme tenant. La fuite directe est limitee par les filtres tenant, mais l'integrite relationnelle peut etre corrompue et les cascades devenir surprenantes.

**Recommandation :** verifier `Case.id == case_id` et `Case.tenant_id == tenant_id` avant upload, ou ajouter une contrainte composite tenant/case au modele.

**Impact pour Claude :** la presence d'un `tenant_id` dans le chemin de stockage donne une impression d'isolation complete alors que la relation `case_id` reste non validee.

### 13. Les scans Trivy image sont en mode rapport uniquement

**Fichier :** `.github/workflows/security-scan.yml:31`

```yaml
severity: "CRITICAL,HIGH"
exit-code: "0"
format: "sarif"
```

**Probleme :** les vulnerabilites critiques/hautes dans les images Docker sont remontees en SARIF mais ne bloquent pas les branches ni les pull requests. Une image vulnerable peut donc etre livree avec une CI verte.

**Recommandation :** garder le rapport SARIF planifie si necessaire, mais ajouter un job bloquant sur PR/push pour les CVE fixables critiques et hautes.

**Impact pour Claude :** la presence d'un workflow de scan peut masquer le fait qu'il n'a aucun effet de gate.

## 🟢 Nice-to-have

### 1. Le bootstrap SQL manuel est obsolete face aux migrations Alembic

**Fichier :** `apps/api/sql/001_init.sql:1`

```sql
-- Initial database schema for OptiFlow
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

**Probleme :** ce script cree un schema initial partiel qui ne reflete plus les migrations Alembic actuelles, alors que le demarrage production verifie explicitement la tete Alembic. L'executer manuellement peut produire une base incoherente.

**Recommandation :** supprimer ce script, le marquer clairement comme archive non executable, ou le remplacer par une commande documentee `alembic upgrade head`.

**Impact pour Claude :** un assistant peut proposer ce fichier comme chemin d'initialisation rapide alors qu'il est stale.

### 2. La politique de taille imposee par `CLAUDE.md` n'est pas respectee

**Fichier :** `CLAUDE.md:224`

```markdown
- Fonctions > 50 lignes
- Fichiers > 300 lignes
```

**Probleme :** plusieurs fichiers depassent 300 lignes (`routers/ai.py`, `facture_service.py`, `integrations/cosium/client.py`) et plusieurs fonctions depassent 100 lignes (`export_fec`, `client_merge_service`, `erp_sync_invoices`). La consigne locale n'est donc plus un garde-fou fiable.

**Recommandation :** soit assouplir `CLAUDE.md` avec une limite realiste et des exceptions, soit planifier des extractions ciblees dans les services les plus longs.

**Impact pour Claude :** Claude peut refuser ou sur-decouper des changements pour satisfaire une regle que le code existant viole deja.

### 3. `.dockerignore` API ne protege pas les futurs fichiers `.env`

**Fichier :** `apps/api/.dockerignore:1`

```dockerignore
__pycache__/
*.pyc
*.pyo
```

**Probleme :** le contexte Docker API exclut les caches et artefacts courants, mais pas `.env`, `.env.*` ni les fichiers de secrets locaux. Le risque est limite aujourd'hui parce que le build part de `apps/api`, mais un futur `.env` local dans ce dossier serait embarque.

**Recommandation :** ajouter `.env`, `.env.*`, `*.pem`, `*.key` et documents de secret au `.dockerignore` API, comme defense en profondeur.

**Impact pour Claude :** un assistant peut ajouter un fichier de test local dans `apps/api` sans realiser qu'il entre dans le contexte Docker.

### 4. Les variables d'environnement pool SQL ne sont pas documentees

**Fichier :** `apps/api/app/core/config.py:73`

```python
database_pool_size: int = 10
database_max_overflow: int = 20
database_pool_recycle_seconds: int = 1800
```

**Probleme :** les reglages de pool SQL existent dans le code mais pas dans `.env.example`, `.env.prod.example` ni `docs/ENV.md`. Les incidents de saturation DB seront donc plus difficiles a diagnostiquer et reproduire.

**Recommandation :** ajouter ces variables aux exemples et au runbook, avec valeurs recommandees pour API web, worker Celery et tests.

**Impact pour Claude :** Claude peut modifier le pool dans le code au lieu de proposer un tuning par environnement.

### 5. `sync_all` degrade silencieusement les erreurs de factures

**Fichier :** `apps/api/app/tasks/sync_tasks/_sync_all.py:54`

```python
except Exception as exc:  # noqa: BLE001
    logger.warning("invoice_sync_failed", extra={"tenant_id": str(tenant_id), "error": str(exc)})
```

**Probleme :** une erreur sur la synchronisation factures est seulement loggee en warning puis la tache globale continue avec un statut `success`. Les alertes d'exploitation peuvent donc manquer une panne partielle importante.

**Recommandation :** retourner un statut partiel explicite, incrementer une metrique d'echec, et faire echouer la tache si la synchronisation factures est contractuellement obligatoire.

**Impact pour Claude :** un assistant peut se fier au succes Celery sans inspecter les logs secondaires.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **Memoire locale versionnee** : `.claude-memory/project_test_env.md` est suivi par Git et contient des instructions operationnelles sensibles; ne pas le traiter comme simple brouillon local.
- **Alembic est obligatoire au boot** : `apps/api/start.prod.sh:27` lance `alembic upgrade head`, et `apps/api/app/main.py:59` refuse de demarrer en production si les migrations ne sont pas a jour.
- **`CELERY_WORKER` change le comportement SQL** : `apps/api/app/db/session.py:9` passe le `statement_timeout` de 30s a 120s uniquement si `CELERY_WORKER=true`; beat ou jobs lances autrement peuvent garder le timeout court.
- **Reseau Docker externe requis** : `docker-compose.yml` depend de `vps-net` externe; `README.md:30` demande de le creer avant `docker compose up`.
- **Proxy IP critique pour le rate limiting** : `TRUSTED_PROXIES` doit inclure nginx en production, sinon le rate limiter groupe les clients derriere l'IP du proxy.
- **Cosium doit rester read-only** : `apps/api/app/integrations/cosium/client.py` documente que seuls GET et auth POST sont autorises; les tests de regression verifient l'absence de POST/PUT/PATCH/DELETE metier.
- **Reset password couple a CORS** : sans `FRONTEND_BASE_URL`, le premier `CORS_ORIGINS` devient l'origine des liens email.
- **MinIO interne n'est pas public** : `S3_ENDPOINT=http://minio:9000` marche entre conteneurs, pas comme URL de redirection navigateur.
- **Stripe webhook depend du corps brut** : `billing.py` passe `await request.body()` a la verification de signature; tout middleware qui parse/transforme le corps avant peut casser la validation.
- **Horaires Celery en Europe/Paris** : `apps/api/app/tasks/__init__.py:74` fixe la timezone beat, donc les crons ne sont pas en UTC.

## ✨ Ameliorations proposees

Non bloquant mais gain qualite / DX :

- **Secret hygiene** : ajouter Gitleaks ou TruffleHog en CI bloquant et documenter une procedure de rotation.
- **Contrats d'environnement** : generer `.env.example` depuis `Settings` ou ajouter un test qui compare les variables code/docs.
- **Tests billing** : couvrir `create_checkout_session` + webhook avec metadata plan, subscription id et cas d'echec signature.
- **Idempotence atomique** : extraire un petit helper Redis `acquire_idempotency_key` teste avec concurrence.
- **Schema invariants** : ajouter des contraintes DB pour les invariants metier documentes, notamment `cosium_id` par tenant.
- **Observabilite sync** : distinguer succes total, succes partiel et echec dans les taches Cosium.
- **Telechargements documents** : proxyfier les downloads S3 via API ou exposer un domaine public HTTPS dedie.
- **CI security gate** : faire echouer les PR sur CVE fixables critiques/hautes pour Python, npm et images Docker.

## Conclusion

Priorite haute : traiter les secrets versionnes, clarifier la terminaison TLS production et supprimer les ignores CVE non justifies. Ensuite, verrouiller les chemins metier a impact client direct : plan Stripe, idempotence des creations, invariants Cosium et URLs de documents. Score global subjectif : 6/10, avec une base technique exploitable mais des risques operationnels et de securite qui doivent etre corriges avant de considerer la production robuste.
