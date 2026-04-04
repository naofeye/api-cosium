# Base de Connaissances Cosium
> Generee le 2026-04-03 | Sources: PDFs API, captures d'ecran, analyse application

---

## 1. Architecture Generale

### Application
- **Nom**: CosiumOptic (logiciel de gestion pour opticiens)
- **Type**: Application web SPA (Angular 20 + AngularJS legacy)
- **UI Framework**: Taiga UI v4.69.0
- **Hebergement**: Cloud Cosium (`c1.cosium.biz`)
- **Auth**: Keycloak/OpenID Connect via `id.neox-it.org`
- **Code site exemple**: `01CONE06488`
- **Moteur FSE**: v2.28.01 (Feuille de Soins Electronique)

### URLs de base
- **Application**: `https://c1.cosium.biz/{siteCode}/classic/`
- **API REST**: `https://c1.cosium.biz/{siteCode}/api/`
- **Documentation**: `https://doc.cosium.com/bin/view/Center/` (wiki XWiki)
- **Fichiers publics**: `https://public.cosium.com/`

---

## 2. API REST Cosium

### 2.1 Authentification

**Endpoint**: `POST /{siteCode}/api/authenticate/basic`

```json
{
  "login": "username",
  "password": "password",
  "site": "site-name"
}
```

**Reponse**: Token dans le header `access_token`

**Utilisation du token** (3 methodes):
- Header: `Authorization: AccessToken {token}`
- Cookie: `access_token={token}`
- Parametre URL: `?access_token={token}`

**Note**: L'application utilise aussi OAuth2/OIDC via Keycloak (`id.neox-it.org`)

### 2.2 Conventions API

- **Format**: JSON, avec support HAL (`Accept: application/hal+json`)
- **Pagination**: `page_number` (defaut 0), `page_size` (defaut 50-100, max 500)
- **CORS**: Desactive par defaut (activation sur demande a Cosium)
- **Verbes HTTP**: GET, POST, PUT, PATCH, DELETE (standard REST)

### 2.3 Codes HTTP
| Code | Signification |
|------|--------------|
| 200  | Succes |
| 201  | Ressource creee |
| 204  | Mise a jour reussie |
| 400  | Requete malformee / trop de resultats |
| 401  | Non authentifie |
| 403  | Interdit (privileges insuffisants) |
| 404  | Ressource introuvable |

---

## 3. Endpoints API Documentes

### 3.1 Customer API (`/api/customers`)

#### Lister les clients
```
GET /{siteCode}/api/customers
```
**Parametres de recherche:**
| Parametre | Description |
|-----------|-------------|
| `lastName` | Nom de famille |
| `firstName` | Prenom |
| `email` | Adresse email |
| `birthDate` | Date de naissance |
| `customerNumber` | ID Cosium du client |
| `mobilePhoneNumber` | Numero de telephone mobile |
| `mobilePhoneCounty` | Pays du telephone (defaut: FRANCE) |

**Reponse** (champs par client):
- `id`, `lastName`, `firstName`, `birthDate`, `email`
- `customerNumber`, `mobilePhone`, `siteId`, `socialSecurityNumber`
- Liens: `self`, `address`, `contact`, `documents`, `document-types`

**Note**: Si trop de resultats, erreur 400 (preciser les parametres)

#### Gestion des abonnements marketing
| Action | Methode | Endpoint |
|--------|---------|----------|
| Inscrire email | PUT | `/api/customers/subscribed-to-email` |
| Desinscrire email | PUT | `/api/customers/unsubscribed-from-email` |
| Inscrire courrier | PUT | `/api/customers/subscribed-to-paper` |
| Desinscrire courrier | PUT | `/api/customers/unsubscribed-from-paper` |
| Inscrire SMS | PUT | `/api/customers/subscribed-to-sms` |
| Desinscrire SMS | PUT | `/api/customers/unsubscribed-from-sms` |

