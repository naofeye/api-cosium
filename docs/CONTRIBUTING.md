# Contributing — OptiFlow AI

## Workflow

1. **Issue d'abord** : ouvrir une issue GitHub avant de coder (sauf hotfix < 30min)
2. **Branche feature** : `git checkout -b feat/nom-court` depuis `main`
3. **Commits conventional** : voir `.gitmessage` (`feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `perf`)
4. **PR avec template** : `.github/PULL_REQUEST_TEMPLATE.md` se charge de pre-remplir
5. **CI verte obligatoire** avant merge (lint + tests + security + Alembic rollback)
6. **Merge** : squash & merge (1 commit clean par PR sur `main`)

## Avant chaque commit

```bash
make lint        # ruff + ESLint
make typecheck   # tsc strict
make test-api    # pytest backend
make test-web    # vitest frontend
```

Ou plus simple : `make check` (lance les 3 premiers).

## Conventions de code

Voir CLAUDE.md (regles fondamentales) :
- Typage strict partout (Python annotations + TS strict)
- Routers SLIM : pas de `db.query()` ni logique metier
- Repos : pas de `db.commit()` (services gerent)
- Services : pas de `HTTPException` (exceptions metier custom)
- Cosium read-only : jamais de `PUT/POST/DELETE/PATCH` vers `c1.cosium.biz`
- Aucun fichier > 300 lignes (objectif), 600 (seuil dur enforcement)
- Aucune fonction > 50 lignes

Tests architecturaux (`tests/test_architecture.py`) verrouillent ces regles.

## Types frontend depuis OpenAPI

Le frontend peut consommer des types auto-generes depuis le schema OpenAPI
de l'API. Source de verite unique : pas de drift entre back/front.

```bash
# Apres modification de routes/schemas backend, exporter le schema :
docker compose exec api python -c "from app.main import app; import json, sys; json.dump(app.openapi(), sys.stdout)" > apps/api/docs/openapi.json

# Puis regenerer les types frontend :
cd apps/web && npm run generate:api-types
```

Usage en TypeScript :

```ts
import type { paths, components } from "@/types/api";

// Endpoint typed :
type GetClient = paths["/api/v1/clients/{client_id}"]["get"];
type ClientResponse = components["schemas"]["ClientResponse"];
```

Adopter progressivement : pas de big-bang refactor des `useApi()` existants.

## Migrations BDD

Voir `docs/ALEMBIC.md`. Resume :
1. Modifier le model SQLAlchemy
2. `make migration MSG="description"` → genere le fichier
3. Verifier le `upgrade()` ET le `downgrade()`
4. `make migrate` pour appliquer
5. CI valide la reversibilite (downgrade -1 puis upgrade head)

## Tests

- Backend : `pytest` avec fixtures `db`, `client`, `auth_headers` dans `conftest.py`
- Frontend : `vitest` + `@testing-library/react` + `@testing-library/user-event`
- Test architectural : `tests/test_architecture.py` (regles CLAUDE.md)

## Pull request

Le template demande :
- Type de changement
- Verification (tests, lint, typecheck)
- Impact (migration ? breaking ? env vars ?)
- Checklist regles projet

CI doit etre verte. Reviewer assigne automatiquement par CODEOWNERS (a configurer).

## Mypy strict (progressif)

OptiFlow est en migration vers `mypy --strict` fichier par fichier. La
config est dans `apps/api/mypy.ini` avec un mode global tolerant
(`ignore_missing_imports`) et des sections `[mypy-app.X.Y]` strict
pour les modules deja types.

**Modules pilots** (CI verte) :
- `app.services._action_items.impact_score` (algorithme deterministe pur)
- `app.services.webhook_service` (signature HMAC, build envelope)
- `app.services.api_token_service` (hash, verify, scope check)
- `app.core.csrf` (middleware CSRF double-submit)

**Pour ajouter un nouveau module** :
1. Verifier qu'il passe localement :
   ```bash
   docker compose exec api python -m mypy --config-file=mypy.ini app/X/Y.py
   ```
2. Ajouter une section dans `mypy.ini` :
   ```ini
   [mypy-app.X.Y]
   strict = True
   ```
3. Ajouter le fichier au job `backend-mypy-pilot` dans `.github/workflows/ci.yml`
4. Commit + push, verifier que la CI passe

**Bonnes pratiques** :
- Annoter les retours `-> int`, `-> str`, `-> dict[str, Any]`, etc.
- Eviter `Any` ; utiliser `object` si vraiment generique
- Pour les classes externes non-typees (Starlette, etc.) : `# type: ignore[misc]`
- `dict` doit avoir des type params : `dict[str, int]` pas `dict`

## Releases

Versionning semver via tags git : `v1.2.3`. CI tag = build prod automatique.
Convention : MAJOR.MINOR.PATCH
- MAJOR : breaking API
- MINOR : nouvelle feature (backward compatible)
- PATCH : bugfix

## Contact

- Issues techniques : GitHub Issues
- Discussion design : GitHub Discussions
- Securite : security@optiflow.ai (pas d'issue publique)
