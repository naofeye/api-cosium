# 10 — Modèle de données détaillé

*Noyau métier, relations, identifiants et principes de persistance*

Ce document définit le socle data d’OptiFlow AI. L’objectif est de garantir un modèle stable, traçable et extensible, capable de soutenir le build incrémental du produit.

Le modèle doit être pensé en agrégats métier, avec identifiants internes persistants, références externes, historisation des statuts et journal d’audit transversal.

## Principes directeurs

- éviter les tables fourre-tout et les colonnes ambiguës
- séparer états calculés, événements et données de référence
- garder des identifiants externes pour Cosium, banques, outils email/SMS et organismes
- prévoir la multi-source et la réconciliation de données

## Agrégats racine

- Client / bénéficiaire
- Dossier
- Document
- Devis / Facture
- PEC
- Paiement / Mouvement bancaire
- Campagne / Interaction
- Utilisateur / Rôle / Audit

## Entités cœur dossier

- client, adresse, contact, préférence canal, consentement
- dossier, type dossier, statut, dates clés, origine, magasin
- prescription / ordonnance, correction, validité, prescripteur
- équipement, monture, verres, options, prix

## Entités finance

- invoice, invoice_line, expected_receivable, payment, payment_allocation, bank_transaction, reconciliation_match, collection_action

## Entités payeurs

- payer_organization, payer_contract, pec_request, pec_document_requirement, pec_status_history, payer_event

## Entités relation client

- crm_profile, segment_membership, campaign, campaign_run, message_log, customer_event, suppression_preference

## Entités documentaires

- document, document_version, document_link, document_validation, external_document_ref

## Règles techniques

- UUID interne sur toutes les entités principales.
- Dates UTC stockées, timezone affichage gérée côté application.
- Soft delete sur les entités utilisateur sensibles ; hard delete limité aux journaux techniques non métier.
- Historique séparé pour les changements d’état critiques.

## Recommandations persistence et lecture

- PostgreSQL comme base transactionnelle principale.
- Schémas logiques ou préfixes par domaine si besoin de clarté.
- Vues matérialisées ou tables de projection pour analytics et dashboards lourds.
- Bus d’événements interne pour synchroniser CRM, finance et documents.

## Synthèse structurée — Entités prioritaires pour le MVP

|Entité|But|Modules consommateurs|
|---|---|---|
|client|référentiel relationnel|tous|
|dossier|pivot opérationnel|tous|
|document|complétude et GED|GED / PEC|
|pec_request|suivi payeurs|PEC / finance|
|payment|encaissements|finance / dashboard|
|bank_transaction|rapprochement|finance|
|campaign|marketing|CRM|
|audit_log|traçabilité|admin / conformité|

## Recommandations de mise en œuvre

- Le modèle doit rester relativement normalisé en transactionnel, puis projeté pour le reporting.
- Les références externes ne doivent jamais remplacer les identifiants internes.
- Chaque module doit pouvoir évoluer sans casser les autres grâce à des contrats d’événements et d’API stables.
