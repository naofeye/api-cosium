# 07 — Mutuelles, Sécurité sociale & Tiers payant

*Spécification avancée du moteur de prise en charge et de suivi payeurs*

Ce module gère l’intégralité du cycle de prise en charge, depuis la préparation du dossier jusqu’au paiement effectif et au traitement des rejets.

Il doit devenir l’outil de maîtrise opérationnelle des organismes payeurs : AMO, AMC, opérateurs de tiers payant, financeurs complémentaires et cas particuliers.

## Ambition du module

- standardiser les workflows de PEC malgré la diversité des organismes
- rendre visibles les délais réels par mutuelle et opérateur
- industrialiser les relances et le traitement des rejets
- réduire les oublis documentaires avant soumission
- mesurer la qualité de paiement par organisme

## Périmètre métier

- Préparation des pièces avant soumission : ordonnance, devis, attestation, mutuelle, consentements, justificatifs.
- Pilotage des demandes de PEC, accords, refus, compléments, expirations, annulations et validations finales.
- Suivi post-envoi : relances, paiement attendu, rapprochement avec le module financier.

## Objets clés

- organisme payeur
- opérateur de tiers payant
- contrat patient
- demande PEC
- lot documentaire
- retour organisme
- motif de rejet
- historique de contact

## Statuts recommandés

- à préparer
- incomplet
- prêt à soumettre
- soumis
- en analyse
- accord partiel
- accord complet
- complément demandé
- refusé
- expiré
- payé
- clôturé

## Règles de gestion

- Un dossier doit disposer d’une checklist paramétrée par organisme et type de prestation.
- Les délais cibles doivent être historisés par payeur pour améliorer les prévisions.
- Toute PEC doit être liée à une source documentaire versionnée ; aucune pièce clé ne doit être remplacée sans historisation.
- Un rejet ne clôture pas le dossier : il ouvre une action de correction ou d’arbitrage.

## Workflows opératoires

- Pré-contrôle documentaire automatisé avant soumission.
- Soumission manuelle assistée ou connectée si l’API existe.
- Suivi des retours et des relances avec SLA internes.
- Transmission au module paiements quand l’accord est obtenu ou la facture validée.

## Analytique payeurs

- délai moyen entre soumission et accord
- délai moyen entre accord et paiement
- taux de complément demandé
- taux de rejet initial et définitif
- charge de travail interne par organisme

## Connecteurs et limites

- Le design doit supporter plusieurs modes : API officielle, import/export fichiers, assistance opérateur manuelle, scraping interdit sauf cadre légal et technique explicite.
- Claude CLI ou Codex peuvent construire le socle d’intégration, mais la faisabilité réelle dépendra des API, contrats, autorisations et formats fournis par Cosium ou par les opérateurs concernés.

## Priorités MVP

- référentiel organismes + règles documentaires
- workflow de PEC standard avec statuts
- tableau de bord des demandes en attente
- reporting délais et rejets
- liaison avec le moteur financier

## Synthèse structurée — Table des indicateurs payeurs

|Indicateur|Niveau|Usage|
|---|---|---|
|Délai accord|organisme|prévision et arbitrage|
|Délai paiement|organisme|pilotage trésorerie|
|Taux rejet|organisme + type dossier|qualité opérationnelle|
|Temps passé interne|équipe|dimensionnement|
|Montant bloqué|portefeuille|priorisation relances|

## Recommandations de mise en œuvre

- Le module doit être pensé comme un cockpit d’exploitation, pas comme un simple registre de PEC.
- La puissance vient de la normalisation des statuts et des checklists, alors que les canaux d’échange peuvent rester hétérogènes.
- Le lien natif avec le module documents et le module paiements est indispensable.
