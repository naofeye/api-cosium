# Evolution de l'Audit Entre les 3 Passes

## Passe 1

Objectif: etablir l'etat des lieux complet du repository, la cartographie, les risques visibles de premier niveau et les livrables initiaux.

Apports:

- Cartographie structurelle du backend, frontend, docs, scripts et infra.
- Identification des risques majeurs initiaux:
  - bootstrap backend avec `create_all()` et `seed_data()`
  - faiblesse du deploiement production
  - dette de complexite sur plusieurs gros modules
  - ecart entre promesse README et inventaire reel
- Production des livrables initiaux a la racine.

## Passe 2

Objectif: relire le repository et relire les livrables pour verifier completude, coherence, precision et profondeur.

Corrections / enrichissements apportes:

- Ajout explicite du diagnostic sur les endpoints admin Cosium non scopes par tenant.
- Ajout du risque de chiffrement derive du `JWT_SECRET`.
- Ajout du sujet hygiene repository (`tsbuildinfo`, `celerybeat-schedule` suivis).
- Ajout des limites de validation d'execution:
  - typecheck frontend verifie
  - tests backend non executables localement faute de `pytest`
  - Vitest bloque ici par `spawn EPERM`
- Renforcement du plan de reprise en separant exploitation, bootstrap, diagnostics, hygiene repo et dette de complexite.

## Passe 3

Objectif: challenger les conclusions precedentes, chercher les angles morts et durcir l'exigence.

Durcissements finaux:

- Reclassement du sujet de deploiement prod comme risque critique et non simplement eleve.
- Mise en avant du caractere trompeur des diagnostics admin/Cosium.
- Ajout d'un angle mort rate en passe 1: incoherences de contrat entre l'ecran admin frontend et les reponses backend (`health`, `metrics`, `sync status`), plus un lien casse vers `/admin/data-quality`.
- Clarification que le projet est fonctionnellement riche mais operationnellement encore fragile.
- Ajout de la nuance importante:
  - il ne faut pas refondre tout le projet
  - il faut d'abord reprendre la maitrise de l'exploitation et du bootstrap
- Consolidation des livrables pour une lecture decisionnelle plus exploitable.
