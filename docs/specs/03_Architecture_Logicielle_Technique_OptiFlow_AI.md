# Architecture logicielle et technique

*Socle evolutif, modules, donnees et principes d'implementation*

> But du document: fournir un support de cadrage directement exploitable dans un dossier local de travail pour lancer le build du logiciel par briques.

## 1. 1. Principes d'architecture

- Adopter une architecture modulaire par domaines, avec interfaces explicites, evenements metier et separation stricte entre coeur de domaine, infrastructure et experience utilisateur.

- Conserver un back-end Python clair, testable et extensible, tout en laissant le front-end evoluer independamment.

- Prevoir des connecteurs externes isoles afin que Cosium, la banque, l'email, le SMS ou d'autres sources puissent etre actives progressivement.


## 2. 2. Stack recommandee

- Front-end: Next.js + React + TypeScript + design system maison avec composants reutilisables.

- Back-end: Python + FastAPI pour les APIs synchrones et l'administration metier.

- Workers asynchrones: Celery ou Dramatiq avec Redis pour les traitements longs, import de documents, campagnes, rapprochement, scoring.

- Base relationnelle: PostgreSQL pour toutes les donnees transactionnelles et analytiques de base.

- Stockage documentaire: S3 compatible pour les fichiers et leurs versions.

- Moteur de recherche documentaire: index hybride full-text + embeddings pour la documentation Cosium et les pieces internes.

- Observabilite: logs structures, traces, journal d'audit, alerting et monitoring applicatif.


## 3. 3. Decoupage par services logiques

- Service Core CRM: clients, beneficiaires, contacts, consentements, interactions.

- Service Dossier & Workflow: dossier, statuts, checklist, prochaines actions, timeline.

- Service Documents: pieces, versions, metadonnees, indexation, controle de completude.

- Service Vente & Devis: prescriptions, equipements, devis, marges, remises, conversion.

- Service PEC & Organismes: mutuelles, securite sociale, reponses, rejets, relances.

- Service Facturation & Paiements: factures, echeances, paiements, avoirs, restes a percevoir.

- Service Banking: import releves, connecteurs banque, regles de matching, rapprochement.

- Service Marketing: segments, campagnes, templates, evenements, statistiques.

- Service IA: assistants, retrieval, prompts, evaluation, garde-fous, historique des reponses.

- Service Auth & Admin: utilisateurs, roles, permissions, audit, parametres.


## 4. 4. Architecture logique cible

- Le front-end appelle une API Gateway logique exposee par FastAPI. Derriere, les domaines restent separes par modules Python et ne partagent pas directement leur persistence sans contrats clairs.

- Les traitements longs passent par une file de jobs. Les evenements metier importants publient des notifications internes exploitees par le marketing, l'IA, l'analytique et le recouvrement.

- Le stockage documentaire et l'index de recherche sont traites comme des composants transverses, accessibles par service mais gouvernes par des policies communes.


## 5. 5. Style d'implementation Python

- Organisation inspiree de domain-driven design leger: domaines, applications, infrastructures, interfaces.

- Regles fortes: schemas Pydantic, services explicites, repositories seulement quand utiles, tests unitaires sur les regles metier, tests d'integration sur les connecteurs.

- Chaque module doit pouvoir etre active ou enrichi sans casser les autres. Les dependances de domaine vers domaine passent par contrats ou evenements, jamais par acces direct non maitrise.


## 6. 6. Modele de donnees coeur

- Entites primaires: Client, Beneficiaire, Dossier, Prescription, Equipement, Devis, Facture, Paiement, MouvementBancaire, OrganismePayeur, PEC, Document, Campagne, Interaction, Utilisateur, AuditLog.

- Entites de support: ConsentementMarketing, TagClient, ModePaiement, RegleRapprochement, Tache, Relance, Anomalie, Notification, TemplateMessage.

- Il faut un identifiant technique stable par entite, un identifiant metier lisible si necessaire, des timestamps, un statut, un createur et un historique minimal.


## 7. 7. Evenements metier a prevoir

- DossierCree, PieceManquanteDetectee, DevisSigne, PECSoumise, PECRefusee, FactureEmise, PaiementRecu, PaiementRapproche, EcartDetecte, RelanceEnvoyee, CampagneLancee, DocumentAjoute, DocumentTelechargeDepuisCosium.

- Ces evenements doivent alimenter les tableaux de bord, les alertes, l'automatisation et les logs d'audit.


## 8. 8. Securite et gouvernance

- RBAC par profils: direction, magasin, back office, marketing, finance, administrateur technique.

- Journal d'audit obligatoire sur les operations sensibles: suppression, modification de paiement, changement de statut de dossier, relance, edition de document, export de base client.

- Chiffrement des secrets, gestion separee des credentials connecteurs, cloisonnement des environnements dev / preprod / prod.


## 9. 9. Strategie IA

- Concevoir une couche provider-agnostic. Les fournisseurs IA doivent etre remplacables sans rearchitecture du produit.

- Isoler les prompts, jeux d'evaluation, policies de securite et journaux d'inference.

- Utiliser retrieval sur documents autorises, pas d'acces libre direct au coeur de donnees sans couche applicative et sans controle de permissions.


## 10. 10. Connecteurs prioritaires

- Cosium: lecture d'informations, documents disponibles, upload/download si les APIs ou actions sont possibles.

- Banque: import de fichiers standard et, plus tard, connecteur direct si utile.

- Email et SMS: envoi de campagnes, messages transactionnels, relances et traçabilite.

- Stockage documentaire local ou cloud selon environnement.


## 11. 11. Decoupage MVP / V2 / V3

- MVP: CRM, dossier, documents, vue financiere de base, paiements, rapprochement manuel assiste, dashboard initial, base documentaire Cosium.

- V2: PEC, securite sociale, automatisation de relances, import bancaire avance, tableaux d'age, campagnes simples email/SMS.

- V3: scoring, prevision d'encaissement, orchestration avancée, multi-sites, benchmark mutuelles, copilotes IA specialises.


## 12. 12. Structure de repository recommandee

- apps/web pour le front-end, apps/api pour FastAPI, apps/workers pour les jobs, packages/common pour schemas et libs partagees, packages/prompts pour IA, infrastructure pour docker/compose/terraform si besoin, docs pour le cadrage et la documentation d'exploitation.

- Des conventions strictes doivent eviter le melange entre logique metier, UI et integration externe.

