# TODO V10 — OptiFlow AI : Production-Grade & Cosium Reel

> **Contexte** : 9 iterations, 296 tests, code propre, securise, documente.
> Mais l'audit de fond revele 6 trous structurels qui empechent une mise en production reelle :
>
> 1. **Pas de Git** — zero historique, zero rollback, zero collaboration possible
> 2. **Pas de Celery worker** — les taches periodiques (sync Cosium, relances auto) ne tournent pas
> 3. **Pas de "mot de passe oublie"** — un opticien bloque ne peut pas se reconnecter
> 4. **Warning `version` sur chaque commande Docker** — bruit permanent
> 5. **Pas de script de restauration backup** — on sauvegarde mais on ne peut pas restaurer
> 6. **Pas de test Cosium reel** — tout est theorique
>
> Cette V10 transforme le projet d'un prototype avance en un produit deployable pour de vrai.

---

## ETAPE 0 : Health check [ ]

- [ ] Docker UP, pytest 296+, vitest 70, ruff 0, tsc 0

---

## PHASE 1 : FONDATIONS MANQUANTES (Etapes 1-3)

### ETAPE 1 : Initialiser Git et faire le premier commit [ ]

> **C'est le plus gros risque du projet.** Pas de Git = pas d'historique, pas de rollback,
> pas de branches, pas de collaboration, pas de CI qui tourne.
> Si un fichier est corrompu ou supprime par erreur, il est perdu.

- [ ] `git init`
- [ ] Verifier que `.gitignore` est complet (`.env`, `__pycache__`, `.next/`, `node_modules/`, `*.pyc`, `postgres_data/`, `minio_data/`, `.pyc`)
- [ ] `git add -A`
- [ ] Revue rapide : `git status` — verifier qu'aucun secret ou artifact n'est staged
  - PAS de `.env` (seulement `.env.example` et `.env.production.example`)
  - PAS de `frontend/.next/`
  - PAS de `__pycache__/`
  - PAS de `node_modules/`
- [ ] Premier commit :
  ```
  git commit -m "feat: OptiFlow AI v1.2.0 — production-ready

  30 modules metier, 296 tests backend (90% couverture),
  70 tests frontend, auth httpOnly, Fernet encryption,
  connecteur Cosium avec retry/timeout/auto-refresh.
  
  Pret pour la premiere connexion Cosium reelle."
  ```
- [ ] Creer une branche `develop` : `git checkout -b develop`
- [ ] Optionnel : creer un repo GitHub/GitLab et pousser

---

### ETAPE 2 : Fixer le warning Docker Compose `version` [ ]

> Chaque commande `docker compose` affiche un warning car `version: "3.9"` est obsolete.

- [ ] Modifier `docker-compose.yml` : supprimer la ligne `version: "3.9"` (premiere ligne)
- [ ] Modifier `docker-compose.prod.yml` : supprimer la ligne `version: "3.9"` si presente
- [ ] Verifier : `docker compose up -d 2>&1 | grep -i warning` retourne rien

---

### ETAPE 3 : Ajouter le Celery worker pour les taches periodiques [ ]

> Les taches Celery existent dans le code (`tasks/reminder_tasks.py`) mais aucun worker ne tourne.
> La sync periodique Cosium et les relances automatiques ne fonctionnent pas.

- [ ] Ajouter un service `worker` dans `docker-compose.yml` :
  ```yaml
  worker:
    build: { context: ./backend }
    command: celery -A app.tasks worker --loglevel=info --beat
    env_file: [.env]
    depends_on: [postgres, redis, api]
    volumes: ["./backend:/app"]
  ```
- [ ] Verifier que `app/tasks/__init__.py` definit l'app Celery correctement
- [ ] Si `app/tasks/__init__.py` n'existe pas ou est vide, creer la config Celery :
  ```python
  from celery import Celery
  from app.core.config import settings
  
  celery_app = Celery("optiflow", broker=settings.redis_url or "redis://redis:6379/0")
  celery_app.autodiscover_tasks(["app.tasks"])
  ```
- [ ] Ajouter `REDIS_URL` dans `config.py` si manquant : `redis_url: str = "redis://redis:6379/0"`
- [ ] Verifier : `docker compose up -d` → le worker demarre → `docker compose logs worker --tail=10` montre "celery@... ready"
- [ ] Ajouter le worker dans `docker-compose.prod.yml` aussi

