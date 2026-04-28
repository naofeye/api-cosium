# Audit Codex — api-cosium

_Genere automatiquement le 2026-04-28. Commit audite : `13000b1`._

## Resume

Le depot est structure et largement teste, mais plusieurs defauts restent exploitables. Le point le plus severe est un risque de deni de service par upload, car les fichiers sont lus integralement en memoire avant tout controle de taille. J'ai aussi releve plusieurs ecarts de securite ou d'operabilite autour des liens de reset, du guard frontend, des URLs S3 presignees et de la gestion des erreurs de cleanup. Les priorites sont donc : 1) bloquer les uploads oversize avant buffering, 2) corriger la generation des URLs externes, 3) fiabiliser les garde-fous auth et les chemins d'erreur.

## 🔴 Critiques

### 1. Limite de taille appliquee apres lecture complete du fichier

**Fichier :** `apps/api/app/api/routers/documents.py:41`

```python
file_data = await file.read()
return document_service.upload_document(
    db,
```

**Probleme :** le backend charge tout le corps multipart en RAM avant le controle `MAX_UPLOAD_SIZE_MB` effectue plus bas dans `document_service`. Un attaquant peut envoyer un fichier tres volumineux et faire exploser la memoire du worker avant que la validation applicative ne s'execute. Le meme anti-pattern existe aussi sur l'upload d'avatar (`apps/api/app/api/routers/clients.py:243`).

**Recommandation :** imposer la limite au plus tot dans la chaine : `Content-Length` strict, streaming par chunks, abort immediat si seuil depasse, et limite coherente au niveau reverse proxy et FastAPI.

**Impact pour Claude :** un assistant qui ne lit que le service verra la validation de taille et pourra conclure a tort que le risque est deja traite.

## 🟡 Moyens

### 1. Les liens de reset utilisent le premier CORS origin comme URL frontend

**Fichier :** `apps/api/app/services/auth_service.py:258`

```python
frontend_origin = settings.cors_origins.split(",")[0].strip()
reset_url = f"{frontend_origin}/reset-password?token={raw_token}"
```

**Probleme :** le lien de reinitialisation depend de l'ordre de `CORS_ORIGINS`, pas d'une URL frontend dediee. En multi-domaines ou avec un premier origin interne/local, les emails peuvent pointer vers le mauvais host. Le token brut de reset est alors envoye vers un domaine non prevu.

**Recommandation :** introduire une variable explicite du type `FRONTEND_PUBLIC_URL` et construire tous les liens email a partir de cette valeur unique.

**Impact pour Claude :** la variable parait optionnelle tant que `CORS_ORIGINS` fonctionne en local, alors qu'en prod elle devient de fait une dependance de securite.

### 2. Le guard frontend fait confiance a la simple presence du cookie JWT

**Fichier :** `apps/web/src/middleware.ts:33`

```ts
const token = request.cookies.get("optiflow_token")?.value;
if (!token && !isPublicPage) {
  return NextResponse.redirect(new URL("/login", request.url));
}
```

**Probleme :** n'importe quelle valeur de cookie `optiflow_token` suffit a passer le middleware Next.js. Un utilisateur peut donc contourner le redirect vers `/login` et charger les pages privees cote web, meme si les appels API echoueront ensuite en 401. Cela degrade l'isolation UI et rend le comportement trompeur.

**Recommandation :** soit verifier la session via un endpoint serveur leger, soit baser le guard sur un cookie secondaire signe/opaque dedie au frontend, soit deplacer la protection sur des layouts server-side qui verifient effectivement la session.

**Impact pour Claude :** le cookie est `httpOnly`, ce qui peut donner une fausse impression de robustesse alors que la valeur n'est jamais validee ici.

### 3. Les URLs presignees renvoyees au navigateur heritent de l'endpoint S3 interne

**Fichier :** `apps/api/app/integrations/storage.py:66`

```python
url = self._client.generate_presigned_url(
    "get_object",
    Params=params,
```

**Probleme :** les routes de download/avatar renvoient une redirection vers l'URL presignee brute. Or l'exemple versionne configure `S3_ENDPOINT=http://minio:9000`, un hostname Docker interne. Sans endpoint public distinct, les documents et avatars seront rediriges vers une adresse inaccessible depuis le navigateur.

**Recommandation :** separer endpoint interne S3 et URL publique, ou servir les fichiers via un proxy applicatif/nginx plutot que via une redirection directe sur l'endpoint interne.

**Impact pour Claude :** le bug ne saute pas aux yeux tant qu'on lit seulement l'API ; il apparait en recollant `storage.py`, `documents.py` et la config `.env.example`.

### 4. Le cleanup d'un upload orphelin peut masquer l'erreur SQL d'origine

**Fichier :** `apps/api/app/services/document_service.py:98`

```python
except SQLAlchemyError:
    try:
        storage.delete_file(bucket=settings.s3_bucket, key=storage_key)
```

**Probleme :** `storage.delete_file()` releve un `BusinessError` sur erreur S3, mais le `except` ne capture que `ConnectionError`, `TimeoutError` et `OSError`. Si la suppression du fichier echoue, l'exception de cleanup remplace l'exception SQL initiale et complique fortement le diagnostic.

**Recommandation :** attraper explicitement `BusinessError` ici, journaliser l'echec de cleanup, puis relancer l'exception SQL initiale sans la masquer.

