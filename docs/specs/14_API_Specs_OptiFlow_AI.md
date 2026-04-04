# API Specs — OptiFlow AI

## Principes
- API REST JSON versionnée.
- Auth JWT + refresh + RBAC.
- Idempotency key sur endpoints financiers sensibles.
- Webhooks internes pour jobs asynchrones.

## Domaines d'API
- /auth
- /clients
- /dossiers
- /documents
- /devis
- /pec
- /factures
- /paiements
- /banking
- /marketing
- /analytics
- /ai

## Exemples critiques
- POST /paiements
- POST /banking/import-statement
- POST /banking/reconcile
- POST /pec/{id}/relances
- POST /marketing/campaigns
- POST /ai/copilot/query