---

## PHASE 2 : FEATURES CRITIQUES MANQUANTES (Etapes 4-5)

### ETAPE 4 : Implementer "Mot de passe oublie" [ ]

> Un opticien qui oublie son mot de passe ne peut pas se reconnecter.
> C'est un basique absolu pour un SaaS.

#### Backend
- [ ] Creer `domain/schemas/auth.py` : ajouter `ForgotPasswordRequest(email)` et `ResetPasswordRequest(token, new_password)`
- [ ] Creer dans `services/auth_service.py` :
  - `request_password_reset(db, email)` : genere un token aleatoire, le stocke en BDD (hash), envoie un email avec le lien
  - `reset_password(db, token, new_password)` : verifie le token (hash), change le mot de passe, revoque les refresh tokens
- [ ] Creer la table `password_reset_tokens` (migration Alembic) : id, user_id, token_hash, expires_at, used
- [ ] Creer les endpoints :
  - `POST /api/v1/auth/forgot-password` — body: `{email}` → envoie un email, retourne 204 (toujours, meme si l'email n'existe pas — securite)
  - `POST /api/v1/auth/reset-password` — body: `{token, new_password}` → change le MDP, retourne 204
- [ ] Integrer `email_sender` pour envoyer l'email de reset avec le lien

#### Frontend
- [ ] Creer `app/forgot-password/page.tsx` : formulaire avec champ email + bouton "Envoyer"
- [ ] Creer `app/reset-password/page.tsx` : formulaire nouveau MDP (lit le token depuis l'URL `?token=xxx`)
- [ ] Ajouter un lien "Mot de passe oublie ?" sur la page de login
- [ ] Ajouter ces 2 pages dans les routes publiques du middleware

#### Tests
- [ ] Test : demander un reset → email envoye (verifier dans Mailhog)
- [ ] Test : utiliser le token → MDP change
- [ ] Test : token expire → erreur
- [ ] Test : token deja utilise → erreur

---

### ETAPE 5 : Script de restauration backup [ ]

> `scripts/backup_db.sh` existe mais il n'y a aucun moyen de restaurer.

- [ ] Creer `scripts/restore_db.sh` :
  ```bash
  #!/bin/bash
  # Usage: ./scripts/restore_db.sh backups/optiflow_2026-04-04_120000.sql.gz
  set -e
  BACKUP_FILE=$1
  if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
  fi
  echo "⚠️  Cette operation va REMPLACER toute la base de donnees !"
  echo "Fichier: $BACKUP_FILE"
  read -p "Continuer ? (oui/non) " confirm
  if [ "$confirm" != "oui" ]; then
    echo "Annule."
    exit 0
  fi
  echo "Restauration en cours..."
  gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U optiflow -d optiflow
  echo "✅ Restauration terminee."
  ```
- [ ] `chmod +x scripts/restore_db.sh`
- [ ] Tester : faire un backup → supprimer des donnees → restaurer → verifier que les donnees sont revenues

---

## PHASE 3 : CONNEXION COSIUM REELLE (Etapes 6-7)

### ETAPE 6 : Preparer et tester la connexion Cosium [ ]

> Tout le code est pret. Il faut maintenant brancher les vrais credentials et gerer ce qui casse.

- [ ] Configurer `.env` avec les vrais credentials :
  ```
  COSIUM_BASE_URL=https://c1.cosium.biz
  COSIUM_TENANT=<code-site>
  COSIUM_LOGIN=<login>
  COSIUM_PASSWORD=<password>
  ENCRYPTION_KEY=<generer avec Fernet.generate_key()>
  ```
- [ ] `docker compose restart api`
- [ ] **Test 1 — Authentification** :
  ```
  curl -s -b /tmp/c.txt http://localhost:8000/api/v1/sync/status
  ```
  → Verifier que `"configured": true`
- [ ] **Test 2 — Sync clients** :
  - Depuis l'interface admin ou : `curl -s -b /tmp/c.txt -X POST http://localhost:8000/api/v1/sync/customers`
  - Verifier les logs : `docker compose logs api --tail=30`
  - Compter les clients crees vs skipped vs warnings
- [ ] **Test 3 — Sync factures** :
  - `curl -s -b /tmp/c.txt -X POST http://localhost:8000/api/v1/sync/invoices`
- [ ] **Test 4 — Verification dans l'app** :
  - Les clients Cosium apparaissent dans `/clients`
  - La vue 360 d'un client montre ses donnees
  - Le dashboard montre des KPIs reels

---

### ETAPE 7 : Documenter les ecarts et adapter [ ]

> La premiere sync va reveler des ecarts entre la spec Cosium et la realite.

- [ ] Creer `docs/COSIUM_INTEGRATION_NOTES.md` :
  - Date du premier test
  - Version de l'API Cosium utilisee
  - Nombre de clients synces / skipped / erreurs
  - Champs manquants ou inattendus
  - Temps de sync (pour X clients, Y factures)
  - Problemes rencontres et solutions appliquees
- [ ] Si des champs manquent dans le mapping :
  - Modifier `integrations/cosium/adapter.py` pour gerer les nouveaux champs
  - Ajouter des fallback pour les champs optionnels
- [ ] Si la pagination Cosium ne fonctionne pas comme prevu :
  - Modifier `get_paginated()` pour s'adapter au format reel
- [ ] Committer toutes les corrections : `git add -A && git commit -m "fix: adapt Cosium mapping after real connection test"`

---

## PHASE 4 : SOLIDIFICATION POST-COSIUM (Etapes 8-9)

### ETAPE 8 : Tests E2E avec donnees reelles [ ]

> Apres la sync Cosium, le jeu de donnees est reel. Tester le workflow complet dessus.

- [ ] Parcourir manuellement :
  1. Login → Dashboard → KPIs refletent les vraies donnees
  2. Rechercher un vrai client Cosium par nom → le trouver
  3. Ouvrir la vue 360 → donnees coherentes
  4. Creer un devis pour ce client → calculs corrects
  5. Generer un PDF → informations du vrai client
  6. Relancer la sync → pas de doublons
- [ ] Corriger tout ce qui ne fonctionne pas
- [ ] Committer : `git commit -m "fix: post-Cosium E2E fixes"`

---

### ETAPE 9 : Tag v1.2.0 et preparation deploiement [ ]

> Le projet est verifie avec des donnees reelles. Pret pour le deploiement.

- [ ] Mettre a jour `CHANGELOG.md` avec les notes de connexion Cosium
- [ ] Verification finale :
  - `pytest -q` → 300+ pass
  - `vitest run` → 70+ pass
  - `ruff check` + `tsc --noEmit` + `prettier --check` → 0 erreur
  - Login OK, sync Cosium OK, PDF OK, recherche OK
- [ ] Tag Git : `git tag v1.2.0 -m "OptiFlow AI v1.2.0 — Cosium connected"`
- [ ] Generer la checklist de deploiement VPS :
  - [ ] Serveur VPS commande (Ubuntu 22.04+, 4 vCPU, 8 GB RAM, 50 GB SSD)
  - [ ] Domaine configure (DNS A record → IP du VPS)
  - [ ] `.env.production` configure avec vrais secrets
  - [ ] `scp` du projet ou `git clone` sur le VPS
  - [ ] `./scripts/deploy.sh` → app demarre
  - [ ] Certbot : `certbot certonly --webroot -w /var/www/certbot -d your-domain.com`
  - [ ] Activer HTTPS dans nginx (decommenter le bloc SSL)
  - [ ] Cron pour backup : `0 3 * * * /opt/optiflow/scripts/backup_db.sh`
  - [ ] Cron pour certbot : `0 0 1 * * certbot renew`

---

## Checkpoints

### Apres PHASE 1 (Etapes 1-3) :
- [ ] Git initialise avec premier commit
- [ ] 0 warning Docker Compose
- [ ] Celery worker tourne (sync periodique et relances auto)

### Apres PHASE 2 (Etapes 4-5) :
- [ ] "Mot de passe oublie" fonctionnel (email + reset)
- [ ] Restauration backup testee

### Apres PHASE 3 (Etapes 6-7) :
- [ ] **Premiere sync Cosium reussie avec donnees reelles**
- [ ] Ecarts documentes et corriges

### Apres PHASE 4 (Etapes 8-9) :
- [ ] E2E valide sur donnees reelles
- [ ] Tag v1.2.0, checklist deploiement prete
- [ ] **Le projet est deployable en production**
