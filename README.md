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
- **Infra** : Docker Compose (PostgreSQL, Redis, MinIO, Mailhog, API, Web, Worker, Beat)
- **Tests** : pytest + httpx (backend, 740 tests), vitest + testing-library (frontend, 133 tests)
- **Lint** : ruff (backend), tsc strict (frontend)
- **OCR** : Tesseract OCR + pdfplumber + poppler-utils
- **CI** : GitHub Actions

## Chiffres cles

| Metrique | Valeur |
|----------|--------|
| Tests backend | 740 (98 fichiers, 100% pass) |
| Tests frontend | 133 (28 fichiers, 100% pass) |
| Pages frontend | 49 |
| Routers API | 38 |
| Services metier | 53 |
| Repositories | 25 |
| Schemas Pydantic | 35 |
| Modeles SQLAlchemy | 23 |
| Commits | 66+ |
| Migrations Alembic | 30 |
| Enregistrements Cosium | 115k+ |
| Documents synchronises | 40k+ (~10 GB) |
| Ruff lint | 0 erreur |
| TypeScript strict | 0 erreur |

## Fonctionnalites principales

- **CRM Client** : CRUD, recherche paginee, vue 360, import/export CSV, detection doublons, fusion clients
- **GED** : upload MinIO, categorisation, completude documentaire, drag & drop
- **OCR + Parsers** : extraction texte (pdfplumber + Tesseract), classification auto (ordonnance, devis, attestation mutuelle, facture), parsers specialises par type de document
- **Consolidation PEC** : moteur multi-sources (Cosium, OCR, devis, mutuelles) pour profil client PEC-ready avec score de completude
- **PEC Intelligence** : soumission tiers payant, workflow complet, historique, relances automatiques, detection mutuelles, operateurs OCAM, preparation PEC guidee
- **Devis & Factures** : creation avec lignes, calculs automatiques, workflow statut, generation PDF, export FEC
- **Paiements** : enregistrement, idempotence, ventilation multi-factures
- **Rapprochement bancaire** : import CSV, matching auto/manuel, drag & drop
- **Relances** : plans parametrables, templates email HTML Jinja2, priorisation intelligente
- **Marketing CRM** : segments, campagnes email/SMS, consentements RGPD
- **Dashboard** : KPIs financiers, balance agee, graphiques Recharts, statistiques avancees
- **IA Copilote** : 4 modes (dossier, financier, documentaire, marketing), quotas par plan
- **Multi-tenant** : isolation par magasin, switch tenant, dashboard reseau
- **Sync Cosium** : clients, factures, ordonnances, produits, paiements, tiers payant, documents — lecture seule
- **Onboarding** : wizard 5 etapes, connexion Cosium (OIDC/basic)
- **Facturation SaaS** : integration Stripe, plans (Solo, Reseau, IA Pro)
- **Aide** : centre d'aide avec FAQ, raccourcis clavier, contact support
- **Dark mode** : theme sombre avec bascule persistante
- **SSE** : notifications temps reel
- **RGPD** : anonymisation, export donnees, consentements
- **Audit trail** : journalisation de toutes les operations sensibles

## Architecture

```
                    +-------------------+
                    |   Next.js 15      |
                    |   (Frontend)      |
                    |   Port 3000       |
                    +--------+----------+
                             |
                    +--------v----------+
                    |   FastAPI         |
                    |   (Backend API)   |
                    |   Port 8000       |
                    +---+----+-----+----+
                        |    |     |
              +---------+    |     +----------+
              |              |                |
    +---------v--+   +------v------+   +-----v-----+
    | PostgreSQL |   |    Redis    |   |   MinIO    |
    |   (BDD)    |   |  (Cache +  |   | (Stockage) |
    | Port 5432  |   |  Celery)   |   | Port 9000  |
    +------------+   | Port 6379  |   +-----------+
                     +------+------+
                            |
                  +---------+---------+
                  |                   |
           +------v-----+    +-------v----+
           | Celery      |    | Celery     |
           | Worker      |    | Beat       |
           | (Taches)    |    | (Cron)     |
           +-------------+    +------------+
```

Separation en couches stricte :
- **Routers** (38) : slim, pas de logique — delegue aux services
- **Services** (53) : logique metier pure, pas de FastAPI, pas de HTTPException
- **Repositories** (25) : SQL pur, pas de logique metier
- **Schemas** (35) : validation Pydantic stricte sur toutes les entrees/sorties

```
backend/app/
  api/routers/       # 38 routes FastAPI
  services/          # 53 services metier
  repositories/      # 25 acces BDD
  domain/schemas/    # 35 schemas Pydantic
  models/            # 23 modeles SQLAlchemy
  integrations/      # Cosium, MinIO, Stripe, Email, IA, templates Jinja2
  core/              # Config, auth, logging, exceptions, middleware
  templates/         # Templates email HTML (Jinja2)
  db/                # Engine, session
  main.py            # Point d'entree FastAPI

frontend/src/
  app/               # 49 pages Next.js (App Router)
  components/        # UI (Button, DataTable, Toast, StatusBadge, KPICard, etc.)
  lib/               # API client, auth, types, hooks SWR, schemas Zod
  middleware.ts      # Protection routes authentifiees
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
# Backend (740 tests, 100% pass)
docker compose exec api pytest -v

# Frontend (133 tests, 100% pass)
cd frontend && npx vitest run
```

## Lint

```bash
# Backend (zero erreur)
docker compose exec api ruff check app/

# Frontend (zero erreur TypeScript strict)
cd frontend && npx tsc --noEmit
```

## Securite Cosium

OptiFlow ne modifie JAMAIS les donnees dans Cosium. La synchronisation est unidirectionnelle (Cosium vers OptiFlow, lecture seule). Seul `POST /authenticate/basic` et `GET /*` sont autorises vers l'API Cosium.

Le `CosiumClient` n'expose que deux methodes : `authenticate()` (seul POST autorise) et `get()` (lecture seule). Aucune methode PUT, POST (hors auth), DELETE ou PATCH n'existe.

Voir `CLAUDE.md` pour les conventions detaillees.
