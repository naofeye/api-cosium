# Audit Codex — api-cosium

_Genere automatiquement le 2026-05-03. Commit audite : `91f85e3`._

## Resume

Le depot est structure et contient deja des garde-fous importants (CSRF, cookies `Secure`, audit CI, tests nombreux), mais deux risques doivent etre traites en priorite : les webhooks permettent une sortie reseau arbitraire depuis le worker, et un `.env` local contient des secrets de production en clair. Les risques moyens les plus exploitables concernent l'idempotence incomplete des operations financieres, la signature publique de devis expires, l'usurpation d'IP dans l'audit de signature, et des divergences entre configuration, docs et runtime. Les audits `npm audit` ne remontent rien en production, mais `pip-audit` detecte encore des CVE ignorees temporairement en CI.

## 🔴 Critiques

### 1. Webhooks exploitables en SSRF depuis le worker

**Fichier :** `apps/api/app/tasks/webhook_tasks.py:84`

```python
with httpx.Client(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
    response = client.post(sub.url, content=body, headers=headers)
    last_status_code = response.status_code
```

**Probleme :** les abonnements webhook acceptent une URL utilisateur via `HttpUrl` sans filtrage reseau, puis le worker poste directement vers cette URL. Comme le worker tourne sur les reseaux Docker `internal` et `public`, une URL vers `localhost`, `api`, `postgres`, `minio`, une IP RFC1918/link-local ou une redirection vers ces plages peut transformer la fonctionnalite webhook en SSRF interne.

**Recommandation :** imposer HTTPS, resoudre le DNS avant envoi, refuser loopback/private/link-local/multicast/metadata, refuser ou revalider les redirects, et ajouter des tests avec `localhost`, `127.0.0.1`, `10.0.0.0/8`, `169.254.169.254`, `api:8000` et `minio:9000`.

**Impact pour Claude :** un assistant risque de voir seulement le type `HttpUrl` et de conclure que l'URL est valide, sans prendre en compte la topologie Docker ni les redirections DNS/HTTP.

### 2. Secrets de production presents en clair dans `.env`

**Fichier :** `.env:9`

```dotenv
S3_SECRET_KEY=<redacted>
JWT_SECRET=<redacted>
ENCRYPTION_KEY=<redacted>
```

**Probleme :** le workspace contient un fichier `.env` non suivi par Git mais utilise par `docker-compose.yml`, avec des secrets applicatifs, S3, JWT, chiffrement et base de donnees en clair. Meme si le fichier est ignore par Git, il reste exposable via sauvegardes, copies de serveur, commandes de diagnostic ou partage involontaire du repertoire.

**Recommandation :** considerer ces secrets comme compromis si l'environnement a ete partage, les renouveler, stocker les valeurs dans un gestionnaire de secrets ou les secrets CI/CD, conserver uniquement `.env.example` dans le repo, et ajouter un scan de secrets sur le workspace complet avant livraison.

**Impact pour Claude :** un audit limite a `git ls-files` manquerait ce fichier, alors que le deploiement Compose s'appuie explicitement dessus.

## 🟡 Moyens

### 1. Les mutations front-end n'envoient pas de cle d'idempotence

**Fichier :** `apps/web/src/app/devis/new/page.tsx:97`

```typescript
const resp = await fetchJson<{ id: number }>("/devis", {
  method: "POST",
  body: JSON.stringify(data),
});
```

**Probleme :** le backend active l'idempotence seulement si `X-Idempotency-Key` est present, mais les creations de devis, factures et avoirs cote front n'envoient pas cet en-tete. Un double clic, un retry navigateur ou une reconnexion peut donc creer des doublons sur des operations financieres.

**Recommandation :** ajouter un helper de mutation qui genere une cle stable par soumission de formulaire, l'utiliser pour les routes critiques, et rendre l'en-tete obligatoire cote API sur les endpoints financiers.

**Impact pour Claude :** la presence du module backend `idempotency.py` peut masquer le fait que le client principal ne l'utilise pas.

### 2. Redis indisponible desactive silencieusement l'idempotence

**Fichier :** `apps/api/app/core/redis_cache.py:84`

```python
r = _get_redis()
if not r:
    return True
```

