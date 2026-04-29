## Post-audit update — 2026-04-29

Les items suivants ont été corrigés depuis le dernier audit Codex :

- ✅ Nginx H2C smuggling fix + correction héritage security headers — commit `348fe5a`
- ✅ ai.py 344→252L split en service dédié — commit `bb6f6a3`
- ✅ Next.js 15→16 + TypeScript 5→6 upgrade — commit `93eaff6`
- ✅ E2E Playwright cookie race condition fixé (router.push → window.location.href) — commit `770c03c`
- ✅ 26 tests frontend ajoutés (176→202 total) — commit `7b28945`
- ✅ Backfill script déplacé vers scripts/ + DOC API gitignorée — commit `eb1ba6a`

**Score estimé après corrections : 7.5/10**

---

# Audit Codex — api-cosium

_Genere automatiquement le 2026-04-28. Commit audite : `bc574b2`._

## Resume

Le dépôt est riche en garde-fous (cookies `HttpOnly`, validation Pydantic, séparation tenant), mais plusieurs défauts concrets restent bloquants sur le parcours réel et l’exploitation prod. Les deux priorités sont 1) la route publique d’inscription qui renvoie encore des tokens bruts sans poser de cookies de session, et 2) l’upload de documents qui lit le fichier complet en mémoire avant d’appliquer la limite de taille. Côté exploitation, la supervision Prometheus est actuellement cassée par nginx, et le pipeline CI masque explicitement une CVE Starlette connue. Les docs/env de prod laissent aussi un angle mort important sur `TRUSTED_PROXIES`, ce qui dégrade le rate limiting derrière nginx.

## 🔴 Critiques

### 1. L’inscription publique renvoie access/refresh tokens en JSON sans poser de cookies

**Fichier :** `apps/api/app/api/routers/onboarding.py:20`

```py
@router.post(
    "/signup",
    response_model=TokenResponse,
)
```

**Probleme :** `TokenResponse` contient `access_token` et `refresh_token` en corps JSON, contrairement au flux `/auth/login` qui les place en cookies `HttpOnly`. Le frontend d’onboarding ne consomme pas ces tokens et passe directement à `StepCosium`, qui appelle un endpoint protégé (`/onboarding/connect-cosium`) sans cookie de session. Résultat: l’inscription réussit côté API, les secrets de session sont exposés au JavaScript client, puis l’étape 2 échoue en 401 dans le navigateur.

**Recommandation :** Aligner `/onboarding/signup` sur `/auth/login`: poser les cookies serveur-side, répondre avec un `LoginResponse` sans tokens, et couvrir le flux `signup -> connect-cosium` par un test E2E navigateur.

**Impact pour Claude :** Un assistant peut voir un `201` et un schéma valide sans remarquer que le parcours réel casse dès l’étape suivante, car le bug n’apparaît qu’en présence des cookies navigateur.

### 2. L’upload lit le fichier complet en RAM avant de vérifier la taille maximale

**Fichier :** `apps/api/app/api/routers/documents.py:41`

```py
file_data = await file.read()
return document_service.upload_document(
```

**Probleme :** La limite `MAX_UPLOAD_SIZE_MB` n’est vérifiée qu’ensuite dans `document_service.upload_document()`. Un utilisateur authentifié avec le droit `document:create` peut donc envoyer un multipart très volumineux: FastAPI charge d’abord tout le corps en mémoire, puis seulement ensuite rejette le fichier. C’est un vecteur direct de déni de service mémoire sur l’API/worker.

**Recommandation :** Passer à une lecture par chunks avec arrêt anticipé, imposer une vérification `Content-Length` avant `read()`, et conserver une limite cohérente nginx/FastAPI sans charger l’intégralité du flux en mémoire.

**Impact pour Claude :** Les tests utilisent de petits fixtures et mockent le stockage; le chemin de DoS reste invisible sans revue du flux mémoire complet.

## 🟡 Moyens

### 1. La CI masque explicitement une CVE Starlette connue

**Fichier :** `.github/workflows/ci.yml:98`

