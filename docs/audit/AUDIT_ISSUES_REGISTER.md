# Registre Detaille des Problemes

## Critique

### C1. Bootstrap applicatif non maitrise en production

- Zone: `backend/app/main.py`
- Constat: au startup, l'application detecte des tables manquantes et appelle `Base.metadata.create_all(bind=engine)`, puis lance `seed_data(db)`.
- Impact: contournement d'Alembic, drift de schema possible, etat de base difficile a predire, risque de masquer des deploiements incomplets, effets de bord au demarrage.
- Risque: tres eleve en production.
- Cause probable: volontarisme pour rendre l'environnement "self-healing".
- Recommandation: supprimer la creation automatique du schema en runtime, reserver tout changement de schema aux migrations, rendre le seeding explicite et borne aux environnements de dev/demo.
- Priorite: immediate.

### C2. Pipeline de deploiement production partiellement casse

- Zone: `scripts/deploy.sh`, `docker-compose.prod.yml`
- Constat: le script appelle `./scripts/backup_db.sh` qui n'existe pas; il attend `http://localhost:8000/health` alors que le compose prod n'expose pas `8000:8000`; la verification finale appelle aussi `localhost:8000`.
- Impact: deploiement automatise non fiable, risque d'echec faux-negatif ou de procedure manuelle improvisee.
- Risque: tres eleve.
- Cause probable: script non rejoue apres evolution du compose prod.
- Recommandation: aligner script, compose et healthchecks sur l'architecture reelle, et tester un runbook de deploiement complet.
- Priorite: immediate.

### C3. HTTPS production non termine alors que la stack expose 443

- Zone: `nginx/nginx.conf`, `docker-compose.prod.yml`
- Constat: le serveur HTTPS dans Nginx est entierement commente, alors que le compose prod ouvre `80` et `443` et monte des certificats.
- Impact: posture securite inachevee, ambiguite d'exploitation, risque de faux sentiment de securisation.
- Risque: tres eleve pour une vraie mise en production internet.
- Recommandation: finaliser la conf TLS, tester la terminaison TLS, durcir le proxy et documenter le mode reel supporte.
- Priorite: immediate.

## Eleve

### E1. Diagnostics Cosium d'admin potentiellement faux car non scopes par tenant

- Zone: `backend/app/api/routers/admin_health.py`
- Constat: `_check_cosium_status()` et `test_cosium_connection()` instancient `CosiumClient()` puis appellent `authenticate()` sans injecter les credentials/chiffres du tenant courant, alors que les cookies Cosium sont stockes par tenant.
- Impact: les pages d'administration peuvent annoncer un etat valide ou invalide qui ne correspond pas au tenant inspecte.
- Risque: eleve.
- Recommandation: factoriser un helper de connexion Cosium par tenant reutilisant la logique de `erp_sync_service._authenticate_connector`.
- Priorite: haute.

### E2. Chiffrement de secours derive du `JWT_SECRET`

- Zone: `backend/app/core/encryption.py`, `.env.example`
- Constat: si `ENCRYPTION_KEY` est vide, la cle Fernet est derivee du `JWT_SECRET`.
- Impact: couplage de secrets heterogenes, rotation JWT risquee pour les secrets chiffres, baisse du niveau de defense en profondeur.
- Risque: eleve.
- Recommandation: imposer une cle de chiffrement dediee hors dev local; refuser le mode fallback en staging/production.
- Priorite: haute.

### E3. Diagnostics README / promesses documentaires obsoletes

- Zone: `README.md`
- Constat: le README affirme des chiffres precis (740 tests backend, 133 tests frontend, 49 pages, 38 routers, 53 services, 25 repositories, 35 schemas) qui ne correspondent plus a l'inventaire source actuel observe.
- Impact: perte de confiance documentaire, pilotage fausse, difficultes de reprise.
- Risque: eleve cote gouvernance technique.
- Recommandation: recalculer automatiquement ou supprimer les compteurs figes.
- Priorite: haute.

