# Cadrage metier et fonctionnel complet

*Cartographie des flux, cas d'usage, modules et exigences de valeur*

> But du document: fournir un support de cadrage directement exploitable dans un dossier local de travail pour lancer le build du logiciel par briques.

## 1. 1. Macro-processus metier cible

- Le logiciel couvre le cycle complet: acquisition client, creation dossier, collecte documentaire, prescription, devis, vente, prise en charge, facturation, encaissements, rapprochement, relances, service apres-vente et reactivation marketing.

- Chaque evenement metier doit creer une trace exploitable: qui a fait quoi, sur quel dossier, a quelle date, avec quel document et avec quel impact financier.


## 2. 2. Domaine CRM et dossier client

- Creation et enrichissement du profil client, du beneficiaire et des ayants droit si necessaire.

- Vue 360: coordonnees, consentements, historique d'achat, mutuelle, preferences, communication, documents, tickets d'action et statut financier.

- Journal des interactions: appel, email, SMS, passage magasin, relance, commentaire interne, taches et compte-rendus.


## 3. 3. Domaine documentaire et GED

- Catalogue central de documents: ordonnance, carte Vitale, mutuelle, attestation, devis, facture, justificatifs de paiement, simulation PEC, documents telecharges de Cosium, documents uploades par l'equipe.

- Classification automatique par type de document et rattachement a un dossier ou a un client.

- Verification des pieces obligatoires selon le contexte: creation dossier, PEC, facturation, remboursement, litige, renouvellement.

- Detection de pieces manquantes, incompletes, incoherentes ou perimees.


## 4. 4. Domaine vente et devis

- Preparation du devis a partir de la prescription, de l'equipement choisi, des regles de prise en charge et des contraintes commerciales.

- Controle du reste a charge, de la marge, des remises, des options et de la conformite du panier.

- Suivi du statut commercial: brouillon, propose, signe, converti, annule, perdu, a relancer.


## 5. 5. Domaine mutuelles, tiers payant et securite sociale

- Gestion complete de la PEC: demande, simulation, reponse, complements, accords, refus, relance et cloture.

- Traque des motifs de rejet, du nombre d'aller-retour, du delai de traitement et du delai de paiement reel par organisme.

- Vision comparative des organismes: rapidite, taux d'acceptation, qualite de paiement, motif de litige, montant moyen, ecarts.


## 6. 6. Domaine facturation

- Gestion distincte des flux clients, securite sociale et AMC, avec dependances, echeances et pieces justificatives.

- Controle des statuts: a facturer, facture, partiellement paye, solde, rejete, en litige, annule, passe en relance.

- Calcul des montants attendus, percus, restants et litigieux par dossier et par payeur.


## 7. 7. Domaine paiements et cash management

- Historique detaille des paiements client: acompte, solde, espece, carte, virement, cheque, paiement fractionne, remises et annulations.

- Suivi des paiements mutuelles et securite sociale: date attendue, date effective, reference, ecart, paiement partiel, retenue ou rejet.

- Tableau d'age des creances avec priorisation des relances et prevision d'encaissement.


## 8. 8. Domaine rapprochement bancaire

- Import de releves bancaires ou synchronisation via connecteur bancaire.

- Reconnaissance des virements entrants et tentative de rapprochement automatique avec dossiers, factures, organismes et paiements attendus.

- File des ecarts a arbitrer: paiement sans reference, montant incomplet, doublon, imputation incertaine, remboursement, rejet bancaire.


## 9. 9. Domaine recouvrement et relances

- Plans de relance parametrables par type de payeur et anciennete.

- Generation de taches, emails, SMS ou scripts d'appel.

- Historique complet des relances et resultat obtenu.

- Priorisation intelligente selon montant, anciennete, probabilite d'encaissement et risque de litige.


## 10. 10. Domaine marketing / CRM actif

- Exploitation de la base client pour campagnes de renouvellement lunettes, changement d'equipement, reactivation, relance devis, commandes pretes, impayes, satisfaction et cross-sell.

- Segmentation par age, date dernier equipement, reste a charge, panier, mutuelle, comportement d'ouverture, score client et consentement.

- Automatisation email/SMS, AB testing, modele de templates, calendrier de campagne, tableau de performance.


## 11. 11. Domaine IA et copilotes

- Assistant documentaire sur les fonctionnalites et APIs de Cosium a partir de la base de connaissances locale.

- Assistant dossier: resume, anomalies, prochaines actions, demandes de pieces, preparation PEC, synthese avant appel client.

- Assistant financier: prediction de date d'encaissement, detection de comportements de paiement, recommandations de relance et explication des ecarts.


## 12. 12. Exigences non fonctionnelles

- Traçabilite fine, audit, role-based access control, historique des modifications, logs metier lisibles.

- Architecture de donnees robuste, APIs stables, modules independants, jobs asynchrones, reprise sur incident, observabilite.

- Design front-end haut de gamme, faible charge cognitive, actions prioritaires visibles, navigation orientee workflow.


## 13. 13. Cas d'usage prioritaires MVP

- Creer un dossier client et verifier sa completude documentaire.

- Afficher la vue financiere d'un dossier avec tout ce qui est facture, recu, attendu et en retard.

- Importer un releve bancaire et rapprocher les paiements entrants.

- Suivre l'etat des PEC et les retards par mutuelle.

- Lancer une campagne de relance ciblant les devis signes non encore soldes ou les clients a renouveler.


## 14. 14. Cas d'usage V2/V3

- Portail de depot documentaire client, pre-remplissage, OCR, extraction de donnees, scoring d'anomalies.

- Previsions de cash, benchmarks mutuelles, recommandations commerciales personnalisees.

- Assistants de conversation internes relies a la documentation produit et aux procedures operatoires.