**Body**: `{ "id": <customerId> }`
**Reponse**: `204 No Content`

---

### 3.2 Invoice API (`/api/invoices`)

#### Lister les factures
```
GET /{siteCode}/api/invoices
```
**Parametres:**
| Parametre | Description |
|-----------|-------------|
| `types` | Types: INVOICE, QUOTE, CREDIT_NOTE, DELIVERY_NOTE, SHIPPING_FORM, ORDER_FORM, VALUED_NOTE, RETURN_VOUCHER, SUPPLIER_ORDER_FORM, SUPPLIER_DELIVERY_NOTE, SUPPLIER_INVOICE, SUPPLIER_CREDIT_NOTE, SUPPLIER_VALUED_NOTE, SUPPLIER_RETURN_VOUCHER, STOCK_MOVE, STOCK_MANUAL_UPDATE |
| `invoiceDateFrom` | Date debut (incluse). Format: `yyyy-MM-dd'T'HH:mm:ss.SSSZ` |
| `invoiceDateTo` | Date fin (exclue) |
| `siteId` | ID du site |
| `archived` | Factures archivees uniquement |
| `hasAdvancePayment` | Avec acomptes uniquement |
| `settled` | Factures reglees uniquement |
| `invoiceNumber` | Numero de facture |
| `validationQuoteDateIsPresent` | Devis avec date de validation |
| `pageSize` | Taille page (max 500, defaut 100) |
| `pageNumber` | Numero de page (defaut 0) |

**Reponse** (champs par facture):
- `id`, `type`, `invoiceNumber`, `invoiceDate`, `customerName`, `siteId`
- `outstandingBalance` (solde restant du)
- `totalTI` (total TTC)
- `shareSocialSecurity` (part securite sociale)
- `sharePrivateInsurance` (part mutuelle)

---

### 3.3 Invoiced Items API (`/api/invoiced-items`)

#### Lister les lignes de facture
```
GET /{siteCode}/api/invoiced-items
```
**Parametres:**
| Parametre | Description |
|-----------|-------------|
| `invoiceId` | Filtrer par ID facture |
| `pageSize` | Max 500, defaut 100 |
| `pageNumber` | Defaut 0 |

**Reponse** (champs par ligne):
- `id`, `label`, `quantity`, `invoiceId`, `rank`
- `productId`, `productCode`
- `vatPercentage` (% TVA)
- `unitPriceIncludingTaxes`, `unitPriceExcludingTaxes`
- `totalPriceIncludingTaxes`
- `discount`, `discountType` (PERCENTAGE ou CURRENCY)

---

### 3.4 Products API (`/api/products`)

#### Rechercher des produits
```
GET /{siteCode}/api/products
```
**Parametres:**
| Parametre | Description |
|-----------|-------------|
| `ean_code` | Code EAN ou UPC |
| `gtin_code` | Code GTIN |
| `code` | Code produit |
| `family_type` | Famille (ex: OPT_FRAME) |
| `page_size` | Taille page (defaut 10) |

**Reponse** (format HAL):
- `productCode`, `barcode`, `gtinCode`, `familyType`
- `label`, `eanCode`, `stopProductionDate`
- Liens: `self`, `stock`, `latent-sales`

#### Stock d'un produit
```
GET /{siteCode}/api/products/{id}/stock?siteId={siteId}
```
**Reponse**: `{ "quantity": 13 }`

#### Ventes latentes
```
GET /{siteCode}/api/products/{id}/latent-sales?quotations_max_age_in_days=10
```
Quantite de produit dans des devis non transformes en factures.
**Reponse**: `{ "quantity": 3 }`

---

### 3.5 Payment Type API (`/api/payment-types`)

```
GET /{siteCode}/api/payment-types
```
**Note**: Documentation incomplete dans le PDF (snippets manquants)

---

### 3.6 Endpoints supplementaires decouverts (API root)

