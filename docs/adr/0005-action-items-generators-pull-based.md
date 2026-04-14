# ADR 0005 — Action items : generateurs pull-based plutot que push-based

**Statut** : Accepte
**Date** : 2026-04-15

## Contexte

L'application doit generer des alertes ("file d'actions intelligente") pour l'opticien :
- Impayes > 30 jours
- Devis dormants > 15 jours
- RDV demain (rappel)
- Renouvellement equipement > 2 ans
- Dossiers incomplets

Deux architectures possibles :

1. **Push-based** : chaque event metier (paiement, devis cree, etc.) declenche immediatement la creation/suppression de l'`action_item` correspondant
2. **Pull-based** : un endpoint `/action-items/refresh` execute periodiquement (ou a la demande) qui calcule l'etat actuel des alertes

## Decision

**Pull-based** via 6 generators dans `action_item_service.generate_action_items()`.

## Consequences

### Avantages
- **Simplicite** : pas de gestion d'event bus, pas de couplage entre services
- **Idempotent** : rejouer = meme etat. Rattrapage facile si une notification a ete loupee
- **Logique centralisee** : tous les criteres dans un seul fichier (`action_item_service.py`)
- **Refactorable** : modifier un seuil (30j -> 45j) = 1 ligne, sans toucher aux services emetteurs

### Inconvenients
- **Latence** : les nouvelles alertes apparaissent au prochain refresh (typiquement < 5 min via Celery)
- **Cout CPU** : recompute complet a chaque refresh (mitigates via `find_existing` + indexes)

### Mitigation
- Refresh declenche en background a chaque sync Cosium reussie
- Bouton "Actualiser" sur la page /actions
- Endpoint POST /action-items/refresh idempotent (deduplication via `find_existing`)

## Generators implementes (6 types)

| Type | Detection |
|---|---|
| dossier_incomplet | required documents manquants par cas |
| paiement_retard | payment.amount_paid < amount_due |
| impaye_cosium | CosiumInvoice.outstanding > 0 ET date > 30j |
| devis_dormant | CosiumInvoice type=QUOTE > 15j sans transformation |
| rdv_demain | CosiumCalendarEvent demain non annule |
| renouvellement | derniere facture entre 2 et 5 ans |
