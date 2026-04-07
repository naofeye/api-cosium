# Plan de Reprise Recommande

## Etape 1. Reprendre la maitrise de l'exploitation

- Corriger `scripts/deploy.sh`.
- Aligner `docker-compose.prod.yml`, Nginx et les healthchecks.
- Finaliser le mode HTTPS reel.
- Documenter un runbook de deploiement et de rollback.

## Etape 2. Retirer les comportements runtime dangereux

- Enlever `create_all()` du startup.
- Sortir `seed_data()` du demarrage automatique.
- Imposer `ENCRYPTION_KEY` en staging/production.
- Clarifier les variables obligatoires et leurs valeurs par environnement.

## Etape 3. Fiabiliser les diagnostics et l'administration

- Corriger les checks Cosium pour utiliser le tenant courant.
- Separer liveness, readiness et diagnostics admin profonds.
- Revoir la politique de sessions/refresh tokens.

## Etape 4. Assainir le repository et la documentation

- Retirer les artefacts suivis.
- Mettre a jour le README et les chiffres clefs.
- Ajouter des garde-fous CI sur docs/config/scripts.

## Etape 5. Revalider la qualite par l'execution

- Rejouer les suites backend et frontend dans un environnement standardise.
- Valider les flux critiques: login, switch tenant, sync Cosium, documents/OCR, export PDF, billing.
- Ajouter des tests de non-regression la ou les bugs de prod ont ete confirmes.

## Etape 6. Reduire la dette de complexite

- Decouper progressivement les gros services backend.
- Decouper les grosses pages frontend.
- Rendre les frontieres transactionnelles plus nettes.
- Isoler les sous-domaines les plus denses: CRM client, sync ERP, exports, PEC.

## Etape 7. Durcir la gouvernance technique

- Definir ce qui est officiellement supporte en prod.
- Distinguer clairement code demo, seed dev, flux reel, scripts de maintenance.
- Mettre sous revue obligatoire tout changement touchant bootstrap, auth, sync et deploiement.
