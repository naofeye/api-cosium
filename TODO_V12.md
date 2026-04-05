# TODO V12 — OptiFlow AI : Le TOP du TOP

> **Etat** : 11 commits, 306 tests backend, 100 tests frontend, 126 endpoints.
> 3710 clients Cosium reels importes. Connexion operationnelle.
> Cette V12 est LA TODO qui fait passer le projet de "prototype connecte" a "produit SaaS livrable".
>
> Organisee en 7 axes strategiques, du plus critique au plus cosmetique.

---

## AXE 1 : INTEGRATION COSIUM COMPLETE (Priorite ABSOLUE)

> On a les clients. Il manque les factures, les produits, les clients restants, et la sync incrementale.
> C'est LE differentiteur du produit — sans les donnees Cosium, OptiFlow n'a pas de valeur.

### 1.1 Sync factures Cosium → OptiFlow [ ]
- [ ] Explorer la structure facture Cosium : `invoiceNumber`, `totalTI`, `outstandingBalance`, `customerName`, `sharePrivateInsurance`, `shareSocialSecurity`, `type` (INVOICE/QUOTE/CREDIT_NOTE)
- [ ] Mapper vers le modele `Facture` OptiFlow (ou creer un modele `CosiumInvoice` dedie)
- [ ] Adapter `cosium_connector.get_invoices()` pour utiliser la pagination par filtres (comme les clients)
- [ ] Creer un lien client↔facture via `customerName` matching ou `included_customer_ids`
- [ ] Endpoint `POST /api/v1/sync/invoices` fonctionnel avec donnees reelles
- [ ] Afficher les factures Cosium dans la vue 360 client

### 1.2 Sync produits Cosium → OptiFlow [ ]
- [ ] Adapter `cosium_connector.get_products()` pour la pagination reelle
- [ ] Stocker dans une table `cosium_products` (catalogue de reference)
- [ ] Afficher dans une page `/produits` avec recherche par nom, code EAN
- [ ] Pre-remplir les lignes de devis depuis le catalogue Cosium

### 1.3 Recuperer les 1283 clients manquants [ ]
- [ ] Ajouter des filtres supplementaires : chiffres (0-9), caracteres speciaux, accents
- [ ] Filtrer par `text` (recherche full-text) avec des patterns differents
- [ ] Filtrer par `id` range si le parametre est supporte
- [ ] Objectif : > 95% des 4993 clients importes

