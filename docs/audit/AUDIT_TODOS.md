# Todo Lists Priorisees

## Bugs et erreurs a corriger

### P0

- Corriger `scripts/deploy.sh` pour supprimer l'appel au script absent `backup_db.sh`.
- Corriger les checks de sante de deploiement qui utilisent `localhost:8000` alors que le compose prod ne publie pas ce port.
- Corriger les endpoints admin Cosium pour qu'ils testent le tenant courant, pas des credentials globaux.

### P1

- Corriger les compteurs/documentation du README.
- Corriger la metrique `pec_transferred` de fusion client si l'intention est de mesurer uniquement le transfert reel.
- Corriger les contrats admin front/back (`health`, `metrics`, `sync status`).
- Corriger le lien frontend `/admin/data-quality` ou creer la page correspondante.

## Robustesse et securite

### P0

- Retirer `create_all()` du startup backend.
- Rendre le seeding runtime explicite et non automatique.
- Finaliser l'HTTPS Nginx en production.
- Exiger `ENCRYPTION_KEY` hors dev local.

### P1

- Revoir l'usage du cookie `optiflow_authenticated` dans le middleware frontend.
- Clarifier la politique de refresh tokens et de revocation.
- Revoir les locks distribues quand Redis est indisponible.
- Reduire la surface des endpoints publics de diagnostic.

## Ameliorations backend

- Scinder `client_service.py` en sous-services (import, merge, avatar, quick view, CRUD).
- Scinder `erp_sync_service.py` en orchestration, matching, auth ERP, enrichissement.
- Recentrer `export_pdf.py` autour de generateurs specialises par document.
- Uniformiser les transactions et limiter les `db.commit()` disperses dans les repositories.
- Distinguer plus clairement health, readiness, diagnostics admin.

## Ameliorations frontend

- Decouper les grosses pages (`clients`, `dashboard`, certaines pages detail) en hooks/metiers/composants.
- Revoir les gardes d'auth cote middleware et la synchronisation avec la session reelle.
- Reduire les actions basees sur `window.open` et `confirm` quand des composants dedies existent deja.
- Renforcer la coherence UX des flows d'import, fusion, export et erreurs globales.
- Aligner strictement les contrats TypeScript de l'administration avec les schemas backend reels.

## Ameliorations architecture

- Formaliser une politique de bootstrap: migrations, seeding, health, readiness, workers.
- Definir un contrat unique de configuration prod/dev/test.
- Introduire des modules de domaine plus nets pour PEC, CRM, analytics, billing.
- Mettre sous controle les dependances et la croissance des fichiers centraux.

## Ameliorations tests

- Verifier en CI que les compteurs de tests affiches dans la doc restent vrais ou les supprimer.
- Ajouter des tests de deploiement/scripts shell et de configuration prod.
- Ajouter des tests sur les endpoints admin Cosium scopes tenant.
- Ajouter des tests de non-regression sur le bootstrap startup.

## Ameliorations configuration / tooling / DX

- Nettoyer les artefacts suivis (`tsbuildinfo`, `celerybeat-schedule`).
- Renforcer `.gitignore` et verifier l'etat du worktree en CI.
- Normaliser les commandes de test local Windows/Linux/macOS.
- Ajouter une verification CI de coherence docs/config/scripts.

## Ameliorations documentation

- Mettre a jour `README.md` avec des chiffres derives du code ou moins assertifs.
- Documenter le runbook de deploiement reel.
- Documenter les prerequis d'execution tests backend/frontend.
- Documenter les limites du mode Cosium cookies par tenant.

## Quick wins

- Nettoyer les fichiers artefacts suivis.
- Corriger le script de deploiement.
- Aligner les healthchecks prod.
- Mettre a jour le README.
- Interdire le fallback `ENCRYPTION_KEY` hors dev.

## Chantiers lourds

- Refactoriser les gros services backend.
- Refactoriser les grosses pages frontend.
- Rationaliser les transactions DB et les frontieres service/repository.
- Revoir le modele d'observabilite et de sante systeme.

## Points a verifier manuellement

- Deploiement prod complet de bout en bout.
- Connexion Cosium par tenant avec cookies stockes.
- Webhook Stripe reel et mise a jour du statut d'abonnement.
- OCR en environnement Linux/Docker avec toutes les dependances systeme.
- Taches Celery longues et sync multi-tenant en charge.
