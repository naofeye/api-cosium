# 06 — Paiements, Encaissements & Rapprochement bancaire

*Spécification avancée du moteur financier opérationnel*

Ce document définit le module financier central d’OptiFlow AI. Il doit fournir une vision exacte, traçable et exploitable des facturations et encaissements liés aux dossiers optiques.

Le module est conçu pour fonctionner comme une brique indépendante, exposée par API, afin d’être intégrée au core dossier client, au tableau de bord de pilotage et aux modules marketing et relance.

## Valeur ajoutée attendue

- savoir immédiatement qui doit encore payer et pourquoi
- croiser paiements bancaires, flux Sécurité sociale et paiements mutuelles
- détecter les dossiers rentables, bloqués ou à relancer
- préparer la comptabilité opérationnelle sans ressaisie
- historiser toute décision manuelle et tout rapprochement

## Objectifs métier

- Suivre chaque dossier au niveau devis, facture, échéance, encaissement et solde.
- Distinguer les flux par payeur : client, AMO, AMC, financeur tiers, remboursement exceptionnel.
- Mettre à jour en continu le statut financier du dossier et les actions à mener.
- Réduire les pertes de temps liées aux vérifications manuelles sur relevés et portails payeurs.

## Objets métier à couvrir

- facture et ligne de facture
- paiement et allocation de paiement
- échéance attendue
- mouvement bancaire importé
- lettrage / proposition de rapprochement
- relance de paiement
- journal des anomalies et des arbitrages humains

## Règles de gestion

- Un dossier peut avoir plusieurs payeurs et plusieurs échéances.
- Un paiement peut couvrir plusieurs dossiers ; une allocation détaillée est donc obligatoire.
- La date de valeur bancaire et la date comptable interne doivent être conservées séparément.
- Aucun mouvement importé ne doit être détruit ; seules des règles de statut et d’exclusion doivent être appliquées.
- Toute correction manuelle doit être auditée avec auteur, motif, ancienne valeur et nouvelle valeur.

## Pipeline de traitement

- 1. Création des attentes financières à partir du devis signé, des règles AMO/AMC et des restes à charge.
- 2. Génération d’échéances théoriques et dates prévues d’encaissement.
- 3. Import des mouvements bancaires et des retours payeurs externes.
- 4. Moteur de matching : exact, tolérance, heuristique, manuel.
- 5. Lettrage, mise à jour du solde, déclenchement d’alertes et de relances.

## Rapprochement bancaire

- Importer relevés CSV, XLSX, OFX ou API bancaire via un connecteur dédié.
- Normaliser libellés, montants, références et contreparties.
- Scorer les propositions de matching selon montant, date, nom, IBAN, référence dossier, référence facture, mutuelle et historique.
- Présenter les rapprochements ambigus dans une file de revue humaine priorisée par montant et ancienneté.

## Sorties attendues

- Vue dossier : facturé, payé, restant, retard, dernier mouvement, prochaines actions.
- Vue caisse / banque : mouvements non rapprochés, flux anormaux, doublons potentiels.
- Vue organismes : délai moyen de paiement, taux de rejet, taux de complément, temps passé.
- Vue direction : trésorerie attendue, cash collecté, aging balance, restes à percevoir par payeur.

## Cas limites à traiter

- paiement partiel client avec acompte puis solde
- paiement mutuelle inférieur à l’attendu
- double virement pour un même dossier
- virement groupé couvrant plusieurs dossiers
- rejet AMO/AMC après un premier accord
- annulation ou refacturation partielle d’un équipement

## Découpage technique recommandé

- service finance-core pour les entités, statuts et calculs
- service bank-ingest pour l’import bancaire et la normalisation
- service reconciliation pour les règles de matching et la revue
- service collections pour relances et workflows
- service analytics-finance pour KPI et prévisions

## Synthèse structurée — Flux à suivre

|Flux|Déclencheur|Sortie principale|Priorité|
|---|---|---|---|
|Acompte client|Devis signé|échéance + reçu|Haute|
|Paiement client final|Livraison / facturation|lettrage dossier|Haute|
|AMO Sécurité sociale|facture télétransmise|attendu AMO|Haute|
|AMC / mutuelle|PEC validée ou facture AMC|attendu AMC|Haute|
|Régularisation / rejet|retour organisme|anomalie + relance|Moyenne|
|Virement groupé|relevé bancaire|allocation multi-dossiers|Haute|

## Recommandations de mise en œuvre

- Ce module doit être livré tôt dans le programme, car il alimente à la fois le pilotage financier, les relances et la connaissance client.
- L’interface doit privilégier les files d’actions et les écarts, pas seulement les historiques.
- Le moteur de règles doit rester configurable sans toucher au code pour les seuils de tolérance, règles de matching et délais cibles.