### 1.4 Sync incrementale (delta) [ ]
- [ ] Stocker `last_sync_at` par tenant dans la BDD
- [ ] Utiliser les filtres Cosium de date (`modification_date_from_included` vu dans l'API root)
- [ ] Ne fetcher que les clients modifies depuis le dernier sync
- [ ] Reduire le temps de sync de 45s a < 5s pour les syncs quotidiennes

### 1.5 Gestion du cookie access_token [ ]
- [ ] Le cookie `access_token` a une duree de vie limitee (verifier combien de temps)
- [ ] Ajouter un mecanisme de re-auth automatique quand le cookie expire
- [ ] Option 1 : utiliser le `device-credential` (longue duree) + OIDC pour regenerer l'access_token
- [ ] Option 2 : detecter le 401 et notifier l'admin de mettre a jour le cookie
- [ ] Documenter la procedure de renouvellement pour l'opticien

### 1.6 Vue 360 enrichie avec Cosium [ ]
- [ ] Afficher les factures Cosium dans l'onglet Finances de la vue 360
- [ ] Afficher l'historique d'achat (montant total, nombre de factures, derniere visite)
- [ ] Calculer l'eligibilite au renouvellement basee sur les vraies dates d'achat
- [ ] Afficher les produits achetes (montures, verres) dans un onglet "Equipements"

---

## AXE 2 : COUVERTURE DE TESTS (306 → 500+)

> 306 tests backend mais les tests sont sur les ENDPOINTS, pas sur les SERVICES individuels.
> 29 services sans test unitaire dedie. 12 composants frontend sans test.
> L'objectif n'est pas 100% couverture — c'est de tester ce qui peut CASSER.

### 2.1 Tests services critiques (les 10 plus importants) [ ]
- [ ] `test_devis_service.py` : calculs montants, workflow statut, transitions invalides
- [ ] `test_facture_service.py` : generation depuis devis, numerotation, montants
- [ ] `test_pec_service.py` : workflow PEC, validation montant_accorde <= demande
- [ ] `test_banking_service.py` : import CSV, reconciliation auto, match manuel
- [ ] `test_auth_service.py` : login, refresh, change password, forgot password, switch tenant
- [ ] `test_client_service.py` : CRUD, soft-delete, restore, import CSV, doublons
- [ ] `test_marketing_service.py` : segments, campagnes, consentements, envoi
- [ ] `test_analytics_service.py` : KPIs financiers, balance agee, taux conversion
- [ ] `test_reminder_service.py` : plans, execution, envoi, stats
- [ ] `test_event_service.py` : emission events, notifications creees

### 2.2 Tests composants frontend manquants [ ]
- [ ] `tests/components/KPICard.test.tsx` : rendu, couleurs, valeur
- [ ] `tests/components/FileUpload.test.tsx` : rendu, drag-drop, click
- [ ] `tests/components/Toast.test.tsx` : affichage, auto-dismiss, variantes
- [ ] `tests/components/LoadingState.test.tsx` : skeleton rendu
- [ ] `tests/components/ErrorState.test.tsx` : message, bouton retry
- [ ] `tests/components/Header.test.tsx` : dark mode toggle, notifications, logout
- [ ] `tests/components/Sidebar.test.tsx` : navigation, collapse, active state

### 2.3 Tests E2E avec donnees Cosium reelles [ ]
- [ ] Scenario : login → recherche client Cosium → vue 360 → factures reelles
- [ ] Scenario : sync → dashboard → KPIs refletent les vrais montants
- [ ] Scenario : creer devis pour client Cosium → calculs corrects

---

## AXE 3 : OPTIMISATION PERFORMANCE

> La sync prend 45s pour 3710 clients. Le dashboard peut etre lent avec 25000 factures.

### 3.1 Optimiser la sync Cosium [ ]
- [ ] Paralleliser les requetes par lettre (A-Z en parallele avec asyncio ou ThreadPool)
- [ ] Utiliser `embed_address=true&embed_tags=true` pour eviter les sous-requetes
- [ ] Batch insert au lieu de `db.add()` un par un
- [ ] Objectif : sync complete < 15 secondes

### 3.2 Optimiser le dashboard avec les vraies donnees [ ]
- [ ] Les KPIs doivent agreger 25000+ factures — verifier les temps de requete
- [ ] Ajouter des indexes sur les colonnes filtrees (date, statut, montant)
- [ ] Pre-calculer les KPIs dans une table `kpi_cache` rafraichie toutes les 5 minutes
- [ ] Redis cache avec TTL adapte au volume de donnees

### 3.3 Frontend : lazy loading et virtualisation [ ]
- [ ] Les listes de 3710 clients sont paginées (OK) mais le select "client" dans les formulaires charge tout
- [ ] Utiliser un composant `AsyncSelect` avec recherche serveur pour les selects de clients
- [ ] Virtualiser les listes longues avec `react-window` si necessaire

---

## AXE 4 : FONCTIONNALITES MANQUANTES POUR L'USAGE QUOTIDIEN

> Ce que l'opticien va demander des le premier jour d'utilisation.

### 4.1 Impressions et exports [ ]
- [ ] PDF facture avec les vrais en-tetes du magasin (logo, adresse, SIRET)
- [ ] Export comptable FEC (Fichier des Ecritures Comptables) — obligatoire en France
- [ ] Export balance clients (qui doit quoi)
- [ ] Impression etiquettes produits (depuis le catalogue Cosium)

### 4.2 Recherche avancee [ ]
- [ ] Recherche par numero de securite sociale
- [ ] Recherche par numero de facture Cosium
- [ ] Recherche par plage de dates (clients crees entre X et Y)
- [ ] Filtres combines (ville + mutuelle + derniere visite)

### 4.3 Tableau de bord personnalisable [ ]
- [ ] Widgets deplacables (drag-and-drop les KPI cards)
- [ ] Choix des KPIs affiches (chaque opticien veut voir des choses differentes)
- [ ] Comparaison periode N vs N-1 (ce mois vs meme mois l'an dernier)
- [ ] Export du dashboard en PDF

### 4.4 Agenda et rendez-vous [ ]
- [ ] Cosium a un endpoint `calendar-events` (vu dans l'API root)
- [ ] Syncer les rendez-vous dans OptiFlow
- [ ] Afficher un calendrier visuel (FullCalendar ou similaire)
- [ ] Lier les rendez-vous aux clients et dossiers

### 4.5 Notes et commentaires sur les clients [ ]
- [ ] Cosium a un endpoint `notes-on-customer` (vu dans l'API root)
- [ ] Syncer les notes dans OptiFlow
- [ ] Permettre d'ajouter des notes depuis OptiFlow (stockees localement)

---

## AXE 5 : FIABILISATION FRONTEND

### 5.1 Migrer les 4 derniers setLoading vers SWR [ ]
- [ ] Identifier les 4 pages restantes avec `setLoading`
- [ ] Migrer vers SWR (meme pattern que les autres)

### 5.2 Formulaires sans RHF restants [ ]
- [ ] `forgot-password/page.tsx` → useForm + Zod
- [ ] `reset-password/page.tsx` → useForm + Zod
- [ ] `marketing/components/SegmentPanel.tsx` → useForm
- [ ] `marketing/components/CampaignPanel.tsx` → useForm

### 5.3 Fichiers > 250 lignes [ ]
- [ ] Identifier les 10 fichiers frontend > 250 lignes
- [ ] Extraire les sections repetitives en composants
- [ ] Objectif : 0 fichier > 300 lignes

### 5.4 Accessibilite WCAG [ ]
- [ ] Audit couleurs de contraste (WCAG AA)
- [ ] Navigation clavier complete (Tab, Enter, Escape sur tous les composants)
- [ ] Lecteur d'ecran : `aria-label` sur tous les boutons icone
- [ ] Skip-to-content link
- [ ] Focus visible sur tous les elements interactifs

---

## AXE 6 : SECURITE ET PRODUCTION

### 6.1 Monitoring production [ ]
- [ ] Sentry backend : valider qu'il capture les erreurs (trigger une erreur test)
- [ ] Sentry frontend : integrer @sentry/nextjs (deja installe, verifier que ca fonctionne)
- [ ] Uptime monitoring : configurer UptimeRobot (gratuit) sur `/health`
- [ ] Alertes email sur erreurs critiques

### 6.2 Preparation deploiement VPS [ ]
- [ ] Commande VPS (Ubuntu 22.04, 4 vCPU, 8 GB RAM, 50 GB SSD)
- [ ] DNS : configurer le domaine (A record → IP VPS)
- [ ] SSL : activer HTTPS via certbot (nginx est pret)
- [ ] Cron : backup quotidien a 3h du matin
- [ ] Cron : certbot renew mensuel
- [ ] `.env.production` avec vrais secrets (JWT, Fernet, MinIO, Stripe)
- [ ] Premier deploiement : `./scripts/deploy.sh`
- [ ] Smoke test en prod : login → dashboard → recherche → PDF

### 6.3 Gestion des cookies Cosium en production [ ]
- [ ] Le cookie `access_token` expire — il faut un mecanisme de renouvellement
- [ ] Page admin : champ pour mettre a jour les cookies Cosium manuellement
- [ ] Alerte quand le cookie expire (test de connexion periodique)
- [ ] Documentation pour l'opticien : "Comment renouveler l'acces Cosium"

---

## AXE 7 : POLISH ET DIFFERENCIATION

> Ce qui fait dire "wow" a un prospect en demo.

### 7.1 IA Copilote avec donnees reelles [ ]
- [ ] Configurer l'API key Anthropic dans `.env`
- [ ] Le copilote dossier resume les donnees Cosium du client (factures, montants, dates)
- [ ] Le copilote financier analyse les impayees et recommande des relances
- [ ] Le copilote renouvellement detecte les clients eligibles avec les vraies dates d'achat Cosium

### 7.2 Emails transactionnels professionnels [ ]
- [ ] Email de bienvenue apres inscription (template welcome.html)
- [ ] Email de confirmation apres creation de devis
- [ ] Email de rappel de paiement (template relance.html)
- [ ] Configurer un vrai SMTP en production (SendGrid, Mailjet, ou OVH)

### 7.3 Mobile responsive [ ]
- [ ] Tester toutes les pages a 375px de large (iPhone)
- [ ] Sidebar collapsible en overlay sur mobile
- [ ] Tableaux scrollables horizontalement
- [ ] Formulaires en full-width sur mobile
- [ ] Boutons d'action en bas d'ecran (sticky)

### 7.4 Onboarding in-app [ ]
- [ ] Tour guide pour les nouveaux utilisateurs (highlight les sections cles)
- [ ] Tooltips contextuels "Saviez-vous que..."
- [ ] Video de presentation integree dans la page d'aide

### 7.5 Multi-langue (preparation) [ ]
- [ ] Extraire toutes les strings hardcodees dans des fichiers de traduction
- [ ] Installer `next-intl` ou `react-i18next`
- [ ] Francais par defaut, anglais en option
- [ ] Le backend retourne les messages d'erreur dans la langue du user

---

## RECAPITULATIF PAR PRIORITE

### SEMAINE 1 — COSIUM COMPLET (Axe 1)
| # | Tache | Effort |
|---|-------|--------|
| 1.1 | Sync factures Cosium | 2h |
| 1.2 | Sync produits Cosium | 1h |
| 1.3 | Clients manquants (1283) | 1h |
| 1.4 | Sync incrementale | 2h |
| 1.6 | Vue 360 enrichie Cosium | 2h |

### SEMAINE 2 — TESTS & PERF (Axes 2-3)
| # | Tache | Effort |
|---|-------|--------|
| 2.1 | 10 tests services critiques | 3h |
| 2.2 | 7 tests composants | 1h |
| 3.1 | Optimiser sync (parallelisme) | 2h |
| 3.2 | Dashboard perf | 1h |

### SEMAINE 3 — FEATURES METIER (Axe 4)
| # | Tache | Effort |
|---|-------|--------|
| 4.1 | Exports comptables (FEC, balance) | 3h |
| 4.2 | Recherche avancee | 2h |
| 4.4 | Agenda (sync calendar-events) | 3h |
| 4.5 | Notes clients | 1h |

### SEMAINE 4 — DEPLOIEMENT (Axe 6)
| # | Tache | Effort |
|---|-------|--------|
| 6.1 | Monitoring Sentry | 1h |
| 6.2 | Deploiement VPS | 3h |
| 6.3 | Gestion cookies Cosium | 2h |

### EN CONTINU — POLISH (Axes 5, 7)
| # | Tache | Effort |
|---|-------|--------|
| 5.1-5.3 | Frontend cleanup | 2h |
| 5.4 | Accessibilite WCAG | 2h |
| 7.1 | IA Copilote avec donnees reelles | 2h |
| 7.2 | Emails pro | 1h |
| 7.3 | Mobile responsive | 3h |

---

## METRIQUES CIBLES FIN V12

| Metrique | Actuel | Cible |
|----------|--------|-------|
| Clients Cosium importes | 3 710 | **4 750+** (95%) |
| Factures Cosium | 0 | **25 000+** |
| Produits Cosium | 0 | **5 000+** (echantillon) |
| Tests backend | 306 | **450+** |
| Tests frontend | 100 | **130+** |
| Temps sync clients | 45s | **< 15s** |
| Couverture backend | ~85% | **> 90%** |
| Deploiement prod | Non | **Oui (VPS)** |
