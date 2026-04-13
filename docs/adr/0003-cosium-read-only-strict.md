# ADR-0003 — Cosium en lecture seule stricte

**Date** : 2026-04-12
**Statut** : Accepted (immutable, règle métier)

## Contexte

Cosium est l'ERP de production de nos clients opticiens. Source de vérité financière
et inventaire. Une corruption de données par OptiFlow serait catastrophique
(facturation faussée, paiements perdus, etc.).

L'API Cosium expose des endpoints write (PUT/POST/DELETE/PATCH) — accessibles
techniquement, mais pas dans notre rôle.

## Décision

OptiFlow ne fait JAMAIS d'écriture vers Cosium. Synchronisation strictement
unidirectionnelle : Cosium → OptiFlow.

## Implémentation

- `CosiumClient` n'a QUE 2 méthodes : `authenticate()` et `get()`
- Pas de méthode `put()`, `post()` (sauf auth), `delete()`, `patch()`
- Tests : `test_security_regression.py` valide qu'aucun call ecriture ne peut sortir
- Test architectural CI : grep pour interdire `httpx.put`, `httpx.post`, `httpx.delete` vers `c1.cosium.biz`

Endpoints autorisés (liste exhaustive — voir `docs/COSIUM_AUTH.md`) :
- `POST /authenticate/basic` (seul POST autorisé)
- `GET /customers`, `/invoices`, `/invoiced-items`, `/products`, `/payment-types`

## Conséquences

**Positives**
- Aucun risque de corruption Cosium par bug OptiFlow
- Garantie contractuelle pour le client
- Architecture simple à raisonner (sync UNIDIRECTIONNELLE)
- Audit security trivial (regex grep)

**Négatives**
- Toute action métier dans OptiFlow doit être saisie aussi dans Cosium par l'opticien
  (double saisie pour les workflows hybrides)
- Pas de possibilité de "push" automatique d'un devis OptiFlow vers Cosium
- Limites pour features comme "auto-créer client dans Cosium depuis OptiFlow"

## Évolution future

Si client demande sync bidirectionnelle :
- Nouvel ADR explicite `0XXX-cosium-bidirectional-sync.md`
- Activation feature flag par tenant
- Workflow d'approbation (ex: dry-run + diff visible avant write)
- Audit log toutes écritures Cosium

Pas d'écriture sans cet ADR. La règle actuelle est verrouillée par CLAUDE.md.
