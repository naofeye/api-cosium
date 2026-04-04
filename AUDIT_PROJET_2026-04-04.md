# Audit complet du projet OptiFlow AI

Date: 2026-04-04

## Périmètre et méthode

Audit refait intégralement sur l’état actuel des fichiers du projet.

Sources examinées:

- backend FastAPI, services, repositories, modèles, middlewares
- frontend Next.js, client API, auth, pages critiques
- CI, README, compose, seeds
- tests présents dans le repo

Vérifications réellement exécutées:

- `python -m compileall app` dans `backend`: OK
- `python -m pytest -q` dans `backend`: impossible ici, module `pytest` absent
- `npm run typecheck` dans `frontend`: impossible ici, `tsc` absent
- `npm test` dans `frontend`: impossible ici, `vitest` absent

Remarque:

- le dossier fourni n’est toujours pas un dépôt Git initialisé, donc cet audit porte sur l’état courant uniquement

## Conclusion rapide

Le projet reste techniquement structuré et ambitieux, avec une vraie architecture applicative, une CI présente et un périmètre métier large. En revanche, plusieurs défauts critiques subsistent et touchent des axes de production centraux: authentification, exposition de secrets, cohérence frontend/backend et sécurité opérationnelle.

Verdict actuel:

- base applicative: solide
- état sécurité production: insuffisant
- état cohérence produit: partiellement cassé
- recommandation: ne pas considérer le projet prêt pour une mise en production exposée sans correction des points P0

## Forces observées

- Architecture backend toujours claire par couches.
- Couverture fonctionnelle large et tests nombreux dans le repo.
- CI cohérente avec lint, tests backend/frontend et build Docker: `.github/workflows/ci.yml`.
- Garde-fou au startup contre `JWT_SECRET` par défaut en prod: `backend/app/main.py`.
- Multi-tenant présent dans les routes et la plupart des accès métiers.

## Constats prioritaires

### P0. Authentification incohérente et tokens exposés côté navigateur

Le backend pose bien des cookies `httponly`:

- `backend/app/api/routers/auth.py:14-28`

Mais ces mêmes tokens sont aussi renvoyés dans le corps JSON des réponses d’auth:

- `backend/app/api/routers/auth.py:31-54`

Puis le frontend les récupère et les réécrit lui-même en cookies lisibles par JavaScript via `js-cookie`:

- `frontend/src/lib/auth.ts:17-31`
- `frontend/src/lib/auth.ts:74-88`
- `frontend/src/lib/auth.ts:96-135`

Impact:

- les `httpOnly cookies` du backend perdent une grande partie de leur intérêt
- access token et refresh token deviennent accessibles au runtime frontend
- le système mélange deux stratégies incompatibles: cookie serveur et token géré côté JS
- surface XSS fortement aggravée

Conclusion:

- c’est toujours un défaut critique
- le bon correctif est d’unifier la stratégie
- recommandation: cookies `httpOnly` uniquement, `credentials: "include"`, suppression du stockage des tokens côté JS et suppression du retour des tokens bruts dans les payloads JSON

### P0. Secrets Cosium stockés en clair en base

Les credentials Cosium sont enregistrés sans chiffrement:

- écriture: `backend/app/services/onboarding_service.py:109-133`
- champ stocké: `backend/app/models/tenant.py:29-31`
- relecture brute: `backend/app/services/erp_sync_service.py:39-54`

Le nom `cosium_password_enc` est trompeur: aucun chiffrement n’est appliqué.

Impact:

- compromission directe des accès ERP si la base fuit
- risque élevé en audit sécurité ou conformité
- confusion technique car le nom du champ laisse croire à une protection absente

Recommandation:

- chiffrer au repos avec une clé applicative dédiée ou un secret manager
- migrer les données existantes
- renommer le champ si le chiffrement n’est pas mis en place immédiatement

### P0. Les refresh tokens sont aussi stockés en clair

Le modèle persiste le refresh token tel quel:

- `backend/app/models/user.py:19-26`

Les lectures/révocations s’appuient ensuite sur cette valeur brute:

- `backend/app/repositories/refresh_token_repo.py:8-31`

Impact:

- toute lecture base donne accès aux sessions persistantes
- risque proche d’un stockage de mots de passe en clair, même si la nature du secret diffère

Recommandation:

- stocker un hash des refresh tokens, pas leur valeur brute
- faire la comparaison sur hash

## Risques importants

### P1. Changement de mot de passe toujours cassé

Le frontend appelle toujours un endpoint inexistant:

- appel UI: `frontend/src/app/settings/page.tsx:30-41`

Le schéma `ChangePasswordRequest` existe côté backend:

- `backend/app/domain/schemas/auth.py:22-32`

Mais aucune route backend `/auth/change-password` n’est implémentée.

Impact:

- fonctionnalité affichée mais non fonctionnelle
- défaut produit sur un parcours sécurité essentiel

Recommandation:

