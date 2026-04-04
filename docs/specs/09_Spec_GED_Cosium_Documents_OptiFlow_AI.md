# 09 — GED, Documents & intégration documentaire Cosium

*Spécification avancée du centre documentaire et des pièces de dossier*

Cette brique a pour mission de centraliser, qualifier, versionner et exploiter les documents du dossier client, tout en restant compatible avec l’écosystème Cosium.

Elle ne doit pas être un simple dépôt de fichiers. Elle doit rendre la documentation exploitable par les workflows, les contrôles de complétude, les PEC et les audits.

## Questions techniques à instruire

- quels documents Cosium permet d’uploader, télécharger ou référencer
- quelles API, exports ou automatisations sont réellement disponibles
- quelle granularité de métadonnées est accessible côté document
- quelles contraintes de nommage, taille, format, droits et historisation existent

## Objectifs du module

- Avoir une liste canonique des pièces par dossier et par phase.
- Détecter automatiquement les documents manquants, expirés, incohérents ou non exploitables.
- Versionner les documents clés et historiser les téléchargements / uploads.
- Exposer des métadonnées utiles aux autres modules : type, statut, validité, source, lien dossier.

## Catalogue documentaire minimal

- attestation de Sécurité sociale
- carte / justificatif mutuelle
- ordonnance
- devis signé
- consentement / RGPD
- fiche opticien
- fiche cabinet d’ophtalmologie
- dossier lunettes
- pièces de PEC
- preuves de paiement ou de livraison

## Fonctions à prévoir

- import manuel et import via connecteur Cosium
- qualification automatique du type documentaire
- OCR léger si utile pour indexation, mais sans dépendre de l’OCR pour la logique principale
- contrôle de présence, de lisibilité, de date et de cohérence métier
- historique des versions, journal des accès, exports et suppressions logiques

## Règles de gouvernance

- aucune pièce critique ne doit être supprimée physiquement sans stratégie d’archivage
- un document doit pouvoir être lié à plusieurs usages métier tout en gardant une seule source
- les statuts documentaires doivent être distincts des statuts de dossier

## Compatibilité Cosium

- Prévoir une couche 'cosium-document-adapter' indépendante, afin de ne pas coupler le cœur GED aux particularités de Cosium.
- Cette couche devra encapsuler téléchargement, upload, mapping des catégories et synchronisation d’identifiants externes.
- Tant que les capacités réelles ne sont pas confirmées, le design doit supporter trois modes : manuel assisté, import/export par fichiers, et API.

## Recherche documentaire

- recherche par type, date, statut, client, dossier, organisme, période
- filtres sur validité et manquants
- moteur de recherche sémantique sur la documentation technique et fonctionnelle séparé des pièces clients

## Sécurité et audit

- droits fins par rôle et par type de document
- journalisation complète des consultations, exports et uploads
- masquage de certaines pièces pour certains profils
- règles de rétention et d’archivage

## Synthèse structurée — Statuts documentaires recommandés

|Statut|Sens|Action typique|
|---|---|---|
|manquant|pièce absente|demander / relancer|
|reçu|pièce présente non validée|contrôle|
|valide|utilisable|aucune|
|à corriger|présente mais inexploitable|remplacement|
|expiré|plus à jour|renouvellement|
|archivé|hors cycle courant|consultation seule|

## Recommandations de mise en œuvre

- Le module GED est un multiplicateur de valeur pour tous les autres modules.
- Le design doit explicitement prévoir l’incertitude sur les API documentaires de Cosium.
- Le front-end doit rendre visibles les trous documentaires immédiatement sur la fiche dossier.
