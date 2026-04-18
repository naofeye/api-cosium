# Guide de contribution — OptiFlow AI

Bienvenue. Ce guide decrit comment contribuer au projet en respectant la charte technique definie dans `CLAUDE.md`.

## Prerequis

- Docker Desktop (Windows/Mac) ou Docker Engine (Linux) avec `docker compose`
- Git
- Editeur recommande : VS Code avec extensions Python, Pylance, ESLint, Prettier

## Demarrer l'environnement

```bash
cp .env.example .env
docker compose up --build
```

Services disponibles :

- API (FastAPI) : http://localhost:8000 (Swagger : `/docs`)
- Frontend (Next.js) : http://localhost:3000
- Mailhog : http://localhost:8025
- MinIO console : http://localhost:9001 (minioadmin / minioadmin)

Login demo : `admin@optiflow.local` / `admin123`

## Structure du monorepo

```
apps/
  api/           # Backend FastAPI (Python 3.12)
  web/           # Frontend Next.js 15
config/          # Nginx, configs infra
scripts/         # Deploiement, backup, restore, health checks
docs/
  adr/           # Architecture Decision Records
  specs/         # Specs metier et fonctionnelles
  audit/         # Audits periodiques
```

## Workflow

1. **Avant de coder** : lire `CLAUDE.md` (charte technique, patterns obligatoires, anti-patterns interdits)
2. Creer une branche depuis `main` : `git checkout -b feat/<description>` ou `fix/<description>`
3. Respecter l'architecture en couches (`api/` → `services/` → `repositories/` → `models/`)
4. Ajouter des tests (pytest pour le backend, Vitest pour le frontend)
5. Verifier que `docker compose up --build` demarre sans erreur
6. Creer une PR vers `main` avec description claire

## Regles non negociables

- **Typage partout** : annotations Python + TypeScript strict
- **Validation Pydantic** pour toutes les entrees/sorties API
- **Services sans FastAPI** : pas de `Request`, `Response`, `HTTPException` dans les services
- **Repositories sans logique metier** : uniquement des requetes BDD
- **Pas de `db.query()` dans un router** : passer par un repository
- **Pas de secrets en dur** : tout via `settings` Pydantic et `.env`
- **Cosium = lecture seule stricte** : UNIQUEMENT `GET` + `POST /authenticate/basic` (voir CLAUDE.md "SECURITE COSIUM")
- **Multi-tenant** : toutes les queries doivent filtrer par `tenant_id` (voir `TenantContext`)
- **Logs structures** : `logger.info("event", key=value)` — pas de `print()`
- **Migrations Alembic** versionnees : jamais `create_all()` en prod

## Tests

```bash
# Backend
docker compose exec api pytest -v

# Frontend
docker compose exec web npm test
```

## Linting et formatage

```bash
# Python (ruff + mypy)
docker compose exec api ruff check .
docker compose exec api mypy app/

# TypeScript
docker compose exec web npm run lint
```

### Reformatage manuel avant PR

Les hooks pre-commit défensifs sont actifs (voir ci-dessous), mais le reformatage automatique est volontairement désactivé pour ne pas toucher au legacy. À run manuellement quand tu modifies un fichier :

```bash
# Python (auto-fix + format)
cd apps/api && python -m ruff check app/ --fix
cd apps/api && python -m ruff format app/

# Frontend (prettier)
cd apps/web && npm run format
```

## Pre-commit hooks

Installation ponctuelle (une fois par clone) :

```bash
pip install pre-commit
pre-commit install
```

Les hooks tournent automatiquement sur `git commit` et bloquent si un problème est détecté. Scope actuel :

- **check-yaml / check-json / check-toml** : syntaxe des fichiers de config
- **check-merge-conflict** : détecte les marqueurs `<<<<<<<` oubliés
- **check-added-large-files** : refuse > 500 kB
- **detect-private-key** : refuse clés privées commitées
- **gitleaks** : scan anti-secrets (tokens, API keys, credentials)

Config : `.pre-commit-config.yaml` à la racine. Les hooks `ruff` / `prettier` / line-endings sont désactivés pour l'instant (ils réécriraient 200+ fichiers legacy au premier run). À réactiver après un commit de nettoyage global.

Diagnostic manuel sur tout le repo :

```bash
pre-commit run --all-files
```

## Commit messages

Suivre la convention [Conventional Commits](https://www.conventionalcommits.org) :

- `feat(scope): ...` — nouvelle fonctionnalite
- `fix(scope): ...` — correction de bug
- `chore(scope): ...` — maintenance (deps, config, CI)
- `docs(scope): ...` — documentation
- `refactor(scope): ...` — refacto sans changement fonctionnel
- `test(scope): ...` — ajout ou modification de tests

Exemple : `feat(auth): ajout endpoint /sessions pour lister les refresh tokens actifs`

## Architecture Decision Records (ADR)

Toute decision architecturale structurante doit faire l'objet d'un ADR dans `docs/adr/`. Utiliser le template `0001-monorepo-apps-structure.md` comme reference.

## Securite

- Ne jamais commiter de secrets (`.env`, credentials, certificats)
- Tout endpoint ecrivant doit etre protege par auth + `require_tenant_role(...)`
- Toute operation sensible doit logger dans `audit_logs`
- Respecter la charte Cosium lecture seule (CLAUDE.md)

## Questions ?

Consulter `CLAUDE.md` en priorite, puis les specs dans `docs/specs/` et les ADRs dans `docs/adr/`.
