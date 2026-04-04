# 08 — CRM, Marketing automation, Emailing & SMS

*Spécification avancée du moteur de relation client et de croissance*

Cette brique transforme la base clients de l’activité optique en actif business exploitable, dans le respect des consentements et de la pression marketing.

Elle doit permettre des campagnes très ciblées, orientées renouvellement, réactivation, satisfaction, conversion devis et prévention de l’attrition.

## Capacités à obtenir

- extraire et segmenter la base client selon des critères métier fins
- déclencher des campagnes email et SMS à forte pertinence
- automatiser des scénarios relationnels basés sur les événements du dossier
- mesurer le revenu généré par campagne
- respecter consentements, opt-in, blacklists et fréquence de sollicitation

## Base de segmentation

- âge de l’équipement et date estimée de renouvellement
- type d’équipement acheté, gamme, reste à charge et sensibilité prix
- statut relationnel : nouveau, actif, inactif, premium, à risque
- historique devis signés / non signés / abandonnés
- source d’acquisition, canal préféré, consentements et préférences

## Scénarios prioritaires

- relance devis non signé à J+2 / J+7
- lunettes prêtes et rappel retrait
- renouvellement présumé selon date d’équipement
- réactivation clients inactifs > 12 mois
- campagnes mutuelle / pouvoir d’achat / deuxième paire
- sollicitation satisfaction et avis

## Fonctions à construire

- éditeur de segments
- orchestrateur de campagnes
- bibliothèque de templates email/SMS
- moteur d’exclusion et contrôle pression marketing
- tracking ouvertures, clics, réponses, conversions, chiffre d’affaires attribué

## Règles de conformité

- séparer consentement transactionnel et consentement marketing
- journaliser la preuve de consentement et la source
- gérer désinscriptions, STOP SMS et listes d’opposition
- appliquer des seuils de fréquence par période

## Mesure de performance

- taux d’ouverture / clic / réponse
- taux de prise de rendez-vous ou de visite générée
- transformation devis après relance
- CA attribué par campagne, segment, canal et template
- LTV approximative et score d’appétence

## Architecture recommandée

- service crm-core pour profils, tags, consentements et interactions
- service campaign-engine pour segments, scénarios et exécutions
- connecteurs email/SMS interchangeables via adaptateurs
- événements métier en entrée : devis signé, équipement livré, paiement reçu, dossier inactif

## Exemples de score

- score de renouvellement
- score d’abandon devis
- score de valeur client
- score de risque de silence long

## Synthèse structurée — Campagnes initiales recommandées

|Campagne|Déclencheur|Canal|Objectif|
|---|---|---|---|
|Relance devis|devis non signé|email + SMS|conversion|
|Retrait équipement|lunettes prêtes|SMS|service|
|Renouvellement|équipement ancien|email|revenu|
|Réactivation|inactivité longue|email + SMS|retour boutique|
|Satisfaction|livraison terminée|email|avis / NPS|

## Recommandations de mise en œuvre

- Le marketing doit être branché sur le cœur métier : sans événements fiables du dossier, l’automation perd en valeur.
- La vue 360 client doit mixer financier, relationnel, documentaire et commercial.
- Les campagnes doivent être paramétrables mais guidées par des templates métier prêts à l’emploi.