```yaml
#   - CVE-2025-71176 (pytest) : dev-only, pas d'exposition prod
#   - CVE-2025-62727 (starlette) : embed FastAPI 0.116, upgrade necessite FastAPI compatible
cd apps/api && pip-audit -r requirements.txt --strict \
```

**Probleme :** Le job `backend-security` ignore volontairement `CVE-2025-62727`, alors que le backend reste aligné sur `fastapi==0.116.1` dans `apps/api/requirements.txt`. Le pipeline repasse donc au vert tout en acceptant un composant vulnérable en production.

**Recommandation :** Mettre à jour vers un couple FastAPI/Starlette corrigé, ou pinner explicitement une version transitive non vulnérable, puis supprimer l’exception `--ignore-vuln CVE-2025-62727`.

**Impact pour Claude :** Un assistant qui se fie à une CI verte peut conclure à tort que le risque dépendances est couvert.

### 2. Le endpoint Prometheus est déclaré mais nginx le bloque toujours en 403

**Fichier :** `config/nginx/nginx.conf:73`

```nginx
location /api/v1/metrics {
    allow 127.0.0.1;
    deny all;
    return 403;
}
```

**Probleme :** Le backend expose bien `/api/v1/metrics` pour Prometheus, mais la location nginx ne proxifie jamais la requête et renvoie systématiquement `403`, y compris depuis localhost. La supervision annoncée dans le code et les commentaires n’est donc pas réellement branchée.

**Recommandation :** Remplacer `return 403;` par un `proxy_pass http://api;` protégé par `allow/deny`, ou réserver le scrape à un réseau interne dédié.

**Impact pour Claude :** La présence du router backend et des fichiers Prometheus donne l’illusion que la télémétrie est active alors qu’elle est coupée au reverse proxy.

### 3. `TRUSTED_PROXIES` est essentiel au rate limit mais absent des exemples/documents de prod

**Fichier :** `apps/api/app/core/config.py:31`

```py
# Trusted proxies (CSV) — IPs autorisees a faire confiance au header X-Forwarded-For
# Vide par defaut : on n'accepte JAMAIS X-Forwarded-For sans config explicite
trusted_proxies: str = ""
```

**Probleme :** Le rate limiter ne prend `X-Forwarded-For` en compte que si `TRUSTED_PROXIES` est renseigné. La variable existe dans `.env.example`, mais elle n’apparaît ni dans `.env.prod.example`, ni dans `.env.production.example`, ni dans `docs/ENV.md`. En prod derrière nginx, toutes les requêtes risquent donc d’être bucketisées sur l’IP du proxy/container, ce qui transforme le rate limiting en coupe-circuit global pour tous les utilisateurs.

**Recommandation :** Ajouter `TRUSTED_PROXIES` aux exemples/docs de production, et faire échouer ou au minimum alerter le boot prod si la variable est vide derrière un reverse proxy.

**Impact pour Claude :** Le piège est facile à manquer parce que l’exemple dev le documente, alors que le chemin prod le perd.

### 4. Les liens de reset de mot de passe sont dérivés du premier `CORS_ORIGINS`

**Fichier :** `apps/api/app/services/auth_service.py:258`

```py
frontend_origin = settings.cors_origins.split(",")[0].strip()
reset_url = f"{frontend_origin}/reset-password?token={raw_token}"
```

**Probleme :** Le lien envoyé par email dépend du premier élément de `CORS_ORIGINS`, pas d’une URL frontend dédiée. En présence de plusieurs origines, d’un ordre mal maintenu ou d’une entrée locale laissée en tête, les utilisateurs reçoivent des liens de reset cassés, internes ou pointant vers le mauvais domaine.

**Recommandation :** Introduire une variable explicite de type `FRONTEND_PUBLIC_URL` et la valider au démarrage pour tous les flux email.

**Impact pour Claude :** Un assistant peut confondre “origine CORS autorisée” et “URL canonique du frontend”, alors que ce sont deux responsabilités distinctes.

## 🟢 Nice-to-have

### 1. La documentation d’environnement annonce `APP_ENV=dev`, mais le runtime n’accepte que `development`

**Fichier :** `docs/ENV.md:15`

```md
| `APP_ENV` | str | `local` | `local`, `dev`, `staging`, `production`, `test` |
```