**Probleme :** `cache_set_nx()` retourne `True` quand Redis est indisponible. Pour les endpoints proteges par idempotence, cela revient a autoriser toutes les requetes concurrentes au moment precis ou le verrou distribue n'existe plus.

**Recommandation :** en production, echouer ferme sur les endpoints idempotents si Redis est indisponible, ou persister les cles dans une table dediee avec contrainte unique et TTL.

**Impact pour Claude :** le nom `cache_set_nx` suggere une operation atomique, mais le fallback modifie la semantique de securite.

### 3. Un devis expire peut encore etre signe via le lien public

**Fichier :** `apps/api/app/services/devis_signature_service.py:114`

```python
if devis.status in {"signe", "facture"}:
    raise BusinessError("Ce devis a deja ete signe")
if devis.status in {"refuse", "annule"}:
```

**Probleme :** la signature publique rejette `signe`, `facture`, `refuse` et `annule`, mais pas `expire`, et ne verifie pas `valid_until` au moment de signer. Si le cron d'expiration n'a pas encore tourne, ou si un devis est deja `expire`, le token public peut encore produire une signature.

**Recommandation :** refuser explicitement `expire`, verifier `valid_until < now` dans `get_devis_public()` et `sign_devis_public()`, et ajouter un test de regression sur un devis expire mais encore muni d'un `public_token`.

**Impact pour Claude :** l'expiration est deplacee dans une tache Celery, donc un assistant peut oublier que la route publique doit aussi proteger l'invariant metier.

### 4. L'IP d'audit de signature publique est falsifiable

**Fichier :** `apps/api/app/api/routers/devis_signature.py:91`

```python
client_ip = (
    request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    or (request.client.host if request.client else "")
```

**Probleme :** une route publique non authentifiee lit directement `X-Forwarded-For`. Un client peut donc forger `signature_ip`, qui devient une donnee d'audit potentiellement utilisee comme preuve de signature.

**Recommandation :** ne faire confiance a `X-Forwarded-For` que si `request.client.host` appartient a `TRUSTED_PROXIES`, reutiliser la logique deja presente pour le rate limiting, et tester le cas proxy non approuve.

**Impact pour Claude :** le header semble standard en environnement proxy, mais il n'a de valeur probante que s'il est borne par une liste de proxies fiables.

### 5. L'API publique expose les clients soft-deletes par identifiant

**Fichier :** `apps/api/app/api/routers/public_v1.py:86`

```python
customer = db.scalars(
    select(Customer).where(
        Customer.id == client_id, Customer.tenant_id == ctx.tenant_id
```

**Probleme :** la liste publique filtre `Customer.deleted_at.is_(None)`, mais le detail par ID ne le fait pas. Un partenaire muni de `read:clients` peut donc recuperer un client supprime logiquement s'il connait ou devine son identifiant.

**Recommandation :** ajouter le filtre `Customer.deleted_at.is_(None)` au detail, aligner les tests liste/detail, et verifier les autres endpoints publics avec soft delete.

**Impact pour Claude :** l'invariant est visible sur la route liste, mais pas centralise dans un repository ou une policy partagee.

### 6. `logout-all` ne revoque pas les access tokens deja emis sur les autres appareils

**Fichier :** `apps/api/app/api/routers/auth.py:227`

```python
# de l'utilisateur, il faudrait un token_version par user — feature TODO.
access_tok = request.cookies.get("optiflow_token")
if access_tok:
```

**Probleme :** la route revoque tous les refresh tokens mais blackliste uniquement l'access token du navigateur courant. Les access tokens des autres appareils restent valides jusqu'a expiration, alors qu'une route separee sait deja incrementer `token_version`.

**Recommandation :** factoriser la logique de revocation globale et incrementer `user.token_version` dans `logout-all`, puis ajouter un test multi-session.

**Impact pour Claude :** le nom de route donne une garantie plus forte que son implementation reelle.

### 7. Le corps S3 n'est pas ferme apres lecture

**Fichier :** `apps/api/app/integrations/storage.py:83`

```python
response = self._client.get_object(Bucket=bucket, Key=key)
return response["Body"].read()
```

