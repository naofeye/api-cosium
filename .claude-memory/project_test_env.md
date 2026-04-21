---
name: Environnement de test — credentials Cosium en clair autorises
description: Le projet OptiFlow tourne en TEST, pas en production. Ne pas revoquer/nettoyer les credentials Cosium dans .env meme si la TODO les flag comme faille P0.
type: project
originSessionId: 861777ae-f82c-4a2a-9dd3-a88da9123f7c
---
Le `.env` contient `COSIUM_LOGIN=AFAOUSSI`, `COSIUM_PASSWORD=Cosium@150623` et `COSIUM_ACCESS_TOKEN=...` en clair, committe dans le repo.

**Why:** Environnement de test/dev actif. Les creds sont intentionnellement laisses pour permettre les tests Cosium sans re-setup. La TODO Phase 0 item 10 (TODO_MASTER.md:45) les flag P0 "revoquer immediatement" — c'est valable UNIQUEMENT au moment du passage en prod.

**How to apply:** Ne jamais proposer de rotation de creds, `git filter-branch`, ou nettoyage de l'historique git sans demande explicite. Traiter item 10 de TODO_MASTER Phase 0 comme "report a la mise en prod". Idem pour `POSTGRES_PASSWORD=optiflow` et `minioadmin:minioadmin` (item 23) tant qu'on est en test.
