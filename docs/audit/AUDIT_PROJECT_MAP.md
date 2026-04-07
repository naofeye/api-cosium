# Cartographie Technique du Projet

## Objectif probable du produit

Plateforme SaaS de gestion pour opticiens connectee a l'ERP Cosium, avec consolidation metier autour du CRM client, des dossiers, des devis/factures, des paiements, de la GED/OCR, des PEC, du marketing, de l'analytics et d'assistants IA.

## Technologies identifiees

- Backend: Python 3.12 cible, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, Celery, Redis
- Frontend: Next.js 15 App Router, React 19, TypeScript strict, SWR, Zod, Tailwind CSS 4
- Donnees: PostgreSQL 16
- Stockage documents: MinIO / S3
- Messaging: Mailhog en dev, email HTML Jinja2
- OCR / parsing: pdfplumber, pytesseract, pdf2image, Pillow
- IA: Anthropic / Claude + RAG documentaire local
- Billing: Stripe
- Infra: Docker Compose dev/prod, Nginx

## Structure globale

### Racine

- `backend/`: API, metier, donnees, sync, workers, tests
- `frontend/`: interface Next.js
- `docs/`: specs fonctionnelles/techniques et docs Cosium
- `scripts/`: backup, restore, deploy
- `nginx/`: reverse proxy production
- `docker-compose.yml`: stack locale complete
- `docker-compose.prod.yml`: stack production
- `README.md`: promesse produit et mode d'emploi

### Backend

- `backend/app/main.py`: bootstrap FastAPI, middleware, handlers, startup, routing
- `backend/app/api/routers/`: 40 routeurs source
- `backend/app/services/`: 62 services source
- `backend/app/repositories/`: 27 repositories source
- `backend/app/models/`: 25 modeles source
- `backend/app/domain/schemas/`: 37 schemas source
- `backend/app/integrations/`: Cosium, Stripe, stockage, email, IA
- `backend/app/core/`: config, auth, middleware, cache, chiffrement, logging
- `backend/app/tasks/`: jobs Celery
- `backend/alembic/versions/`: migrations
- `backend/tests/`: 101 fichiers de test backend

### Frontend

- `frontend/src/app/`: 54 pages App Router
- `frontend/src/components/`: 41 composants partages
- `frontend/src/lib/`: API client, auth, hooks, types, schemas, theme
- `frontend/src/middleware.ts`: garde d'acces route-level
- `frontend/tests/`: 28 fichiers de test frontend

## Flux techniques majeurs

### Authentification / session

- Login via `/api/v1/auth/login`
- Cookies httpOnly pour access + refresh token
- Cookie non sensible `optiflow_authenticated` pour aider le frontend/middleware
- Multi-tenant porte par le JWT (`tenant_id`) + verification DB via `TenantUser`

### Donnees metier

- CRUD clients, dossiers, devis, factures, paiements, rappels, marketing
- Couche repository souvent simple
- Couche service concentre l'essentiel de la logique metier

### Sync ERP Cosium

- Abstraction `ERPConnector` / `erp_factory`
- Implementation Cosium read-only
- Sync clients, factures, paiements, ordonnances, references, documents
- Support de cookies navigateur ou credentials classiques

### Documents / OCR

- Upload vers MinIO
- Reference en base
- Extraction OCR et classification par regles
- Telechargement via URL presignee

### IA

- Endpoint copilote
- Contexte dossier / financier / documentaire / marketing
- RAG local sur docs
- Logging d'usage IA en base

### Billing

- Checkout Stripe
- Webhook Stripe
- Statut d'abonnement tenant / organisation

## Zones sensibles

- Bootstrap backend au startup
- Deploiement production et Nginx
- Admin health / admin Cosium
- Services tres volumineux
- Sync ERP et traitements batch
- Exports PDF
- Frontend pages denses avec beaucoup d'etat local

## Zones obscures ou difficiles a valider

- Cohesion exacte des 100+ tests sans execution locale
- Fiabilite des taches Celery en conditions reelles
- Robustesse des integrations Cosium live
- Exhaustivite du modele de donnees vis-a-vis des specs dans `docs/specs`
- Consistance exacte entre les pages frontend les plus denses et les contrats backend sur tous les cas limites
