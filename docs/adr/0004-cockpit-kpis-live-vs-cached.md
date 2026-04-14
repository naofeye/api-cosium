# ADR 0004 — KPIs cockpit : lecture locale (cache) vs live Cosium

**Statut** : Accepte
**Date** : 2026-04-15

## Contexte

Le dashboard cockpit affiche des KPIs metier (CA jour/sem/mois, panier moyen, balance agee, top clients). Deux strategies possibles :

1. **Lecture locale** : interroger PostgreSQL local sur les tables `cosium_invoices` synchronisees periodiquement par Celery
2. **Live Cosium** : appel direct API Cosium a chaque chargement dashboard

## Decision

**Lecture locale via cache PostgreSQL** pour tous les KPIs cockpit.

## Consequences

### Avantages
- **Latence faible** : un dashboard se charge en < 200ms (vs 5-10s pour 5+ appels Cosium en parallele)
- **Resilience** : le dashboard fonctionne meme si Cosium est indisponible (donnees du dernier sync)
- **Aggregations SQL** : `GROUP BY type`, `SUM(total_ti)`, `aging buckets` triviaux en SQL local, complexes via API
- **Rate limiting** : Cosium impose des limites, eviter de saturer pour des KPIs

### Inconvenients
- **Donnees jusqu'a 1h en retard** : sync Celery quotidien (modifiable via beat_schedule)
- **Stockage** : on materialise localement les donnees brutes Cosium

### Mitigation
- Indicateur "Derniere synchro : il y a Xh" sur le dashboard admin
- Sync incrementale planifiee toutes les heures pour les donnees critiques (factures, RDV)
- Endpoints LIVE separes (/cosium-live, /cosium/spectacles/{id}) pour les fiches detail necessitant fraicheur immediate

## Pattern resultant

| Use case | Strategie |
|---|---|
| Cockpit dashboard | Cache local |
| Liste paginee (factures, devis) | Cache local |
| Fiche client onglet "Fidelite" | Live (rare, fraicheur prioritaire) |
| Detail dossier lunettes | Live |
| Recherche fuzzy customer | Live (donnees changent souvent) |
