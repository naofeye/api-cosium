# Prompt pour Claude CLI — Fix CI GitHub Actions

Colle ce prompt tel quel dans Claude CLI (`claude`) depuis le dossier `API COSIUM` :

---

Le workflow CI GitHub Actions échoue sur 5 jobs sur 7. Les 2 qui passent sont Frontend Typecheck et Gitignore Check. Voici le diagnostic précis de chaque échec et ce qu'il faut corriger. Fais tout dans l'ordre.

## JOB 1 : Backend Lint (ruff) — 54 erreurs

Le job exécute `cd apps/api && python -m ruff check app/`.

### Étape 1a : Auto-fix (47 erreurs)
```bash
cd apps/api && python -m ruff check app/ --fix
```
Ça corrige automatiquement :
- Tous les F401 (imports inutilisés) sauf ceux avec `# noqa: F401`
- Tous les I001 (imports mal triés)
- Le UP035 (`from typing import Sequence` → `from collections.abc import Sequence`)

### Étape 1b : Fix manuels (7 erreurs restantes)

1. **`app/core/exceptions.py:59`** — `ImportError_` déclenche N801 + N818. Renomme la classe en `ImportDataError` (ou `DataImportError`). Fais un grep dans tout le projet pour mettre à jour toutes les références à `ImportError_`.

2. **`app/domain/schemas/consolidation.py:12`** — `class FieldStatus(str, Enum)` déclenche UP042. Change en `class FieldStatus(StrEnum)` et ajoute `from enum import StrEnum` (Python 3.11+). Retire l'import de `str` et `Enum` s'ils ne sont plus utilisés.

3. **`app/repositories/base_repo.py:22`** — `class BaseRepository(Generic[T])` déclenche UP046. Change en syntaxe Python 3.12 type parameters : `class BaseRepository[T]:`. Retire l'import de `Generic` et `TypeVar` s'ils ne sont plus utilisés.

4. **`app/services/client_360_service.py:160`** — `reste_du` est assigné mais jamais utilisé (F841). Soit utilise la variable, soit remplace par `_ = resume_financier.reste_du` si c'est intentionnel, soit supprime la ligne.

5. **`app/services/document_service.py`** — `_MAGIC` en majuscule dans une fonction (N806). Renomme en `_magic` (minuscule) car c'est une variable locale de fonction, pas une constante de module.

6. **`app/services/onboarding_service.py:92`** — `raise BusinessError(...)` dans un `except` sans `from` (B904). Change en `raise BusinessError("Impossible de créer le magasin, veuillez réessayer.") from err` (ajoute le `from err` ou `from None`).

### Vérification : `cd apps/api && python -m ruff check app/` doit afficher 0 erreur.

## JOB 2 : Backend Tests — pytest échoue

Le job exécute :
```bash
pip install -r apps/api/requirements.txt
cd apps/api && alembic upgrade head
cd apps/api && python -m pytest tests/ -v --tb=short
```
Avec un service PostgreSQL 16 (optiflow:optiflow@localhost:5432/optiflow_test).

Lance localement :
```bash
docker compose up -d postgres
cd apps/api && python -m pytest tests/ -v --tb=short 2>&1 | tail -50
```

Corrige les tests qui échouent. Les causes probables :
- Import errors suite aux renames de l'étape 1 (ImportError_ → ImportDataError)
- Tests qui importent des symboles supprimés par ruff --fix
- Schema changes non migrées

## JOB 3 : Frontend Build — npm audit ou next build échoue

Le job exécute :
```bash
cd apps/web && npm ci
cd apps/web && npm audit --audit-level=high
cd apps/web && npm run build
```

Lance localement :
```bash
cd apps/web && npm audit --audit-level=high 2>&1
```

Si `npm audit` échoue avec des vulnérabilités high/critical :
- `npm audit fix` pour les fixes automatiques
- Si des vulnérabilités restent et qu'elles sont dans des devDependencies ou des faux positifs, ajoute un `overrides` dans package.json ou change la commande CI pour `npm audit --audit-level=critical`

Ensuite :
```bash
cd apps/web && npm run build 2>&1 | tail -30
```

Si le build Next.js échoue, corrige les erreurs TypeScript ou les imports cassés.

## JOB 4 : Frontend Tests — vitest échoue

Le job exécute :
```bash
cd apps/web && npm ci && npm run test -- --run
```

Lance localement :
```bash
cd apps/web && npm run test -- --run 2>&1 | tail -50
```

Corrige les tests qui échouent. Les tests sont dans `apps/web/tests/`.

## JOB 5 : Security Regression Tests — pytest échoue avec SQLite

Le job exécute :
```bash
cd apps/api && python -m pytest tests/test_security_regression.py -v
```
Avec `DATABASE_URL=sqlite://` (pas de Postgres).

Lance localement :
```bash
DATABASE_URL=sqlite:// cd apps/api && python -m pytest tests/test_security_regression.py -v 2>&1
```

Ce test vérifie que le CosiumClient n'a pas de méthodes d'écriture (PUT/POST/DELETE/PATCH). S'il échoue, c'est probablement un import error ou un problème de compatibilité SQLite.

## Ordre d'exécution

1. Fix lint (ruff --fix + manuels)
2. Fix security regression tests (rapide, pas de DB)
3. Fix backend tests (nécessite Postgres)
4. Fix frontend build (npm audit + next build)
5. Fix frontend tests (vitest)

## Validation finale

```bash
# Lint
cd apps/api && python -m ruff check app/

# Backend tests
docker compose up -d postgres
cd apps/api && python -m pytest tests/ -v --tb=short

# Frontend
cd apps/web && npm audit --audit-level=high
cd apps/web && npm run build
cd apps/web && npm run test -- --run

# Security
DATABASE_URL=sqlite:// cd apps/api && python -m pytest tests/test_security_regression.py -v
```

Quand tout passe, fais un commit :
```
git add -A && git commit -m "fix: resolve all CI failures — lint, tests, build, security"
git push
```
