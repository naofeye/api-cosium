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
# Prerequis : reseau Docker externe partage avec les autres services du VPS
# (panel, reverse-proxy). En local pur, creer le reseau avant le premier `up`.
docker network create vps-net 2>/dev/null || true
docker compose up -d --build
```

> Les services `api`/`web`/`worker` rejoignent `vps-net` (defini en
> `external: true` dans `docker-compose.yml`) pour parler au reverse-proxy
> Caddy et au panel deployes sur le meme hote. Sans ce reseau, le premier
> `docker compose up` echoue avec `network vps-net declared as external, but
> could not be found`. La commande `docker network create` est idempotente.

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

## Architecture (vue d'ensemble)

```
                   Internet (HTTPS)
                         |
                  +------v------+
                  |    Caddy    |  reverse-proxy + TLS
                  | (vps-panel) |
                  +------+------+
                         |
        +----------------+----------------+
        |                                 |
   +----v----+                       +----v----+
   |   web   |  Next.js 16 + React   |   api   |  FastAPI + Python 3.12
   | (3000)  |  RSC + Service Worker | (8000)  |  60+ routers, ~300 routes
   +----+----+                       +----+----+
        |                                 |
        |        +------------------------+
        |        |
        |   +----v----+    +-----------+    +--------+
        |   | worker  |    |   beat    |    | celery |
        |   | (Celery)|    |(scheduler)|    | result |
        |   +----+----+    +-----+-----+    +--------+
        |        |               |
        +--------+---------------+
                 |
        +--------+--------+--------+--------+
        |        |        |        |        |
   +----v---+ +-v---+ +-v----+ +-v-----+ +-v-----+
   |postgres| |redis| |minio | |mailhog| |Cosium |
   | (5432) | |6379 | |(9000)| |(8025) | | API   |
   +--------+ +-----+ +------+ +-------+ +---+---+
                                             |
                                  c1.cosium.biz (read-only)
```

**8 containers** : web, api, worker, beat, postgres, redis, minio, mailhog.
**3 monitoring** (prod) : prometheus, grafana, postgres-exporter, redis-exporter.

**Flux donnees** :
- Sync Cosium **read-only unidirectionnelle** (Cosium -> OptiFlow), jamais l'inverse.
  Pattern HAL JSON, auth Basic/Cookie/OIDC, retry borne (4 retries).
- Webhooks HTTP **sortants** : push vers systemes tiers (CRM, comptabilite)
  signes HMAC-SHA256, retry [30s, 2m, 15m, 1h, 6h]. Voir `docs/WEBHOOKS.md`.
- API publique **read-only v1** : token Bearer + scopes par tenant. 4
  endpoints (clients, devis, factures, pec). Voir `/admin/api-publique`.
- Stripe : checkout, portal, webhooks entrants (subscriptions, payments).

## Stack technique

| Couche | Tech | Notes |
|---|---|---|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2 | 60 routers, 290+ routes |
| **DB** | PostgreSQL 16 | 53+ migrations Alembic, indexes composites |
| **Cache + queue** | Redis 7 | Celery broker + result backend, rate limiter |
| **Worker** | Celery 5 | Beat scheduler persistent, retry + DLQ |
| **Storage** | MinIO (S3 API) | Documents Cosium, exports, GED |
| **Frontend** | Next.js 16 + React 19 + TypeScript strict | RSC, ESLint strict (0 `any`) |
| **PWA** | Service Worker | Offline-first, install prompt iOS/Android |
| **Auth** | JWT (PyJWT) + bcrypt + MFA TOTP | Cookies httpOnly SameSite=Strict, CSRF double-submit |
| **Tests** | pytest + httpx + Playwright | 2300+ backend, 200+ frontend, 10 E2E |
| **CI** | GitHub Actions | 9 jobs (lint, test, security, E2E), Trivy + SBOM weekly |
| **Observabilite** | Prometheus + Grafana | 2 dashboards (ops, business), 7 alertes |
| **Reverse proxy** | Caddy (auto TLS Let's Encrypt) | Configure dans /srv/reverse-proxy |

## Features livrees recemment

- **2026-05-03** : API publique REST v1 (Coming Soon T3 2026 -> reel),
  Devis signature electronique eIDAS Simple, Token revocation per-user
  (logout-everywhere), exporters Postgres+Redis Prometheus, alertmanager
  rules, validate-prod.sh + COSIUM_CREDS_ROTATION runbook.
- **2026-05-02** : CSRF double-submit cookie, Webhooks HTTP sortants
  (Coming Soon -> reel), PEC reconciliation factures orphelines,
  fix CI rollback Alembic mergepoint-safe.

Voir `docs/WEBHOOKS.md`, `docs/adr/`, `TODO.md` pour le detail.

