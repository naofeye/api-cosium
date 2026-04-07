# Audit Technique OptiFlow AI

Version: finale consolidee apres 3 passes  
Date: 2026-04-07  
Perimetre: repository complet (`backend`, `frontend`, `docs`, `scripts`, `nginx`, compose, CI implicite, tests, outillage)

## Vision d'ensemble

OptiFlow AI est une plateforme metier ambitieuse pour opticiens, structuree autour d'un backend FastAPI riche, d'un frontend Next.js volumineux, d'une integration ERP Cosium en lecture seule, d'un stockage objet MinIO, de taches Celery et d'une couverture fonctionnelle large: CRM, devis, facturation, documents, OCR, PEC, marketing, analytics, billing SaaS et IA.

Le projet n'est pas un simple prototype. Il contient une vraie architecture en couches, une base de schemas et de tests importante, des flux metier nombreux, une separation globale plutot lisible et un effort manifeste de structuration. En revanche, il reste expose a plusieurs risques de production non triviaux: drift schema/BDD, deploiement production fragile, securisation infra incomplete, diagnostics de sante trompeurs, dette de complexite elevee et quelques incoherences entre promesse documentaire et comportement reel.

## Evaluation globale

- Qualite globale percue: moyenne a bonne
- Maturite fonctionnelle: elevee
- Maturite operationnelle: moyenne
- Robustesse production: moyenne a faible selon le flux
- Maintenabilite: moyenne, degradee par la taille de certains modules et par la dispersion des commits/transactions
- Niveau de confiance global: moyen

## Points forts majeurs

- Architecture backend globalement saine: routers, services, repositories, schemas distincts.
- Couverture fonctionnelle large et coherente avec le domaine.
- Presence de nombreux tests backend et frontend.
- Typage present des deux cotes.
- Multi-tenant pris en compte de bout en bout dans beaucoup de flux.
- Effort clair sur la journalisation, la cache, l'audit trail, les exports et l'outillage metier.
- Integration Cosium encapsulee derriere une abstraction ERP plutot bien pensee.

## Risques majeurs

1. Le backend corrige implicitement le schema a chaud au startup via `Base.metadata.create_all(...)` et execute du seeding automatiquement. C'est un contournement des migrations Alembic et un risque de drift/etat non maitrise.
2. La chaine de deploiement production est fragile voire partiellement cassée: `scripts/deploy.sh` appelle un script absent, s'appuie sur `localhost:8000` alors que le compose prod n'expose pas ce port, et l'HTTPS Nginx n'est pas reellement active.
3. Les endpoints d'admin de sante/connexion Cosium testent des credentials globaux et non ceux du tenant courant, ce qui peut produire des diagnostics faux.
4. L'ecran d'administration presente des incoherences front/back de contrat (`health`, `metrics`, `sync status`) et au moins un lien vers une page absente.
5. Le chiffrement des secrets retombe sur une cle derivee du `JWT_SECRET` si `ENCRYPTION_KEY` est vide. C'est dangereux en production et couple inutilement deux secrets differents.
6. La base de code est devenue tres large pour une equipe de reprise: plusieurs gros fichiers concentrent beaucoup de logique, ce qui augmente le cout de maintenance et le risque de regression.

## Decision rapide

- A garder: l'ossature generale du produit, la separation backend, le modele metier, la plupart des integrations, le frontend applicatif, les tests existants comme base de confiance.
- A corriger en priorite: deploiement prod, schema/bootstrap runtime, diagnostics admin/Cosium, gestion des secrets, hygiene repository.
- A corriger en priorite: deploiement prod, schema/bootstrap runtime, diagnostics admin/Cosium, contrats admin front/back, gestion des secrets, hygiene repository.
- A refondre progressivement: gros services a forte densite (`client_service.py`, `erp_sync_service.py`, `export_pdf.py`, plusieurs grosses pages frontend), et certains flux transverses ou les transactions sont trop diffuses.
- A supprimer ou assainir rapidement: artefacts suivis dans Git (`frontend/tsconfig.tsbuildinfo`, `backend/celerybeat-schedule`) et promesses documentaires numeriques devenues inexactes.

## Limites de validation

- Les tests backend n'ont pas pu etre executes localement dans cet environnement car `pytest` n'est pas installe ici.
- Le typecheck frontend a pu etre execute avec succes.
- Les tests frontend n'ont pas pu etre verifies jusqu'au bout dans ce sandbox Windows a cause d'un `spawn EPERM` au chargement de Vitest.
- Les integrations externes reelles (Cosium, Stripe, SMTP, MinIO hors mode mock) n'ont pas ete validees en live.