| Endpoint | Description |
|----------|-------------|
| `/api/application` | Infos application |
| `/api/application-oidc-client-id` | Client ID OIDC |
| `/api/authentication-challenges` | Challenges d'auth |
| `/api/users/current/cleared-sites` | Sites accessibles par l'utilisateur |
| `/api/device-credentials` | Credentials d'appareil |
| `/api/help-chat/configuration` | Config du chat d'aide |
| `/api/oidc-ui-activation-status` | Statut activation OIDC |
| `/api/oidc/ui/configuration` | Config OIDC |
| `/api/configurations/public` | Configuration publique |
| `/api/reseller` | Info revendeur |
| `/api/webstart/configuration` | Config Webstart |

---

## 4. Modules de l'application CosiumOptic

### 4.1 General
- **Gestion clients**: Fiche client, courrier, rendez-vous, devis/factures
- **Recherche clients**: Par nom, recherche avancee, derniere recherche
- **Agenda**: Calendrier et recherche de rendez-vous
- **Alertes**: Systeme d'alertes

### 4.2 Caisse / Comptabilite
- **Factures**: Creation facture, creation devis, en cours
- **Teletransmission**: Consultation, retours NOEMIE (RSP), virements RSP, actions/stats/parametrage SV140
- **Comptabilite**: Journaux, operations diverses
- **Recherche**: Factures, articles factures, reglements, remises en banque
- **Caisse**: Operations de caisse, livre de caisse

### 4.3 Stock / SAV
- **Recherche**: Produit, article, mouvements de stock
- **Produits**: Ouvrir produit courant, liste produits, liste articles
- **Inventaire**: Module, fiche stock, fiche d'ecart, inventaire, historique
- **SAV**: Recherche, ouvrir, nouveau SAV
- **Creation produit**

### 4.4 Marketing
- **Achats**: Bons de commande, bons de livraison, factures fournisseur
- **Mailing**: Modeles, champs de fusion, creation courrier/email/SMS, listes mailings
- **Jobs**: Dashboard fournisseur, changement d'etat, recherche
- **Statistiques**: Objectifs site/employe

### 4.5 Parametres
- Utilisateurs, impressions, scanner
- Signature electronique
- Configuration Carte Vitale, lecture CPS/CPE
- Appairage module SV140 distant

---

## 5. Gestion des dossiers clients (optique)

### Structure d'un dossier (d'apres les captures d'ecran)

#### Fiche patient
- Nom, prenom, date de naissance
- Adresse, telephone, email
- N° Securite Sociale
- Caisse Secu (ex: CPAM Evry)
- Taux remboursement (ex: 60%)
- Complementaire sante (mutuelle)
- N° client Cosium (ex: 100004808)

#### Dossier Lunettes
- Corrections OD/OG (sphere, cylindre, axe)
- Ecart pupillaire, hauteur
- Type de verre (VL, VP, PROG)
- Monture (reference, fournisseur)
- Verres (reference, fournisseur, traitements)

#### Documents associes
Types de documents geres:
- Ordonnance lunettes
- Ordonnances lentilles
- Fiche OPTICIEN
- Devis
- Fiche OPHTALMO
- Consentement RGPD
- Attestation SECU
- Carte Mutuelle

#### Processus devis
- Devis normalise en optique medicale (conforme reglementation)
- Equipement classe A (100% Sante / RAC 0) et classe B
- Simulation remboursement mutuelle (ex: via Oxantis)
- Part Securite Sociale, part mutuelle, reste a charge

---

## 6. Documentation Cosium (wiki XWiki)

### Structure
- **URL**: `https://doc.cosium.com`
- **Plateforme**: XWiki 15.10.12
- **Langue**: Francais (principal), + Portugais, Italien, Polonais, Chinois, Espagnol, Anglais