**Impact pour Claude :** le commentaire promet une suppression d'orphelin "best effort", mais le type d'exception reel vient d'un autre module et casse cette hypothese.

### 5. Le pipeline de securite ignore explicitement un CVE applicatif encore present

**Fichier :** `.github/workflows/ci.yml:98`

```yaml
#   - CVE-2025-62727 (starlette) : embed FastAPI 0.116, upgrade necessite FastAPI compatible
cd apps/api && pip-audit -r requirements.txt --strict \
  --ignore-vuln CVE-2025-62727
```

**Probleme :** le workflow de securite neutralise volontairement un CVE touchant Starlette, transitif via `fastapi==0.116.1`. Le build repasse donc au vert meme si la dependance prod reste vulnerable.

**Recommandation :** documenter le risque residual, pinner une combinaison FastAPI/Starlette saine des qu'elle existe, ou isoler formellement les surfaces exposees tant que le correctif n'est pas deploye.

**Impact pour Claude :** un assistant qui se fie seulement au badge CI conclura que le scan dependances est strict, alors qu'il est partiellement contourne.

## 🟢 Nice-to-have

### 1. Le stream S3 n'est pas ferme apres lecture

**Fichier :** `apps/api/app/integrations/storage.py:76`

```python
response = self._client.get_object(Bucket=bucket, Key=key)
return response["Body"].read()
```

**Probleme :** le body de reponse boto3 n'est pas ferme explicitement. Sous charge, cela peut garder des connexions HTTP ouvertes inutilement et epuiser le pool.

**Recommandation :** lire le body dans un `try/finally` puis appeler `response["Body"].close()`.

**Impact pour Claude :** faible a froid, mais cumulatif sur des workers OCR/export qui telechargent beaucoup de fichiers.

### 2. Le endpoint `/api/v1/metrics` est bloque par sa propre config nginx

**Fichier :** `config/nginx/nginx.conf:74`

```nginx
location /api/v1/metrics {
    allow 127.0.0.1;
    deny all;
    return 403;
}
```

**Probleme :** `return 403;` s'execute de toute facon, meme pour `127.0.0.1`. Le scraping Prometheus via nginx ne peut donc jamais fonctionner tel quel.

**Recommandation :** remplacer `return 403;` par un `proxy_pass http://api;` conditionne par `allow/deny`, ou faire scraper Prometheus directement sur l'API.

**Impact pour Claude :** l'intention du commentaire est bonne, mais l'ordre d'evaluation nginx annule la protection attendue.

### 3. Le middleware Next.js applique une CSP image trop stricte pour les medias rediriges

**Fichier :** `apps/web/src/middleware.ts:23`

```ts
"img-src 'self' data: blob:",
`connect-src 'self' ${apiOrigin} https://c1.cosium.biz`,
```

**Probleme :** si les avatars/documents continuent d'etre servis par redirection vers une origine S3/MinIO distincte, cette CSP bloquera aussi leur affichage dans le navigateur.

**Recommandation :** soit servir les medias via meme origine, soit declarer explicitement l'origine publique des assets dans `img-src`.

**Impact pour Claude :** ce point reste invisible tant qu'on ne relie pas la CSP frontend au mecanisme de presigned URL backend.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **Reseau Docker externe obligatoire** : le premier `docker compose up` echoue sans creation prealable de `interface-ia-net` (`README.md`).
- **Migrations bloquantes au boot** : en `production/staging`, l'API refuse de demarrer si Alembic n'est pas a `head` (`apps/api/app/main.py`).
- **URL de reset dependante du CORS** : l'ordre des valeurs dans `CORS_ORIGINS` change effectivement le domaine des emails de reset (`apps/api/app/services/auth_service.py`).
- **Endpoint S3 doit etre publiquement resolvable** : `S3_ENDPOINT` ne sert pas qu'au trafic backend, il fuit aussi dans les URLs presignees consommees par le navigateur.
- **Volume Beat critique** : la persistance `celerybeat_schedule` evite de redeclencher des taches planifiees apres restart (`docker-compose.yml`).

## ✨ Ameliorations proposees

Non bloquant mais gain qualite / DX :

- **Streaming upload unifie** : factoriser documents + avatars sur un helper commun qui valide MIME, taille et magic bytes en flux ; cela supprime le doublon et ferme la faille DoS.
- **URL publiques explicites** : ajouter `FRONTEND_PUBLIC_URL` et `S3_PUBLIC_BASE_URL` pour sortir la logique d'URL des variables internes de transport.
- **Session guard cote serveur** : centraliser la verification de session dans un endpoint court ou un layout server-side pour eviter les divergences entre middleware Next et API FastAPI.
- **Durcissement CI dependances** : remonter les CVE ignorees dans un job separé "accepted risk" avec date d'expiration pour eviter qu'elles deviennent invisibles.
- **Tests d'erreur storage** : ajouter des tests couvrant echec de cleanup S3, presigned URL publique, et uploads > limite avant buffering.

## Conclusion

Priorite immediate : corriger le buffering des uploads et sortir les URLs publiques des configs internes. Ensuite, fiabiliser les flux auth annexes (reset password, guard frontend) et les chemins d'erreur storage. Score global subjectif : **6/10** — base solide et relativement disciplinee, mais encore quelques defauts transverses qui toucheront directement la securite ou l'exploitabilite en production.
