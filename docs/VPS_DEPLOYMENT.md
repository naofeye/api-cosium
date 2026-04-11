# Deploiement VPS

## Prerequis

- Ubuntu 22.04+ avec acces `sudo`
- Docker Engine et Docker Compose plugin installes
- Domaine ou sous-domaine pointant vers le VPS si vous ajoutez un reverse proxy

## Structure attendue

Le depot est organise pour la production autour de:

- `apps/api` pour le backend FastAPI
- `apps/web` pour le frontend Next.js
- `config/nginx` pour la configuration de reverse proxy
- `scripts` pour l'automatisation
- `docs` pour l'exploitation

## Installation

```bash
git clone <repo-prive> optiflow
cd optiflow
cp .env.example .env
```

Renseigner ensuite au minimum dans `.env`:

- `APP_ENV=production`
- `DATABASE_URL`
- `JWT_SECRET`
- `ENCRYPTION_KEY`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

## Lancement

```bash
docker compose build
docker compose up -d
docker compose ps
```

Services utiles apres deploiement:

- Frontend: `http://<vps>:3000`
- API: `http://<vps>:8000/docs` si `APP_ENV` n'est pas `production`
- Mailhog: `http://<vps>:8025` en environnement non public

## Commandes d'exploitation

```bash
bash scripts/start.sh
bash scripts/check.sh
bash scripts/backup_db.sh
bash scripts/restore_db.sh docker-compose.yml runtime/backups/<fichier.dump>
```

## Reverse proxy

Le projet inclut `config/nginx/nginx.conf` comme base Linux-compatible. Si vous activez Nginx sur le VPS:

1. Monter le fichier dans un conteneur ou un service systemd.
2. Pointer le proxy vers `web:3000` et `api:8000`.
3. Ajouter TLS via Let's Encrypt ou votre proxy habituel.

## Mise a jour

```bash
git pull
docker compose build
docker compose up -d
```

## Donnees runtime

Ne versionnez jamais:

- `.env`
- `runtime/`
- volumes Docker PostgreSQL et MinIO
- logs et caches locaux