### Sections principales
| Section | URL |
|---------|-----|
| Documentation Utilisateur | `/bin/view/Center/` |
| Documentation Administrateur | `/bin/view/CenterAdmin/` |
| Liste de tous les documents | `/bin/view/Main/AllDocs` |
| Macros | `/bin/view/Macros/` |
| Applications | `/bin/view/Applications/` |
| Aide | `/bin/view/Help/` |

### Acces
- Via l'application Cosium: Menu Aide > Documentation
- Redirection: `/jsp/doc_redirect.jsp`
- Authentification separee (XWiki) - identifiants differents de l'application

### Documentation Utilisateur (`/bin/view/Center/`)

| Section | URL | Description |
|---------|-----|-------------|
| Support Materiel (infogérance) | `/bin/view/Center/workstation-configuration/` | Configuration postes de travail |
| Support Logiciel Cosium | `/bin/view/Center/software-support/` | Support logiciel CosiumOptic |
| Formation en video | `/bin/view/Center/user-video-tutorials/` | Tutoriels video utilisateurs |

### Documentation Administrateur (`/bin/view/CenterAdmin/`)

| Section | URL | Description |
|---------|-----|-------------|
| Presentation generale des parametrages | `/bin/view/CenterAdmin/general-configuration/` | Config generale du logiciel |
| Caisse / Compta | `/bin/view/CenterAdmin/till-accounts/` | Parametrage caisse et comptabilite |
| Produits | `/bin/view/CenterAdmin/product/` | Configuration catalogue produits |
| Stock | `/bin/view/CenterAdmin/Stocks/` | Gestion et parametrage des stocks |
| Fiche client | `/bin/view/CenterAdmin/client-file/` | Configuration fiche client |
| Dossier Optique (Offre commerciale) | `/bin/view/CenterAdmin/lens-file-configuration/` | Parametrage dossier optique |
| Sante / TPP / Mutuelles / RAC 0 | `/bin/view/CenterAdmin/health-tpp/` | Tiers payant, mutuelles, conventionnement, prescripteurs |
| Centres / Societes / Entites | `/bin/view/CenterAdmin/centres-societies-entities/` | Gestion centres et entites juridiques |
| Materiel / Logiciel | `/bin/view/CenterAdmin/software/` | Config materiel et integrations |
| Utilisateurs et droits | `/bin/view/CenterAdmin/user-configuration/` | Gestion utilisateurs, roles, droits |
| Formation en video | `/bin/view/CenterAdmin/admin-video-tutorials/` | Tutoriels video administrateurs |

---

## 7. Integrations tierces identifiees

| Partenaire | Fonction |
|------------|----------|
| **Oxantis** | Simulation remboursement mutuelle |
| **NOEMIE/SV140** | Teletransmission Securite Sociale |
| **Carte Vitale** | Lecture carte patient |
| **CPS/CPE** | Authentification professionnel de sante |
| **Essilor** | Fournisseur verres (visible dans captures) |
| **Neox IT** | Fournisseur identite/SSO (Keycloak) |

---

## 8. Informations techniques pour integration

### Pour se connecter a l'API
1. Obtenir un token via `POST /{siteCode}/api/authenticate/basic`
2. Passer le token dans chaque requete via header `Authorization: AccessToken {token}`
3. Utiliser `Accept: application/hal+json` pour le format HAL avec liens hypermedia
4. Pagination: `page_number=0&page_size=50`

### Base URL
```
https://c1.cosium.biz/{siteCode}/api/
```
Ou `{siteCode}` est le code du centre (ex: `01CONE06488`, `01ACJA05562`)

### Flux typique d'integration
1. Authentification → obtenir token
2. Recherche client → `GET /api/customers?lastName=...`
3. Details client → suivre le lien `self` du client
4. Factures client → `GET /api/invoices?...`
5. Lignes de facture → `GET /api/invoiced-items?invoiceId=...`
6. Produits → `GET /api/products?ean_code=...`
7. Stock → `GET /api/products/{id}/stock`