### E4. Hygiene repository insuffisante

- Zone: Git tree
- Constat: `frontend/tsconfig.tsbuildinfo` et `backend/celerybeat-schedule` sont suivis dans Git; des `__pycache__` existent localement; l'arbre est pollue par des artefacts d'execution.
- Impact: bruit de diff, conflits inutiles, risque d'etats non deterministes.
- Risque: eleve pour la qualite operationnelle.
- Recommandation: nettoyer les artefacts suivis, renforcer `.gitignore`, clarifier les fichiers runtime acceptes.
- Priorite: haute.

### E5. Production compose et Nginx encore ambigus sur l'exposition des docs et du backend

- Zone: `docker-compose.prod.yml`, `nginx/nginx.conf`
- Constat: l'acces `/docs` et `/openapi.json` reste explicitement laisse possible en prod, avec un commentaire "restrict in production by uncommenting".
- Impact: exposition inutile des metadonnees API et d'une surface d'information supplementaire.
- Risque: eleve.
- Recommandation: desactiver par defaut en production ou proteger strictement l'acces.
- Priorite: haute.

### E6. Contrats front/back incoherents sur l'ecran d'administration

- Zone: `frontend/src/app/admin/page.tsx`, `frontend/src/app/admin/components/HealthStatus.tsx`, `frontend/src/app/admin/components/CosiumConnection.tsx`, `backend/app/api/routers/admin_health.py`, `backend/app/services/erp_sync_service.py`, `backend/app/domain/schemas/admin.py`
- Constat: le frontend attend `health.services` et un statut `"healthy"`, alors que le backend renvoie surtout `components` et des statuts `"ok"` / `"degraded"`; le frontend attend `metrics.totals.users`, absent du backend; le frontend attend aussi `tenant` et `base_url` dans le statut sync, absents de la reponse backend.
- Impact: dashboard admin potentiellement partiellement casse ou affichant des informations vides/fausses.
- Risque: eleve.
- Recommandation: figer un contrat unique typed end-to-end pour l'admin, puis revalider l'ecran complet.
- Priorite: haute.

## Moyen

### M1. Le middleware frontend accepte un simple flag cookie non httpOnly comme preuve d'auth pour l'UX

- Zone: `frontend/src/middleware.ts`, `backend/app/api/routers/auth.py`
- Constat: si `optiflow_token` est absent, le middleware se rabat sur `optiflow_authenticated=true`, cookie non httpOnly et non marque `secure`.
- Impact: faux positifs d'auth cote UI, garde client contournable par manipulation locale, UX incoherente possible.
- Risque: moyen.
- Recommandation: utiliser uniquement un signal serveur fiable ou un endpoint session/me cote middleware serveur.
- Priorite: moyenne.

### M2. Accumulation de refresh tokens et gestion de session partielle

- Zone: `backend/app/services/auth_service.py`
- Constat: login et switch tenant creent de nouveaux refresh tokens sans revoquer systematiquement les anciens.
- Impact: multiplication des sessions actives, surface de revocation floue, hygiene session moyenne.
- Risque: moyen.
- Recommandation: definir une politique explicite par appareil/session, ou revoquer a minima lors du switch tenant.
- Priorite: moyenne.

### M3. Strategie de verrouillage faible quand Redis tombe

- Zone: `backend/app/core/redis_cache.py`
- Constat: `acquire_lock()` retourne `True` si Redis est indisponible.
- Impact: les operations concurrentes critiques (sync, imports) peuvent s'executer en parallele sans verrou distribue.
- Risque: moyen.
- Recommandation: distinguer cache degrade et verrouillage degrade; refuser certaines operations si le lock distribue n'est pas disponible.
- Priorite: moyenne.

### M4. Sante publique potentiellement couteuse et trompeuse

