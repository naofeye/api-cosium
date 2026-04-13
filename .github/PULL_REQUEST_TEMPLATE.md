<!--
Format de titre conventional commits:
  feat(scope): description
  fix(scope): description
  refactor(scope): description
-->

## Resume

<!-- Quoi & pourquoi en 2-3 phrases. Lien issue/ticket si applicable. -->

## Type de changement

- [ ] feat — nouvelle fonctionnalite
- [ ] fix — correction de bug
- [ ] refactor — refacto sans changement comportement
- [ ] perf — amelioration performance
- [ ] docs — documentation seulement
- [ ] chore — outillage, deps, configs
- [ ] test — ajout/correction de tests

## Verification

<!-- Comment as-tu valide ces changements ? -->

- [ ] Tests pytest passent : `make test-api`
- [ ] Tests frontend passent : `make test-web`
- [ ] Lint OK : `make lint`
- [ ] Typecheck OK : `make typecheck`
- [ ] Teste manuellement via Swagger / UI

## Impact & risque

<!-- Migration BDD ? Breaking change ? Variable d'env nouvelle ? Service externe ? -->

- [ ] Pas de migration Alembic
- [ ] Pas de breaking change API
- [ ] Pas de nouvelle variable d'env
- [ ] Pas de modification Cosium (lecture seule garantie)

## Checklist regles projet (CLAUDE.md)

- [ ] Pas de logique metier dans les routers
- [ ] Pas de `db.commit()` dans les repos
- [ ] Schemas Pydantic sur tous les endpoints (entree + sortie)
- [ ] Aucun appel ecriture vers Cosium (PUT/POST hors auth/DELETE/PATCH)
- [ ] Aucun fichier > 300 lignes
- [ ] Aucune fonction > 50 lignes

## Screenshots (UI)

<!-- Avant/Apres pour les changements visuels -->