**Probleme :** `StreamingBody` n'est pas ferme explicitement. Sous charge OCR/import/export, des connexions HTTP vers S3/MinIO peuvent rester ouvertes plus longtemps que necessaire et epuiser le pool.

**Recommandation :** fermer le body dans un `finally` ou utiliser `contextlib.closing(response["Body"])`, puis ajouter un test avec un faux body qui verifie `close()`.

**Impact pour Claude :** la lecture en memoire semble simple, mais boto3 retourne un stream reseau qui a un cycle de vie propre.

### 8. Deux CVE Python restent ignorees en CI

**Fichier :** `.github/workflows/ci.yml:140`

```yaml
cd apps/api && pip-audit -r requirements.txt --strict \
  --ignore-vuln CVE-2025-71176 \
  --ignore-vuln CVE-2025-62727
```

**Probleme :** `pip-audit` detecte encore `pytest==8.4.2` vulnerable a CVE-2025-71176 et `starlette==0.47.3` vulnerable a CVE-2025-62727 via `fastapi==0.116.1`. Le workflow documente une tolerance temporaire jusqu'au 2026-06-15, mais le risque est reporte sans garde supplementaire.

**Recommandation :** monter `pytest` vers une version corrigee et planifier l'upgrade FastAPI/Starlette, puis supprimer les deux exceptions CI avant la date d'expiration.

**Impact pour Claude :** un audit qui lit seulement `requirements.txt` ne voit pas que le pipeline masque explicitement ces CVE.

### 9. CORS de production peut accepter une origine HTTP non locale

**Fichier :** `apps/api/app/core/config.py:136`

```python
if "*" in self.cors_origins:
    errors.append("CORS_ORIGINS ne doit pas contenir '*' en production")
```

**Probleme :** la validation production interdit `*`, mais n'interdit pas `http://` hors localhost alors que CORS est credentialed. Un front servi en HTTP peut exposer les cookies et reponses API a une interception reseau.

**Recommandation :** refuser `http://` en production sauf `localhost`/`127.0.0.1`, transformer le warning de `scripts/validate-prod.sh` en erreur, et ajouter un test de configuration.

**Impact pour Claude :** la presence d'une validation CORS donne une impression de couverture complete, alors qu'elle ne verifie qu'un seul cas dangereux.

## 🟢 Nice-to-have

### 1. Le scan Trivy des images est en mode informatif

**Fichier :** `.github/workflows/security-scan.yml:31`

```yaml
- name: Trivy vulnerability scan
  uses: aquasecurity/trivy-action@0.28.0
  with:
```

**Probleme :** le job configure `severity: "CRITICAL,HIGH"` mais aussi `exit-code: "0"`, donc une image avec CVE haute ou critique ne bloque jamais la CI.

**Recommandation :** passer `exit-code` a `1` au moins sur les images de branche principale, avec une allowlist documentee pour les faux positifs.

**Impact pour Claude :** le nom du workflow suggere un controle bloquant, mais le resultat est seulement report-only.

### 2. Le composant d'administration webhooks est trop volumineux

**Fichier :** `apps/web/src/app/admin/webhooks/page.tsx:75`

```typescript
export default function WebhooksAdminPage() {
  const { data: subs, error: subsError, isLoading: subsLoading } =
    useSWR<Subscription[]>("/webhooks/subscriptions", fetcher);
```

**Probleme :** ce composant depasse 600 lignes et concentre chargement SWR, formulaires, rendu, filtres, modales et actions. Cela rend les changements de securite webhook plus risques et limite la couverture de tests unitaires ciblee.

**Recommandation :** extraire les formulaires, la table des livraisons et les hooks d'actions dans des composants/modules dedies, puis tester la validation URL independamment du rendu complet.

**Impact pour Claude :** les invariants de formulaire peuvent etre perdus dans un gros fichier UI difficile a parcourir entierement.

### 3. CSP front-end conserve `unsafe-inline` en production

**Fichier :** `apps/web/src/middleware.ts:17`

```typescript
const scriptSrc = [
  "'self'",
  "'unsafe-inline'",
```

**Probleme :** la CSP reduit certains risques mais garde les scripts inline autorises en production. Si une injection HTML apparait ailleurs, cette directive facilite l'escalade en XSS executable.

