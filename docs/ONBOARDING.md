# ONBOARDING — Nouveau développeur OptiFlow AI

Ce guide t'amène en < 30 minutes d'un clone vierge à un environnement de dev fonctionnel.

## 1. Prérequis

- **Git**
- **Docker Desktop** (ou Docker + docker-compose)
- **Python 3.12** (pour exécuter des scripts hors container si besoin)
- **Node.js 20** + npm (pour dev frontend rapide hors container)
- Éditeur : VS Code recommandé (config dans `.devcontainer/`)

## 2. Clone & setup

```bash
git clone <repo-url>
cd api-cosium
cp .env.example .env
# Éditer .env : pour la majorité, les valeurs par défaut suffisent en local.
```

## 3. Lancer la stack

```bash
docker compose up --build
```

Ce qui démarre :
- **PostgreSQL** (port 5432) — base applicative
- **Redis** (6379) — cache + rate-limit + Celery broker
- **MinIO** (9000/9001) — stockage S3 (console http://localhost:9001, `minioadmin:minioadmin`)
- **Mailhog** (1025/8025) — SMTP capture (UI http://localhost:8025)
- **API** (8000) — FastAPI http://localhost:8000
- **Web** (3000) — Next.js http://localhost:3000

Migrations Alembic auto-appliquées au démarrage (ou manuellement : `make migrate`).

## 4. URLs dev

| Service | URL | Identifiants |
|---|---|---|
| Frontend | http://localhost:3000 | `admin@optiflow.com` / `admin123` |
| API Swagger | http://localhost:8000/docs | JWT via `/api/v1/auth/login` |
| API ReDoc | http://localhost:8000/redoc | — |
| MinIO Console | http://localhost:9001 | `minioadmin:minioadmin` |
| Mailhog | http://localhost:8025 | — |
| Health | http://localhost:8000/health | public |

## 5. Commandes utiles

```bash
# Terminals
docker compose logs -f api     # logs API
docker compose logs -f web     # logs Next
docker compose exec api bash   # shell dans le container API

# Tests
make test-api                  # pytest backend
make test-web                  # vitest frontend
make test                      # les deux

# Lint / typecheck
make lint                      # ruff + eslint
make typecheck                 # tsc --noEmit

# Migrations Alembic
make migration msg="ajout_table_xxx"  # crée une migration
make migrate                   # applique

# Tout en un
make check                     # lint + typecheck + test
```

## 6. Structure monorepo

```
api-cosium/
├── apps/
│   ├── api/           # FastAPI backend (Python 3.12)
│   │   ├── app/
│   │   │   ├── api/routers/        # Routes HTTP
│   │   │   ├── core/               # Config, deps, security, logging
│   │   │   ├── domain/schemas/     # Pydantic I/O
│   │   │   ├── integrations/       # Cosium, MinIO, Claude, Stripe
│   │   │   ├── models/             # SQLAlchemy ORM
│   │   │   ├── repositories/       # Accès DB
│   │   │   ├── services/           # Logique métier
│   │   │   └── tasks/              # Celery workers
│   │   ├── alembic/versions/       # Migrations DB
│   │   └── tests/
│   └── web/           # Next.js 15 frontend (TS strict)
│       └── src/
│           ├── app/                # App Router (RSC + client components)
│           ├── components/         # UI réutilisable
│           └── lib/                # Hooks, utils, types
├── config/nginx/      # Reverse proxy
├── scripts/           # Bash ops (backup, deploy, etc.)
└── docs/              # Documentation (commence ici !)
```

## 7. Règles d'or métier

### ⚠️ Cosium est **LECTURE SEULE**

Jamais de `PUT`, `POST` (sauf `/authenticate/basic`), `DELETE`, `PATCH` vers `c1.cosium.biz`. Toute écriture = corruption ERP client = catastrophe.

Le `CosiumClient` n'a que `authenticate()` et `get()` par design. Ne pas ajouter d'autres méthodes HTTP.

### Multi-tenant

Toutes les tables métier ont `tenant_id`. **Aucune query sans `WHERE tenant_id = ?`**. Les repositories prennent `tenant_id` en paramètre systématiquement.

### Pas de logique métier dans les routers

Les routers délèguent aux services. Les services ne connaissent pas FastAPI (pas de `HTTPException`, `UploadFile`, `Response` dedans — lever des `BusinessError`, `NotFoundError`, etc.).

### Pas de `db.query()` dans les routers

Toujours passer par un repository (`apps/api/app/repositories/`).

## 8. Troubleshooting rapide

| Problème | Solution |
|---|---|
| "port 5432 already in use" | `docker compose down` puis `docker compose up` |
| Migrations bloquées | `docker compose exec api alembic upgrade head` |
| Bucket MinIO manquant | Auto-créé au startup ; sinon manuel via console 9001 |
| `JWT_SECRET too short` en prod | Définir ≥ 32 caractères |
| Redis down → auth échoue | Vérifier `docker compose ps redis` |
| Tests échouent getaddrinfo | Mock email_sender dans le test (voir `test_marketing.py`) |

## 9. Guides détaillés

Voir [docs/README.md](./README.md) pour l'index complet.
