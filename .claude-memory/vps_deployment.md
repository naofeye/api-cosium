---
name: VPS deployment OptiFlow
description: Coordonnees + chemin + secrets pour deployer api-cosium sur le VPS production
type: reference
originSessionId: b52841a4-964d-4c1f-a411-0639e890bcfc
---
## Acces SSH
- IP : `187.124.217.73`
- User : `nabil`
- Cle SSH locale : `~/.ssh/id_ed25519`
- Sudo password : `123soleil` (necessaire pour chown projet)

## Chemin projet
- Repo VPS : `/srv/projects/api-cosium/` (verifie 2026-04-21)
- Branch deployee : `main` (HEAD = ecf7678+)
- Owner : `nabil:nabil` (changed par chown initial)
- `.env` : owner `claude-agent:claude-agent`, mode `0600` — docker compose doit etre lance via sudo pour le lire

## Stack docker-compose
- 7 services : postgres, redis, minio, api, web, beat, worker
- Build : `docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.override.yml up -d`
- L'override expose les ports 8000 et 3000 (sinon prod ferme tout)

## URLs externe
- API : http://187.124.217.73:8000 (health: ok)
- Frontend : http://187.124.217.73:3000 (login : admin@optiflow.com / admin123)

## Reverse-proxy global VPS
- Caddy : `/srv/reverse-proxy/Caddyfile`
- Domaine actuel : `ia.coging.com` -> orchestrator/admin-ui/vps-panel
- TODO : ajouter sous-domaine pour api-cosium (ex: optiflow.coging.com -> api-cosium-web-1:3000 + /api/* -> api-cosium-api-1:8000)

## .env production VPS
- Cree par claude le 2026-04-15
- Secrets generes (POSTGRES_PASSWORD, JWT_SECRET, ENCRYPTION_KEY, MinIO keys)
- Cosium creds : VIDES (placeholders) — endpoints Cosium retournent 502 propre
- Anthropic API key : VIDE — IA desactivee
- Domaine NEXT_PUBLIC_API_BASE_URL : `http://187.124.217.73/api/v1` (a corriger en https://domain quand DNS configure)

## Commande deploy standard
```bash
ssh nabil@187.124.217.73
cd /srv/projects/api-cosium
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.override.yml build api web
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.override.yml run --rm api alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.override.yml up -d
```

## Bug deploy.sh connu
Le script `scripts/deploy.sh` lance `up -d` AVANT `alembic upgrade head` -> l'API fail-fast en prod si tables manquent.
Workaround : run alembic upgrade BEFORE up -d.

## Pieges rencontres deploy 2026-04-19 (HEAD passe de 8c494dd a 6e000e3)
1. **Nginx port 80 conflit** : le service `nginx` du docker-compose.prod.yml conflicte avec le Caddy VPS global qui ecoute deja sur :80. Solution temporaire : le service nginx ne demarre pas (les 7 autres services sont OK). Caddy devrait etre configure pour proxy vers `api-cosium-web-1:3000` et `api-cosium-api-1:8000` (direct conteneur) sans passer par un nginx intermediaire. Sous-domaine a ajouter dans `/srv/reverse-proxy/Caddyfile`.
2. **Volume celerybeat_schedule nouveau** : cree root:root par defaut -> beat (user appuser=UID 1000) crash avec `Permission denied: /app/celery-schedule/schedule.db`. Fix : `sudo chown -R 1000:1000 /var/lib/docker/volumes/api-cosium_celerybeat_schedule/_data` puis restart beat. A faire une seule fois apres `up -d`.
3. **`docker compose exec` vs `run --rm` pour Alembic** : `exec` utilise l'ancienne image encore en memoire (container running), `run --rm` instancie la nouvelle image. Toujours utiliser `run --rm api alembic upgrade head` apres un build.
4. **`git pull` impossible apres force-push** : toujours `git fetch origin --prune && git reset --hard origin/main`.
5. **Migrations appliquees 2026-04-19** : 9 migrations de `p1q2r3s4t5u6` -> `y0z1a2b3c4d5` (FK ondelete, MFA TOTP+backup, require_admin_mfa, customer cosium_id, etc.). Snapshot avant = soft_delete/composite indexes.