**Recommandation :** evaluer une CSP avec nonce/hash pour les scripts necessaires a Next.js, garder `unsafe-eval` limite au dev, et ajouter un test de header sur une route representative.

**Impact pour Claude :** la CSP existe, donc un assistant peut la cocher comme presente sans regarder la force effective des directives.

### 4. La file Celery `dlq` est documentee mais pas consommee

**Fichier :** `docker-compose.yml:156`

```yaml
command: celery -A app.tasks worker --loglevel=info --concurrency=2 -Q default,email,sync,extraction,batch,reminder
env_file: [.env]
environment:
```

**Probleme :** le code indique que le worker doit etre lance avec `...,dlq`, mais la commande Compose n'inclut pas cette queue. Les taches dead-letter peuvent donc rester non traitees ou invisibles selon le routage effectif.

**Recommandation :** aligner la commande Compose avec `apps/api/app/tasks/__init__.py`, ou retirer/commenter la DLQ si elle n'est pas encore operationnelle.

**Impact pour Claude :** le commentaire dans le code et l'orchestration divergent, et seul le compose decide du comportement reel en production.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **`.env` non suivi mais actif** : le fichier est ignore par Git, mais `docker-compose.yml` le charge pour `api`, `web`, `worker` et `beat`; un audit purement Git manquerait les secrets reels.
- **`S3_PUBLIC_ENDPOINT` quasi obligatoire** : `apps/api/app/integrations/storage.py` ne remplace l'endpoint interne MinIO que si cette variable est definie; sinon des URLs presignees peuvent pointer vers `http://minio:9000`.
- **Topologie webhook** : le worker a acces aux reseaux Docker interne et public; la validation URL doit tenir compte de Docker DNS, IP privees et redirects, pas seulement du schema HTTP.
- **Expiration devis asynchrone** : la tache Celery marque les devis expires quotidiennement, mais les routes publiques doivent proteger `valid_until` en temps reel.
- **`TRUSTED_PROXIES` conditionne plusieurs garanties** : sans cette variable, IP d'audit, rate limiting et logs derriere proxy peuvent etre faux meme si l'application demarre.
- **Seed production trompeur** : `SEED_ON_STARTUP=true` dans l'environnement ne seed pas en production car le code limite le seed a `local/development`.
- **DLQ Celery non alignee** : `apps/api/app/tasks/__init__.py` mentionne `dlq`, mais `docker-compose.yml` ne lance pas le worker sur cette queue.
- **Doc API token divergente** : `apps/api/app/api/routers/public_v1.py` mentionne `X-API-Token`, alors que l'auth publique lit `Authorization: Bearer`.

## ✨ Ameliorations proposees

Non bloquant mais gain qualite / DX :

- **Centraliser les mutations idempotentes** : fournir un helper `mutateJson()` cote web qui gere CSRF, idempotency key, erreurs typées et retries.
- **Durcir la validation production** : transformer en erreurs les origines CORS HTTP, l'absence de `S3_PUBLIC_ENDPOINT` et les secrets encore aux valeurs d'exemple.
- **Extraire les policies d'acces** : regrouper soft delete, tenant scoping et scopes partenaires dans des repositories/policies pour eviter les oublis route par route.
- **Automatiser la rotation de secrets** : documenter une procedure courte de rotation JWT, encryption key, S3 et DB avec fenetres d'invalidation explicites.
- **Rendre les scans bloquants graduellement** : activer Trivy bloquant sur `main`, garder les exceptions CVE dans un fichier date et proprietaire, et echouer apres expiration.
- **Reduire les gros fichiers UI/API** : cibler d'abord `apps/web/src/app/admin/webhooks/page.tsx` et les services Python de plus de 150 lignes pour faciliter les revues futures.

## Conclusion

Priorite recommandee : fermer le SSRF webhook et sortir les secrets du workspace, puis corriger l'idempotence des operations financieres et les routes publiques de signature/client. Le socle est exploitable et bien teste sur plusieurs axes, mais quelques invariants critiques restent disperses entre frontend, backend, jobs Celery et Compose. Score subjectif : 6.5/10 aujourd'hui, avec un potentiel rapide vers 8/10 apres les correctifs de configuration, idempotence et exposition reseau.
