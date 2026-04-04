# Script de Demo OptiFlow AI

## Preparation

1. Demarrer l'environnement : `docker compose up --build -d`
2. Seeder les donnees de demo :
   - Login : `admin@optiflow.local` / `admin123`
   - Appeler `POST /api/v1/sync/seed-demo` via Swagger ou la page Admin
3. Verifier : http://localhost:3000

## Scenario de demo (10 minutes)

### 1. Dashboard (2 min)
- Ouvrir http://localhost:3000/dashboard
- Montrer les **KPIs financiers** : CA total, encaisse, reste a encaisser, taux de recouvrement
- Montrer la **courbe CA** sur 6 mois
- Montrer la **balance agee** : creances par tranche et par payeur
- Montrer les **KPIs operationnels** : dossiers, completude, conversion devis

### 2. Vue client 360 (2 min)
- Aller dans **Clients** → cliquer sur un client
- Montrer les **6 onglets** : Resume, Dossiers, Finances, Documents, Marketing, Historique
- Montrer le **resume financier** en haut (4 KPIs)
- Onglet **Finances** : montrer devis → facture → paiement
- Onglet **Historique** : montrer les interactions, ajouter une note en live

### 3. Workflow dossier complet (3 min)
- **Nouveau dossier** : Clients → Nouveau dossier → remplir le formulaire
- **Devis** : Devis → Nouveau → ajouter 3 lignes (monture + verres + traitement)
  - Montrer le **calcul automatique** HT/TVA/TTC et le reste a charge
- **Signer** le devis : bouton "Envoyer" puis "Signer"
- **Facturer** : bouton "Generer la facture" → facture creee avec numero sequentiel
- **Paiement** : Paiements → enregistrer le paiement

### 4. PEC et relances (1.5 min)
- **PEC** : montrer le tableau de bord PEC avec les KPIs par statut
- **Relances** : montrer la balance agee, la liste priorisee des impayees
- Montrer les **plans de relance** configurables

### 5. Copilote IA (1 min)
- Ouvrir un dossier → onglet **Assistant IA**
- Selectionner "Copilote Dossier" → demander "Resume ce dossier"
- Selectionner "Copilote Documentaire" → demander "Comment gerer les stocks dans Cosium ?"

### 6. Administration (0.5 min)
- Page **Admin** : montrer la sante du systeme (vert partout)
- Montrer les metriques : nombre de clients, dossiers, factures
- Montrer la synchronisation Cosium (boutons sync)

## Points cles a souligner
- **Vue 360** : tout le client en 1 clic
- **Automatisation** : calculs devis, generation facture, relances
- **RGPD** : export/anonymisation des donnees
- **IA** : copilote contextuel pour chaque dossier
- **Cosium** : synchronisation lecture seule, securisee
