# OptiFlow AI

Plateforme metier pour opticiens avec backend FastAPI, frontend Next.js et stack Docker prete pour un depot GitHub prive et un deploiement futur sur VPS Linux.

## Structure

- `apps/api` : backend FastAPI, migrations Alembic, tests Python
- `apps/web` : frontend Next.js, tests Vitest
- `config/nginx` : configuration reverse proxy
- `scripts` : scripts Bash de setup, demarrage, checks, sauvegarde
- `docs` : documentation d'exploitation et de deploiement

## Installation locale

```bash
cp .env.example .env
npm install
bash scripts/setup.sh
```

## Lancement local

```bash
npm run dev
```

Ou en mode detache:

```bash
# Prerequis : reseau Docker externe (partage avec d'autres services du VPS)
docker network create interface-ia-net 2>/dev/null || true
docker compose up -d --build
```

> Le service `web` rejoint `interface-ia-net` (defini en `external: true` dans
> `docker-compose.yml`) pour pouvoir parler a l'orchestrateur interface-ia
> deploye sur le meme hote. Sans ce reseau, le premier `docker compose up`
> echoue avec `network interface-ia-net declared as external, but could not
> be found`. La commande `docker network create` est idempotente — relancer
> ne casse rien.

Services par defaut:

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- MinIO: `http://localhost:9001`
- Mailhog: `http://localhost:8025`

## Docker

La stack standard est deployee avec:

```bash
docker compose up -d
```

Les images applicatives sont construites depuis:

- `apps/api/Dockerfile`
- `apps/web/Dockerfile`

## Verification

```bash
npm run check
```

Le script valide la configuration Docker Compose et lance les verifications locales disponibles.

## Variables d'environnement

Le fichier versionnable est `.env.example`. Le fichier `.env` ne doit jamais etre commit.

Variables importantes:

- `APP_ENV`
- `DATABASE_URL`
- `JWT_SECRET`
- `ENCRYPTION_KEY`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

## Deploiement VPS

Voir `docs/VPS_DEPLOYMENT.md`.