**Probleme :** `docs/ENV.md` annonce `dev`, alors que `apps/api/app/core/config.py` n’accepte que `development`. Un opérateur qui suit la doc peut provoquer un boot failure immédiat.

**Recommandation :** Harmoniser la documentation et la validation runtime, idéalement en exposant exactement la même liste de valeurs dans les deux endroits.

### 2. Plusieurs dépendances Python critiques restent non figées

**Fichier :** `apps/api/requirements.txt:26`

```txt
rapidfuzz>=3.0.0
pdfplumber>=0.10.0
pytesseract>=0.3.10
```

**Probleme :** Ces bornes basses laissent entrer des versions différentes selon la date du build. Cela réduit la reproductibilité, brouille les audits sécurité et peut introduire des régressions non revues entre deux déploiements “identiques”.

**Recommandation :** Figer toutes les versions prod via un lockfile (`pip-tools`, `uv pip compile`, ou équivalent) et auditer sur ce lock plutôt que sur des ranges ouverts.

### 3. La barrière qualité reste faible pour une surface aussi large

**Fichier :** `apps/api/pyproject.toml:53`

```toml
[tool.coverage.report]
show_missing = true
fail_under = 45
```

**Probleme :** Le dépôt expose beaucoup de routes métier, d’intégrations externes et de chemins auth, mais le seuil de couverture CI reste à 45%. Cela laisse trop de place à des régressions fonctionnelles comme le flux onboarding cassé.

**Recommandation :** Remonter progressivement le seuil, puis cibler d’abord les flux à risque: onboarding complet, reset password, upload volumineux, et chemins admin/tenant.

## 🧠 Angles morts Claude

Elements qu'un assistant IA risque de rater sans cette note :

- **Signup sans cookie** : `POST /api/v1/onboarding/signup` renvoie des tokens bruts en JSON mais ne pose aucun cookie `HttpOnly`; l’étape 2 de l’onboarding a donc besoin d’une correction backend, pas juste d’un “appel API réussi”.
- **`TRUSTED_PROXIES` obligatoire derrière nginx** : sans cette variable, le rate limiter utilise l’IP TCP du proxy/container au lieu du vrai client.
- **HTTPS réellement obligatoire en prod** : les cookies auth sont `secure=True` hors dev/test; si le bloc HTTPS commenté dans `config/nginx/nginx.conf` n’est pas activé, le login navigateur devient incohérent.
- **Prometheus non branché malgré les fichiers présents** : le router `/api/v1/metrics` existe, Prometheus est configuré, mais nginx le coupe avant proxy.
- **Ordre de démarrage critique** : l’API refuse de booter en `production/staging` si Alembic n’est pas à `head`; le déploiement doit lancer les migrations avant de redémarrer les services applicatifs.

## ✨ Ameliorations proposees

Non bloquant mais gain qualite / DX :

- **URL frontend dédiée** : ajouter `FRONTEND_PUBLIC_URL` pour tous les emails et redirects métier évite de détourner `CORS_ORIGINS` de sa responsabilité.
- **Upload streaming** : centraliser un helper d’upload par chunks avec arrêt anticipé, hash, et vérification de signature/magic bytes réduit le risque DoS et simplifie tous les imports de fichiers.
- **Guard rails proxy** : logguer un warning explicite au boot si `APP_ENV=production|staging` et `TRUSTED_PROXIES` est vide.
- **Sécurité dépendances** : supprimer les exceptions `pip-audit`, geler les versions Python, et faire échouer la CI sur toute CVE prod non triée.

## Conclusion

Le socle n’est pas à reprendre de zéro, mais il reste des écarts importants entre l’intention de sécurité et le comportement réel en prod. Les priorités recommandées sont: corriger le flux d’onboarding pour revenir à une auth exclusivement par cookies `HttpOnly`, durcir l’upload pour ne plus charger les gros fichiers en RAM, puis remettre d’équerre la chaîne d’exploitation (CVE Starlette non masquée, metrics réellement scrapable, `TRUSTED_PROXIES` documenté et imposé). Score global subjectif: **6/10**.
