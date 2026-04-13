# Architecture Decision Records (ADRs)

> Décisions architecturales importantes, formalisées pour traçabilité.

## Format

Chaque ADR suit un template :
- **Date** : décision
- **Statut** : Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
- **Contexte** : situation, contraintes
- **Décision** : choix retenu
- **Conséquences** : positives + négatives + à surveiller

## ADRs actuels

| # | Titre | Statut |
|---|-------|--------|
| [0001](0001-monorepo-apps-structure.md) | Structure monorepo `apps/` | Accepted |
| [0002](0002-multi-tenant-row-level-security.md) | Multi-tenant via `tenant_id` colonne | Accepted |
| [0003](0003-cosium-read-only-strict.md) | Cosium en lecture seule stricte | Accepted (immutable) |

## Quand créer un ADR ?

- Choix d'architecture qui impacte plusieurs services/modules
- Décision difficile à inverser (DB schema, format API public, dépendance majeure)
- Compromis explicite entre options concurrentes
- Règle métier critique (ex: Cosium read-only)

Pas besoin d'ADR pour : choix d'une lib utilitaire, refacto local, fix de bug.

## Workflow

1. Créer `XXXX-titre-court.md` (numérotation continue)
2. Statut `Proposed` initial
3. Discussion en PR ou réunion d'archi
4. Statut `Accepted` après validation
5. Ne JAMAIS supprimer un ADR — le marquer `Deprecated` ou `Superseded by ADR-YYYY`

## Inspirations

- [Michael Nygard ADR template](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [adr-tools](https://github.com/npryce/adr-tools)