- soit implémenter la route et le service
- soit retirer l’UI tant que le backend n’existe pas

### P1. Import bancaire frontend toujours incohérent avec l’auth réelle

La page rapprochement lit encore `localStorage.getItem("access_token")` pour uploader:

- `frontend/src/app/rapprochement/page.tsx:67-73`

Or l’application ne gère pas cet état comme source de vérité. Le reste du frontend passe par `js-cookie`:

- `frontend/src/lib/auth.ts:17-31`
- `frontend/src/lib/api.ts:1-48`

Impact:

- l’import bancaire peut échouer alors que l’utilisateur est connecté
- comportement incohérent entre les écrans
- risque de faux succès UI car la réponse n’est pas validée proprement avant affichage

Recommandation:

- unifier l’upload sur le même client API que le reste
- supprimer toute dépendance à `localStorage` pour l’auth

### P1. Endpoint `/api/v1/admin/health` public et trop bavard

Le endpoint est explicitement public:

- `backend/app/api/routers/admin_health.py:19-57`

Il expose l’état détaillé de PostgreSQL, Redis et MinIO, avec erreurs et temps de réponse.

Impact:

- fuite d’informations d’infrastructure
- fingerprinting simplifié
- exposition d’erreurs internes inutile sur un endpoint public

Recommandation:

- réserver ce endpoint à l’interne ou à une auth admin
- garder un healthcheck public minimal sur `/health`

### P1. Upload documentaire encore trop permissif

Le service:

- lit le fichier entier en mémoire: `backend/app/services/document_service.py:23-34`
- ne valide ni taille ni type ni extension
- crée ensuite le document en base sans validation métier explicite du `case_id` dans cette couche: `backend/app/repositories/document_repo.py:17-21`

Impact:

- risque mémoire sur fichiers volumineux
- surface d’attaque inutile sur les types de fichiers
- robustesse métier incomplète

Recommandation:

- limiter la taille
- filtrer type MIME et extensions
- vérifier explicitement l’existence et l’appartenance du dossier métier avant upload

## Dette de qualité et cohérence

### P2. Documentation toujours en retard sur l’état réel du projet

Le README annonce encore:

- un login démo `Admin123`: `README.md:21`
- 42 fichiers de tests backend et 228 tests: `README.md:48`, `README.md:73`
- 6 fichiers de tests frontend et 36 tests: `README.md:56`, `README.md:76`

Mais le seed crée toujours `admin123`:

- `backend/app/seed.py:48-52`

Et le repo a clairement évolué au-delà des chiffres indiqués.

Impact:

- friction dès le démarrage
- perte de confiance dans la doc d’exploitation

### P2. Artefacts de build/runtime toujours présents

État observé:

- `550` fichiers `.pyc`
- `17` dossiers `__pycache__`
- `frontend/tsconfig.tsbuildinfo` présent

Impact:

- workspace sale
- bruit important pendant l’audit
- signal de discipline de build insuffisante

## Évaluation par domaine

### Sécurité

État: insuffisant pour prod.

Points forts:

- headers sécurité présents
- rate limiting sur login/refresh
- garde-fou sur `JWT_SECRET` en prod

Points faibles majeurs:

- tokens exposés au frontend
- refresh tokens en clair en base
- secrets ERP en clair en base
- endpoint admin health public

### Robustesse produit

État: mitigé.

Points positifs:

- beaucoup de parcours métiers existent
- pages et services couvrent un périmètre large

Points faibles:

- changement de mot de passe cassé
- import bancaire avec auth incohérente

### Qualité technique

État: bon socle, dette ciblée.

Points positifs:

- séparation des couches claire
- CI utile
- ajout de nouveaux schémas et nouveaux endpoints structurés

Points faibles:

- documentation non synchronisée
- artefacts de build dans l’arborescence
- plusieurs défauts critiques encore non résolus malgré les évolutions récentes

## Priorisation recommandée

### Avant toute mise en production

1. Reconcevoir complètement la stratégie d’auth:
   - ne plus exposer les tokens dans le JSON
   - ne plus les réécrire côté frontend
   - choisir cookie `httpOnly` only
2. Chiffrer les credentials Cosium au repos.
3. Hacher les refresh tokens en base.
4. Corriger ou retirer la fonction de changement de mot de passe.

### Juste après

1. Corriger l’import bancaire frontend.
2. Restreindre `/api/v1/admin/health`.
3. Durcir l’upload documentaire.
4. Aligner README, seed et chiffres réels.
5. Nettoyer les artefacts de build.

## Conclusion finale

Le projet a continué d’évoluer dans le bon sens sur la structure générale et le périmètre fonctionnel. En revanche, les problèmes les plus sensibles de la précédente passe ne sont pas résolus sur les axes critiques. Le socle est crédible, mais l’état sécurité et la cohérence de certains parcours restent insuffisants pour considérer l’ensemble comme prêt pour une exploitation réelle.
