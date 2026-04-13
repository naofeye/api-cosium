# Business rules — OptiFlow

> Regles metier transverses. Source de verite pour code, tests, support.

## Customer (Client)

- Nom + prenom obligatoires (validation Pydantic)
- Email ou telephone obligatoire pour relances
- `social_security_number` : 13 chiffres + 2 cle (15 total), valide via formule INSEE
- `cosium_id` UNIQUE par tenant — empeche les doublons import Cosium
- Soft-delete via `deleted_at` (audit trail conserve)
- **Anonymisation RGPD** : `last_name`, `first_name`, `email`, `phone` -> "ANONYMIZED",
  preserve les financiers (factures, paiements) pour comptabilite

## Devis

- Statuts : `draft` -> `envoye` -> `signe` | `refuse` | `expire`
- Montant TTC = HT + TVA = part_secu + part_mutuelle + reste_a_charge
- Validite : 90 jours par defaut (`expire` automatique apres)
- 1 dossier (Case) peut avoir N devis, mais 1 seul `signe` actif
- PDF genere via `export_pdf.py` (ReportLab)

## Facture

- Statuts : `a_facturer` -> `facturee` -> `payee` | `partiellement_payee` | `impayee` | `annulee`
- Numero unique sequentiel par tenant et par annee : `FAC-YYYY-NNNNN`
- Cree depuis un Devis `signe` uniquement
- Date emission = date legale (n'est PAS modifiable apres validation)
- TVA : taux 20% par defaut, 10% pour services optometrie

## Paiement

- Statuts : `en_attente` -> `recu` | `retard` | `rejete`
- Modes : `CB`, `CHQ`, `ESP`, `VIR`, `ALMA` (paiement en N fois)
- Tiers payants : `TPSV` (Securite Sociale), `TPMV` (Mutuelle complementaire)
- 1 facture = N paiements possibles (lettrage multi-partiel)
- Remboursements (avoirs) : type `AV`, montant negatif

## PEC (Prise en charge mutuelle)

- Statuts : `soumise` -> `acceptee` | `acceptee_partiellement` | `refusee` | `expiree`
- Auto-relance si `> 30 jours sans reponse mutuelle` (Celery `pec_tasks`)
- Documents obligatoires : ordonnance + devis signe + (optionnel) attestation mutuelle
- Pre-controle avant soumission (`run_precontrol`) : score completude >= 80%, 0 erreur bloquante
- Multi-OCAM supporte (Almerys, Sante Claire, Viamedis, etc.)

## Reconciliation Cosium (lecture seule)

- Sync incremental toutes les 1h (`sync_cosium_daily` Celery beat 6h00)
- Statuts dossier client : `solde` | `solde_non_rapproche` | `partiellement_paye` |
  `en_attente` | `incoherent` | `info_insuffisante`
- Confidence : `certain` | `probable` | `partiel` | `incertain`
- Tolerance financier : 0.02 EUR (rounding bank)
- Anomalies detectees : surpaiement, paiements non rapproches, ordre paiement avant facture

## RGPD / Consentement marketing

- Canaux : `email`, `sms`, `postal`, `telephone`, custom (`telegram`, `whatsapp`)
- Etat default : pas d'enregistrement = pas de consentement (defaut conservateur)
- Toggle opt-in/opt-out cree 1 seul record par (client, canal) — upsert
- Audit log obligatoire si `user_id` fourni (qui a modifie quoi quand)
- Droit a l'oubli : anonymisation 30 jours apres demande (delai legal RGPD)

## Marketing campaigns

- Statuts : `draft` -> `programmee` -> `en_envoi` -> `envoyee` | `echec`
- Segments dynamiques (rules_json) ou statiques (manual_ids)
- Filtres consentement : exclut automatiquement les opt-out du canal cible
- Limite : 5000 destinataires par campagne (anti-spam, scaling)
- Tracking : `MessageLog` enregistre envoi/ouverture/click

## Reminders (relances)

- Plans configurables (cron-like) : J+7, J+15, J+30 etc.
- Manual only par defaut (pas d'auto-envoi sans validation utilisateur)
- 1 reminder par (client, target_id, plan) — pas de spam
- Templates Jinja2 avec variables `{{client_name}}`, `{{montant}}`, etc.

## Multi-tenant

- Chaque tenant = magasin (filiale d'un groupe via `Organization`)
- Isolation BDD : `tenant_id` filtre OBLIGATOIRE sur 100% des queries
- 1 user peut appartenir a N tenants (`TenantUser` pivot)
- Switch tenant : nouveau JWT avec `tenant_id` different
- Group admin (`is_group_admin=True`) : voit tous tenants du groupe via `/admin/group-dashboard`

## Cosium (lecture seule stricte)

Voir `docs/COSIUM_AUTH.md`. Resume :
- ZERO ecriture vers Cosium (pas de PUT/POST/DELETE/PATCH sauf `/authenticate/basic`)
- Sync 1h incremental + 6h complet (Celery beat)
- Cookie expire ~4h : utilisateur doit renouveler manuellement
- Tests : `tests/test_security_regression.py` valide qu'aucun call ecriture est possible

## Stripe (facturation OptiFlow SaaS)

- Plans : `solo` | `reseau` | (add-on `ia_pro`)
- Webhooks : `checkout.completed` -> active | `payment_failed` -> past_due |
  `subscription.deleted` -> canceled | `subscription.updated` -> propage status
- Trial : 30 jours pour nouveaux clients
- Past_due : grace period 7 jours avant suspension UI
