# OptiFlow AI

Plateforme metier pour opticiens — CRM, GED, devis, factures, PEC, paiements, relances, marketing, IA.
Branchee sur l'ERP Cosium (lecture seule, 115k+ enregistrements synchronises).

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

## Chiffres cles

| Metrique | Valeur |
|----------|--------|
| Tests backend | 706 (74 fichiers, 100% pass) |
| Pages frontend | 47+ |
| Routers API | 37+ |
| Services metier | 50+ |
| Enregistrements Cosium | 115k+ |
| Documents synchronises | 40k+ (~10 GB) |
| Migrations Alembic | 24+ |
| Ruff lint | 0 erreur |
| TypeScript strict | 0 erreur |
| Next.js build | OK |

## Fonctionnalites principales

- **CRM Client** : CRUD, recherche paginee, vue 360, import/export CSV, detection doublons
- **GED** : upload MinIO, categorisation, completude documentaire
- **OCR + Parsers** : extraction texte (pdfplumber + Tesseract), classification auto (ordonnance, devis, attestation mutuelle, facture), parsers specialises
- **Consolidation PEC** : moteur multi-sources (Cosium, OCR, devis, mutuelles) pour profil client PEC-ready avec score de completude
- **Devis & Factures** : creation avec lignes, calculs automatiques, workflow statut, generation PDF
- **PEC Intelligence (V12)** : soumission tiers payant, workflow, historique, relances automatiques, detection mutuelles
- **Paiements** : enregistrement, idempotence, ventilation multi-factures
- **Rapprochement bancaire** : import CSV, matching auto/manuel, drag & drop
- **Relances** : plans parametrables, templates email HTML Jinja2, priorisation intelligente
- **Marketing CRM** : segments, campagnes email/SMS, consentements RGPD
- **Dashboard** : KPIs financiers, balance agee, graphiques Recharts
- **IA Copilote** : 4 modes (dossier, financier, documentaire, marketing)
- **Multi-tenant** : isolation par magasin, switch tenant, dashboard reseau
- **Sync Cosium** : clients, factures, ordonnances, produits, paiements, tiers payant, documents — lecture seule
- **Onboarding** : wizard 5 etapes, connexion Cosium (OIDC/basic)
- **Facturation SaaS** : integration Stripe, quotas IA
- **Aide** : centre d'aide avec FAQ, raccourcis clavier, contact support
- **Dark mode** : theme sombre avec bascule persistante
- **SSE** : notifications temps reel

## Architecture

Separation en couches stricte :
- **Routers** (35+) : slim, pas de logique — delegue aux services
- **Services** (50+) : logique metier pure, pas de FastAPI, pas de HTTPException
- **Repositories** (19+) : SQL pur, pas de logique metier
- **Schemas** (27+) : validation Pydantic stricte sur toutes les entrees/sorties

```
backend/app/
  api/routers/       # 35+ routes FastAPI
  services/          # 50+ services metier
  repositories/      # 19+ acces BDD
  domain/schemas/    # 27+ schemas Pydantic
  models/            # 17+ modeles SQLAlchemy
  integrations/      # Cosium, MinIO, Stripe, Email, IA, templates Jinja2
  core/              # Config, auth, logging, exceptions, middleware
  templates/         # Templates email HTML
  db/                # Engine, session
  main.py            # Point d'entree FastAPI

frontend/src/
  app/               # 45+ pages Next.js
  components/        # UI (Button, DataTable, Toast, etc.)
  lib/               # API client, auth, types, hooks SWR, schemas Zod
  middleware.ts       # Protection routes
```

## Commandes utiles (Makefile)

```bash
make up              # Demarrer les services (detache)
make down            # Arreter les services
make build           # Rebuild + demarrer
make test            # Tests backend (pytest -q)
make test-v          # Tests backend (verbose)
make lint            # Lint backend (ruff)
make lint-fix        # Lint + auto-fix
make typecheck       # TypeScript check frontend
make check           # lint + typecheck + test
make logs            # Suivre les logs API
make shell           # Shell Python dans le conteneur API
make sync            # Lancer sync Cosium
make redis-flush     # Vider le cache Redis
```

## Tests

```bash
# Backend (660+ tests)
docker compose exec api pytest -v

# Frontend
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

## Securite Cosium

OptiFlow ne modifie JAMAIS les donnees dans Cosium. La synchronisation est unidirectionnelle (Cosium vers OptiFlow, lecture seule). Seul `POST /authenticate/basic` et `GET /*` sont autorises vers l'API Cosium.

Voir `CLAUDE.md` pour les conventions detaillees.
