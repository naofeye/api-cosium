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
