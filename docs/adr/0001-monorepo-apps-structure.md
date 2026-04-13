# ADR-0001 — Structure monorepo `apps/`

**Date** : 2026-04-10
**Statut** : Accepted

## Contexte

Le projet OptiFlow comporte un backend FastAPI Python et un frontend Next.js TypeScript.
Initial : `backend/` et `frontend/` à la racine. Migration vers `apps/api/` et `apps/web/`
pour préparer multi-app future (mobile, admin séparé, etc.).

## Décision

Adopter la convention monorepo avec `apps/` comme racine logique :
- `apps/api/` : backend FastAPI (Python 3.12)
- `apps/web/` : frontend Next.js 15 (React 19, TypeScript)
- `apps/<future>/` : possible mobile, admin standalone, CLI, etc.

Tous les outils communs (docker-compose, scripts, docs, config nginx) restent à la racine.

## Conséquences

**Positives**
- Préparé pour ajout d'apps sans refacto
- Convention reconnue (Nx, Turborepo, Bazel)
- Imports clairs : pas d'ambiguïté entre code app et code shared
- Tests CI plus faciles à scoper (matrix par app)

**Négatives**
- Légère augmentation profondeur path (`apps/api/app/services/x.py`)
- Migration douloureuse une fois (renommer toutes refs)
- Quelques outils tiers attendent root direct (vite, certains linters)

## Alternatives écartées

- **Garder `backend/` `frontend/`** : OK aujourd'hui mais bloque évolution
- **Workspaces npm/pnpm dédiés** : sur-engineering pour 2 apps
- **Repos séparés** : perd traçabilité git unifiée + déploiement coordonné