- Zone: `backend/app/api/routers/admin_health.py`
- Constat: le healthcheck public teste PostgreSQL, Redis, MinIO et Cosium; il utilise en plus une URL Redis hardcodee.
- Impact: endpoint plus lourd que necessaire, couplage infra, lecture de sante melangeant readiness applicative et dependances externes.
- Risque: moyen.
- Recommandation: separer liveness, readiness et diagnostics admin profonds; utiliser `settings.redis_url`.
- Priorite: moyenne.

### M5. Services et pages trop volumineux

- Zone: `backend/app/services/client_service.py`, `backend/app/services/erp_sync_service.py`, `backend/app/services/export_pdf.py`, `frontend/src/app/clients/page.tsx`, `frontend/src/app/dashboard/page.tsx`
- Constat: plusieurs fichiers centraux concentrent beaucoup de responsabilites.
- Impact: maintenance couteuse, revue difficile, regression plus probable.
- Risque: moyen.
- Recommandation: decomposer par sous-domaines/facades, surtout cote services et grosses pages UI.
- Priorite: moyenne.

### M6. Metrique de fusion client possiblement trompeuse

- Zone: `backend/app/services/client_service.py`
- Constat: `pec_transferred` est compte apres transfert des `Case`, ce qui peut inclure des PEC deja rattachees au client conserve.
- Impact: reporting de fusion inexact.
- Risque: moyen faible.
- Recommandation: compter avant mutation ou en filtrant strictement les objets venant du client fusionne.
- Priorite: moyenne.

### M7. Inventaire de tests revendique eleve mais execution locale non immediatement reproductible

- Zone: environnement projet / docs
- Constat: le backend depend de `pytest` non present dans cet environnement local et les tests frontend Vitest n'ont pas pu se charger ici a cause d'un `spawn EPERM`.
- Impact: la qualite testee n'a pas pu etre revalidee de bout en bout dans cette session.
- Risque: moyen.
- Recommandation: documenter une procedure locale fiable Windows et/ou standardiser via Docker/Make/CI.
- Priorite: moyenne.

### M8. Lien frontend vers une page d'administration inexistante

- Zone: `frontend/src/app/dashboard/page.tsx`
- Constat: le dashboard pointe vers `/admin/data-quality`, mais aucune page `frontend/src/app/admin/data-quality/page.tsx` n'existe.
- Impact: lien casse dans une zone importante de navigation.
- Risque: moyen.
- Recommandation: soit creer la page dediee, soit rediriger vers `/admin` avec ancrage/section.
- Priorite: moyenne.

## Faible

### F1. Artefacts UX et gardes route cote client perfectibles

- Zone: plusieurs pages frontend
- Constat: usage direct de `window.open`, `confirm`, et gros etats locaux dans des pages complexes.
- Impact: UX/browser behavior moins maitrisable, testabilite moyenne.
- Priorite: faible.

### F2. Incoherences mineures entre commentaires et realite

- Zone: `README.md`, commentaires divers
- Constat: plusieurs commentaires numeriques ou descriptifs semblent dater d'un etat anterieur.
- Impact: comprehension ralentie.
- Priorite: faible.

### F3. HSTS defini au niveau app meme en HTTP

- Zone: `backend/app/core/security_headers.py`
- Constat: le header HSTS est ajoute systematiquement meme si l'application n'est pas servie en TLS direct.
- Impact: faible techniquement, mais signal de securite pas totalement coherent avec la conf Nginx actuelle.
- Priorite: faible.

## Amelioration

### A1. Mieux tracer les limites de confiance de l'audit

- Zone: documentation projet
- Constat: beaucoup de choses sont documentees comme factuelles sans distinguer clairement "verifie en execution" et "deduit du code".
- Recommandation: separer dans la doc ce qui a ete teste de ce qui est seulement implemente.

### A2. Automatiser l'inventaire du projet

- Zone: docs / CI
- Constat: les compteurs et promesses vieillissent vite.
- Recommandation: generer les stats de structure depuis CI si elles doivent rester affichees.
