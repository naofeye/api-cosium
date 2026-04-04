# OptiFlow AI

Plateforme metier pour opticiens — CRM, GED, devis, factures, PEC, paiements, relances, marketing, IA.
Branchee sur l'ERP Cosium (lecture seule).

## Demarrage rapide

```bash
# Prerequis : Docker Desktop installe et lance
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Swagger | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 (minioadmin/minioadmin) |
| Mailhog | http://localhost:8025 |

**Login demo** : `admin@optiflow.local` / `Admin123`

## Stack technique

- **Backend** : Python 3.12, FastAPI, SQLAlchemy 2.x, PostgreSQL 16, Alembic, Celery + Redis
- **Frontend** : Next.js 15, React 19, TypeScript (strict), Tailwind CSS 4, shadcn/ui, Recharts
- **Infra** : Docker Compose (PostgreSQL, Redis, MinIO, Mailhog, API, Web)
- **Tests** : pytest + httpx (backend), vitest + testing-library (frontend)
- **Lint** : ruff (backend), prettier + tsc (frontend)
- **CI** : GitHub Actions

## Structure du projet

```
.
├── backend/
│   ├── app/
│   │   ├── api/routers/       # 29 routes FastAPI (slim, pas de logique)
│   │   ├── services/          # 34 services metier
│   │   ├── repositories/      # 18 acces BDD
│   │   ├── domain/schemas/    # 20 schemas Pydantic (validation)
│   │   ├── models/            # 15 fichiers SQLAlchemy (25 tables)
│   │   ├── integrations/      # Cosium, MinIO, Stripe, Email, IA
│   │   ├── core/              # Config, auth, logging, exceptions, middleware
│   │   ├── db/                # Engine, session
│   │   └── main.py            # Point d'entree FastAPI
│   ├── alembic/               # 18 migrations
│   ├── tests/                 # 44 fichiers de tests (279 tests)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/               # 30 pages Next.js
│   │   ├── components/        # UI (Button, DataTable, Toast, etc.)
│   │   ├── lib/               # API client, auth, types, hooks SWR, schemas Zod
│   │   └── middleware.ts      # Protection routes
│   ├── tests/                 # 6 fichiers de tests (36 tests)
│   └── package.json
├── docs/
│   ├── specs/                 # 23 specs fonctionnelles et techniques
│   ├── cosium/                # Documentation Cosium + PDFs API
│   └── directives/            # Chartes de developpement
├── .github/workflows/         # CI GitHub Actions
├── docker-compose.yml
├── docker-compose.prod.yml
├── CLAUDE.md                  # Directive maitre pour Claude CLI
├── TODO.md                    # Backlog original (30 etapes completees)
└── TODO_V2.md                 # Backlog qualite/production (22 etapes)
```

## Tests

```bash
# Backend (279 tests, couverture 88%)
docker compose exec api pytest -v

# Frontend (70+ tests)
docker compose exec web npx vitest run
```

## Lint

```bash
# Backend
docker compose exec api ruff check app/
docker compose exec api ruff format --check app/

# Frontend
docker compose exec web npx tsc --noEmit
docker compose exec web npx prettier --check "src/**/*.{ts,tsx}"
```

## Architecture

Separation en couches stricte :
- **Routers** : slim, pas de logique — delegue aux services
- **Services** : logique metier pure, pas de FastAPI, pas de HTTPException
- **Repositories** : SQL pur, pas de logique metier
- **Schemas** : validation Pydantic stricte sur toutes les entrees/sorties

Voir `CONTRIBUTING.md` pour les conventions detaillees.
