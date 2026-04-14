# TODO MASTER — OptiFlow AI : Le Cosium Copilot

> **Vision** : Transformer OptiFlow en **copilote intelligent** pour opticiens, branche sur Cosium en temps reel.
> Ce document consolide les 5 TODOs precedentes (V1-V5) + les nouvelles capacites decouvertes dans le DOC API.
> **Perimetre** : Optique uniquement (pas d'audio/audiologie).
> **Derniere mise a jour** : 2026-04-14

---

## LEGENDE

- `[ ]` = A faire
- `[x]` = Fait (herite des TODOs V1-V5)
- `[!]` = BLOQUANT pour la production
- `[NEW]` = Nouveau, issu de l'analyse DOC API
- Priorite : P0 (critique) > P1 (haute) > P2 (moyenne) > P3 (nice-to-have)

---

# PHASE 0 — FONDATIONS & DETTE CRITIQUE
> Corriger tout ce qui bloque le deploiement production.
> Herite de TODO V1-V5, items non coches.

## 0.1 Deploiement & Infrastructure (P0) [!]

- [x] **Fix deploy.sh** : `scripts/backup_db.sh` existe (retention + verif integrite), port 8000 ferme en prod via `ports: !reset []`
- [ ] **Activer TLS/HTTPS** : decommenter le bloc HTTPS dans `config/nginx/nginx.conf`, tester certbot
- [x] **Fix bootstrap prod** : `main.py` fail-fast en prod/staging si tables manquantes (`apps/api/app/main.py:294-298`)
- [x] **Celery beat heartbeat** : tache `beat_heartbeat` chaque minute ecrit dans Redis, exposee via `/api/v1/admin/health` (seuil 300s)
- [x] **Redis eviction policy** : `maxmemory-policy allkeys-lru` configure dans `docker-compose.prod.yml`
- [ ] **MinIO backup automation** : script de backup S3 vers stockage off-site
- [x] **Require ENCRYPTION_KEY** : enforce en prod/staging (`apps/api/app/core/encryption.py:13-17`)

## 0.2 Securite (P0) [!]

- [x] JWT role mismatch corrige (User.role → TenantUser.role)
- [x] Race condition signup corrigee (unique slug)
- [x] File upload magic bytes ajoutes
- [x] Rate limiting PEC/batch/import
- [x] Email header injection sanitise
- [x] float → Decimal sur toutes les tables financieres
- [x] **Fix auth fallback cookie** : `middleware.ts` utilise UNIQUEMENT `optiflow_token` httpOnly (plus de fallback). `optiflow_authenticated` reste non-httpOnly comme signal UX + `secure=True` en prod
- [x] **Session revocation (partiel)** : endpoints `GET/POST /auth/sessions[/id/revoke]` + task Celery `purge_refresh_tokens` quotidienne (3h30). Tracking par device (user_agent/IP) reporte — necessite migration.
- [x] **Redis lock fail-safe** : `acquire_lock()` retourne False si Redis down (`apps/api/app/core/redis_cache.py:94-102`)
- [x] **Masquer /docs et /openapi.json en prod** : `docs_url=None` hors dev (`apps/api/app/main.py:87`)
- [ ] **Audit OWASP Top 10** : pass complet headers, CSRF, rate-limit login

## 0.3 Contrats Frontend/Backend (P1)

- [x] **Fix admin dashboard** : schema + endpoint retournent `services` + `components`, status `healthy/degraded` (`apps/api/app/domain/schemas/admin.py:12-18`)
- [x] **Fix metrics admin** : `users` ajoute a `MetricsTotals` (`apps/api/app/domain/schemas/admin.py:21`)
- [x] **Fix Cosium admin** : `tenant` et `base_url` deja dans `erp_sync_service.get_sync_status` (`apps/api/app/services/erp_sync_service.py:171-180`)
- [x] **Creer /admin/data-quality** : route dediee wrap le composant `DataQualitySection` (`apps/web/src/app/admin/data-quality/page.tsx`)
- [ ] **Fix cosium_admin tenant-aware** : `_check_cosium_status()` accepte `tenant_id` mais `/admin/health` est public — refactor auth necessaire

## 0.4 Tests E2E Docker (P1)

- [ ] Deploy prod E2E : `docker compose -f docker-compose.prod.yml up` sans erreur
- [ ] TLS termination test : certificat valide, redirect HTTP→HTTPS
- [ ] Backup cycle complet : backup → drop → restore → verify
- [ ] Multi-tenant isolation : 2 tenants, verifier qu'aucune donnee ne fuite
- [ ] Cosium sync E2E : mock server → sync → verify data
- [ ] Celery task profiling : mesurer temps/memoire des tasks de sync
- [ ] Load test : 50 users concurrents, temps de reponse < 3s

## 0.5 Documentation & Hygiene (P2)

- [x] **Fix README.md** : aucune mention fausse de 740 tests
- [x] **Clean .gitignore** : `*.tsbuildinfo` et `celerybeat-schedule*` deja ignores et non trackes
- [ ] **ERD auto-genere** : schema de la BDD depuis les modeles SQLAlchemy
- [x] **CONTRIBUTING.md** : guide de contribution cree (`CONTRIBUTING.md`)
- [ ] **ADR pour chaque decision** : 3 ADRs existent, a completer au fil de l'eau

---

# PHASE 1 — COSIUM CORE : SYNCHRONISATION COMPLETE
> Exploiter TOUS les endpoints GET de Cosium pour avoir une copie locale riche.
> C'est le socle de tout le reste.

## 1.1 Enrichissement Client Cosium [NEW] (P0)

- [x] GET `/customers` — recherche basique (nom, email, tel)
- [x] [NEW] **Embed complet** : `GET /api/v1/cosium/customers/{cosium_id}/detail?embed=...` — endpoint live avec embeds par defaut (accounting, address, consents, optician, site, tags)
- [x] [NEW] **Cartes de fidelite** : route `GET /api/v1/cosium/customers/{id}/fidelity-cards` — lecture live
- [x] [NEW] **Parrainages** : route `GET /api/v1/cosium/customers/{id}/sponsorships` — lecture live
- [x] [NEW] **Consentements marketing** : `GET /customers/{id}/consents` -> 4 flags (email, sms, whatsapp, exclude_all). Inclus dans `cosium-live` + cards visuels dans onglet Fidelite.
- [x] [NEW] **Recherche fuzzy** : `GET /api/v1/cosium/customers/search?last_name=&first_name=&customer_number=` (loose match Cosium, gestion 502 gracieuse)
- [ ] [NEW] **Adapter enrichi** : `cosium_customer_to_optiflow()` doit mapper fidelity, sponsorship, consents, tags
- [ ] [NEW] **Migration Alembic** : tables `client_fidelity_cards`, `client_sponsorships` + champs consents sur `clients`

## 1.2 Dossiers Optiques Complets [NEW] (P0)

> C'est LE differenciateur. Recuperer le panier optique complet du client.

- [x] [NEW] **Spectacle Files** : GET `/end-consumer/spectacles-files/{id}` — connector + service + route `GET /api/v1/cosium/spectacles/{file_id}`
- [x] [NEW] **Dioptries** : GET `/end-consumer/spectacles-files/{id}/diopters` — adapter `cosium_diopter_to_optiflow`, inclus dans le dossier complet
- [x] [NEW] **Catalogue montures** : GET `/end-consumer/catalog/optical-frames` — routes `GET /api/v1/cosium/catalog/frames[/{id}]`
- [x] [NEW] **Catalogue verres** : GET `/end-consumer/catalog/optical-lenses` — routes `GET /api/v1/cosium/catalog/lenses[/{id}]`
- [x] [NEW] **Options verres** : GET `/end-consumer/catalog/optical-lenses/{id}/available-options` — route `GET /api/v1/cosium/catalog/lenses/{id}/options`
- [x] [NEW] **Selection client** : `get_spectacle_selection` integre dans `get_spectacle_file_complete`
- [x] [NEW] **Adapter** : 3 fonctions existent (`cosium_spectacle_file_to_optiflow`, `cosium_diopter_to_optiflow`, `cosium_optical_frame_to_optiflow`)
- [ ] [NEW] **Modeles SQLAlchemy** : `spectacle_files`, `prescriptions_detail` (catalogue lu en live, persistence reportee)
- [ ] [NEW] **Migration Alembic** : a creer si on choisit la persistence
- [x] [NEW] **Service** : `spectacle_service.py` — orchestrateur live (sans persistence pour l'instant)
- [x] [NEW] **Router** : `GET /api/v1/cosium/spectacles/{file_id}` + `/customer/{cosium_id}`
- [x] [NEW] **Frontend** : onglet "Equipements" enrichi avec section "Dossiers lunettes Cosium en cours" (live)

## 1.3 Facturation & Paiements Enrichis [NEW] (P1)

- [x] GET `/invoices` — factures basiques
- [x] GET `/invoiced-items` — lignes de facture
- [x] [NEW] **Paiements facture** : `GET /api/v1/cosium/invoice-payments/{payment_id}` (live) — connector + endpoint avec gestion 502 gracieuse
- [ ] [NEW] **Liens de paiement** : GET `/invoices/{id}/payment-links` — liens de paiement en ligne si disponibles
- [ ] [NEW] **16 types de documents** : exploiter tous les types (INVOICE, QUOTE, CREDIT_NOTE, DELIVERY_NOTE, SHIPPING_FORM, ORDER_FORM, VALUED_NOTE, RETURN_VOUCHER, SUPPLIER_ORDER_FORM, SUPPLIER_DELIVERY_NOTE, SUPPLIER_INVOICE, SUPPLIER_CREDIT_NOTE, SUPPLIER_VALUED_NOTE, SUPPLIER_RETURN_VOUCHER, STOCK_MOVE, STOCK_MANUAL_UPDATE)
- [x] [NEW] **Filtres avances** : `archived`, `has_outstanding`, `min_amount`, `max_amount` ajoutes a `/cosium/factures-cosium` (settled deja existant). Validé : 208 factures > 100€ avec encours.
- [ ] [NEW] **Adapter enrichi** : mapper les 16 types + montants detailles (`shareSocialSecurity`, `sharePrivateInsurance`, `outstandingBalance`)
- [x] [NEW] **Vue comptable** : page `/analytics-cosium` (sidebar Cosium > Analyse financiere) — table ventilee par type avec count/TI/SS/AMC/RAC/encours. Endpoint `GET /api/v1/analytics/financial-breakdown[?date_from=&date_to=]`. Live : 6 types Cosium, INVOICE 3.25M€.

## 1.4 SAV / Apres-Vente [NEW] (P1)

> Module entierement nouveau. Permet de suivre les reparations et garanties.

- [x] [NEW] **Liste SAV** : GET `/after-sales-services` — route `GET /api/v1/cosium/sav` avec filtres (status, resolution, date, site)
- [x] [NEW] **Detail SAV** : GET `/after-sales-services/{id}` — route `GET /api/v1/cosium/sav/{id}`
- [x] [NEW] **Workflow statuts** : mappes TO_REPAIR/IN_PROCESS/REPAIR_IN_PROCESS/FINISHED + RESOLVED/SOLD_OUT
- [x] [NEW] **Adapter** : `cosium_after_sales_to_optiflow()` — 17 champs metier extraits
- [ ] [NEW] **Modele** : `after_sales_services` (id, customer_id, status, site_id, repairer, created_at, resolved_at)
- [ ] [NEW] **Migration Alembic** : table `after_sales_services`
- [ ] [NEW] **Service** : `after_sales_service.py`
- [ ] [NEW] **Router** : `GET /api/v1/cosium/sav` + `GET /api/v1/cosium/sav/{id}`
- [x] [NEW] **Frontend SAV** : page `/sav` dans sidebar Cosium + filtre statut + DataTable (statut, client, produit, reparateur, site)
- [ ] [NEW] **KPI dashboard** : nombre de SAV en cours, delai moyen de resolution, taux de cloture

## 1.5 Calendrier & Rendez-vous [NEW] (P1)

- [x] [NEW] **Evenements** : GET `/calendar-events` enrichi — filtres ISO 8601 `from_start_date`/`to_start_date` + `customer_number` + `site_name`
- [x] [NEW] **Categories** : GET `/cosium/calendar-event-categories` — depuis cache local
- [x] [NEW] **Detail evenement** : GET `/cosium/calendar-events/{id}`
- [ ] [NEW] **Recurrence** : mapper les patterns de recurrence (frequence, jour, heure)
- [x] [NEW] **Adapter enrichi** : `adapt_calendar_event()` existant + filtres date dans router
- [ ] [NEW] **Sync incrementale** : ne recuperer que les events modifies depuis le dernier sync
- [ ] [NEW] **Frontend** : vue calendrier (semaine/mois) avec evenements colores par categorie
- [x] [NEW] **Widget dashboard** : `GET /cosium/calendar-events/upcoming?limit=N` — endpoint pret pour le widget

## 1.6 Notes CRM [NEW] (P2)

- [x] [NEW] **Liste notes** : route `GET /api/v1/cosium/notes/{note_id}` — detail note
- [x] [NEW] **Notes par client** : `GET /api/v1/cosium/notes/customer/{cosium_id}` — historique CRM
- [x] [NEW] **Statuts notes** : `GET /api/v1/cosium/notes/statuses`
- [x] [NEW] **Adapter** : `cosium_note_to_optiflow()` — message, dates, customer, appearance, status
- [ ] [NEW] **Modele** : `cosium_notes` (id, customer_id, content, status, appearance, created_at)
- [ ] [NEW] **Migration Alembic** : table `cosium_notes`
- [ ] [NEW] **Frontend** : integration dans la timeline client (onglet "Activite")

## 1.7 Operations Commerciales [NEW] (P2)

- [x] [NEW] **Avantages** : routes `GET /api/v1/cosium/commercial-operations/{id}/advantages[/adv_id]`
- [~] [NEW] **Bons d'achat** : Cosium n'expose `/vouchers` qu'en PUT — INTERDIT par charte read-only
- [~] [NEW] **Paniers** : Cosium n'expose `/carts` qu'en PUT/DELETE — INTERDIT par charte read-only
- [x] [NEW] **Adapter** : `cosium_advantage_to_optiflow()` — name, dates, links HAL
- [ ] [NEW] **Modele** : `commercial_operations`, `vouchers`
- [ ] [NEW] **Frontend** : section "Avantages actifs" dans la fiche client + alertes dans la file d'actions

## 1.8 Sites & Multi-magasins [NEW] (P2)

- [x] GET `/sites` basique — adapter `adapt_site()` existant
- [ ] [NEW] **Filtres enrichis** : type (optique), code comptable, pagination
- [ ] [NEW] **Stock par site** : GET `/products/{id}/stocks-by-site` — inventaire multi-site
- [ ] [NEW] **Vue multi-magasins** : dashboard comparatif entre sites (CA, clients, SAV, stock)

---

# PHASE 2 — INTELLIGENCE METIER
> Transformer les donnees brutes en insights actionnables pour l'opticien.

## 2.1 File d'Actions Intelligente (P0)

- [x] Action items basiques
- [x] [NEW] **Alertes renouvellement** : `_generate_renewal_opportunities` (clients dernier achat 2-5 ans, max 100, priorise par CA). Type `renouvellement` integre dans dashboard widget + page Actions. Validé live : 100 alertes generees.
- [ ] [NEW] **Alertes SAV** : SAV en attente depuis > X jours
- [x] [NEW] **Alertes RDV** : type `rdv_demain` (testé : 11 alertes generees) — `_generate_upcoming_appointments`
- [ ] [NEW] **Alertes bons d'achat** : bons expirant dans < 30 jours
- [x] [NEW] **Alertes devis non transformes** : type `devis_dormant` > 15j (testé : 100 alertes) — `_generate_stale_quotes`
- [x] [NEW] **Alertes impaye** : type `impaye_cosium` > 30j (testé : 169 alertes) — `_generate_overdue_cosium_invoices`
- [x] [NEW] **Priorisation auto** : impaye > 90j = high, sinon medium ; devis = medium ; RDV = medium
- [x] [NEW] **Widget sidebar** : badge rouge sur item "Actions" avec compteur SWR auto-refresh 60s (99+ si > 99)

## 2.2 Dashboard Cockpit Opticien (P0)

- [x] 6 KPIs basiques
- [x] [NEW] **KPI Cosium live** : CA jour/semaine/mois via `/api/v1/dashboard/cosium-cockpit` (testé, données réelles 4771€)
- [x] [NEW] **KPI Panier moyen** : `panier_moyen` dans cockpit (CA mois / nb factures = 477€)
- [x] [NEW] **KPI Taux de transformation** : `quote_to_invoice_rate` 90 derniers jours (testé : 79.5%)
- [ ] [NEW] **KPI Delai PEC** : temps moyen de reponse mutuelles
- [ ] [NEW] **KPI SAV** : nombre en cours, delai moyen, taux satisfaction
- [ ] [NEW] **KPI Renouvellements** : clients eligibles ce mois vs contactes vs convertis
- [ ] [NEW] **KPI Stock** : alertes rupture (stock < seuil) via `latent-sales` vs `stock`
- [x] [NEW] **Graphique CA comparatif** : `ca_this_month`/`ca_last_month`/`ca_same_month_last_year` dans cockpit
- [ ] [NEW] **Graphique mix produits** : repartition montures/verres/lentilles/accessoires
- [x] [NEW] **Frontend cockpit dashboard** : `CosiumCockpitKPIs` integre dans `/dashboard` — 8 KPIs (CA jour/sem/mois, panier, taux, balance agee, comparatif M-1/N-1) avec auto-refresh 60s
- [x] [NEW] **Graphique balance agee** : 4 tranches (0-30j, 30-60j, 60-90j, 90j+) dans cockpit (15694€ total)

## 2.3 Fiche Client 360° Ultime (P1)

- [x] Fiche client basique avec onglets
- [x] [NEW] **Onglet Equipements** : section "Dossiers lunettes Cosium en cours" (live `/cosium/spectacles/customer/{id}`) + cache historique. Badges Dioptries/Selection/Prescripteur. Degradation gracieuse si Cosium KO.
- [ ] [NEW] **Onglet Prescriptions** : evolution des dioptries dans le temps (graphique Recharts)
- [x] [NEW] **Backend Fidelite** : `GET /clients/{id}/cosium-live` retourne fidelity_cards + sponsorships + notes en LIVE
- [x] [NEW] **Frontend Onglet Fidelite** : `TabFidelite` cree, integre dans fiche client (cartes + parrainages + notes CRM, gestion erreurs gracieuse)
- [ ] [NEW] **Onglet RDV** : historique et prochains rendez-vous depuis le calendrier Cosium (frontend)
- [ ] [NEW] **Onglet SAV** : dossiers SAV avec statut et timeline (frontend)
- [x] [NEW] **Backend Notes** : inclus dans `cosium-live` (live Cosium, gestion erreur gracieuse)
- [x] [NEW] **Score client** : `GET /api/v1/clients/{id}/score` (0-100, 6 composantes : CA, freq, anciennete, mutuelle, outstanding, renouvelable). Categorie VIP/Fidele/Standard/Nouveau. Affiche en haut TabResume avec breakdown visuel. Validé live : KRYS YOHAN = 67/Fidele.
- [ ] [NEW] **Alerte proactive** : bandeau en haut de la fiche si action requise (renouvellement, impaye, SAV en attente)

## 2.4 Analyse Financiere Avancee (P1)

- [x] Rapprochement bancaire basique
- [ ] [NEW] **Ventilation par tiers** : part Secu (`shareSocialSecurity`) vs mutuelle (`sharePrivateInsurance`) vs reste a charge
- [ ] [NEW] **Analyse par type document** : INVOICE vs QUOTE vs CREDIT_NOTE — taux de credit notes (indicateur qualite)
- [ ] [NEW] **Acomptes** : suivi des factures `hasAdvancePayment=true` — encaisse vs restant
- [x] [NEW] **Ventes latentes** : KPI `latent_quotes_count` + `latent_quotes_amount` (devis 90j non transformes) integre dans cockpit + carte dashboard couleur warning. Live : 39 devis = 655€ potentiel.
- [ ] [NEW] **Export FEC enrichi** : inclure les donnees Cosium dans l'export comptable
- [x] [NEW] **Previsionnel tresorerie** : `GET /api/v1/analytics/cashflow-forecast` + widget dashboard 3 cards (encours total / encaissable 30j / risque irrecouvrable). Heuristique aging-based (70/40/20/5%). Live : 15694€ -> 7155€ encaissable, 5380€ risque.

## 2.5 Gestion de Stock Intelligente [NEW] (P2)

- [ ] [NEW] **Vue stock global** : GET `/products/{id}/stock` pour tous les produits actifs
- [ ] [NEW] **Stock par site** : GET `/products/{id}/stocks-by-site` pour les groupes multi-magasins
- [ ] [NEW] **Alertes rupture** : stock < seuil configurable par famille produit
- [ ] [NEW] **Ventes latentes** : GET `/products/{id}/latent-sales` — produits reserves dans des devis
- [ ] [NEW] **Stock disponible reel** : stock physique - ventes latentes = dispo reel
- [x] [NEW] **Catalogue montures** : page `/catalogue` (onglet Montures) — grille cards (marque, modele, couleur, materiau, style, dimensions, prix)
- [x] [NEW] **Catalogue verres** : page `/catalogue` (onglet Verres) — grille cards (marque, modele, materiau, indice, traitement, teinte, photochromique)
- [ ] [NEW] **Frontend** : page "Stock" dans la sidebar avec vue grille/liste, filtres, export

---

# PHASE 3 — COPILOTE IA
> L'intelligence artificielle au service de l'opticien.

## 3.1 Assistant IA Contextuel (P1)

- [x] Service IA basique (`ai_service.py`)
- [ ] [NEW] **Contexte client enrichi** : l'IA connait les equipements, prescriptions, SAV, fidelite du client
- [ ] [NEW] **Suggestion renouvellement** : "Ce client a un equipement de 3 ans, myopie en progression (-0.50 en 2 ans), proposer un bilan"
- [ ] [NEW] **Suggestion upsell** : "Ce client a des verres basiques, les verres progressifs avec traitement anti-lumiere bleue seraient adaptes vu son addition de +2.00"
- [ ] [NEW] **Resume RDV** : avant un RDV, l'IA prepare un brief du client (dernier achat, prescription, PEC en cours, notes)
- [ ] [NEW] **Analyse devis** : l'IA verifie la coherence d'un devis (prescription vs verres choisis, prix vs catalogue)
- [ ] [NEW] **Chatbot opticien** : interface chat pour poser des questions ("combien de SAV ce mois ?", "quel CA verres progressifs ?")

## 3.2 IA Renouvellement Proactif (P1)

- [x] Renewal engine basique
- [ ] [NEW] **Scoring renouvellement** : combiner anciennete equipement + evolution dioptries + date derniere visite + age client
- [ ] [NEW] **Segmentation automatique** : classer les clients en cohortes (urgent, bientot, pas encore)
- [ ] [NEW] **Templates messages** : email/SMS personnalises avec nom + type d'equipement + duree depuis dernier achat
- [ ] [NEW] **Timing optimal** : l'IA determine le meilleur moment pour contacter (basee sur historique reponses)
- [ ] [NEW] **A/B testing** : tester differents messages et mesurer le taux de conversion

## 3.3 IA Aide au Devis (P2)

- [ ] [NEW] **Simulation remboursement** : a partir des dioptries + mutuelle client → estimer le reste a charge
- [ ] [NEW] **Recommandation produit** : en fonction de la prescription, proposer les montures/verres adaptes du catalogue
- [ ] [NEW] **Comparaison devis** : si plusieurs devis pour un client, comparer les options et montants
- [ ] [NEW] **Detection anomalie** : alerter si un devis semble anormal (prix trop bas/haut pour la prescription)

## 3.4 IA Analyse Business (P2)

- [ ] [NEW] **Rapport hebdo automatique** : resume IA du CA, tendances, alertes de la semaine
- [ ] [NEW] **Detection tendances** : evolution du mix produit, panier moyen, frequentation
- [ ] [NEW] **Benchmark** : comparer les KPIs entre magasins (pour les groupes multi-sites)
- [ ] [NEW] **Prevision CA** : modele predictif base sur l'historique et la saisonnalite

---

# PHASE 4 — EXPERIENCE UTILISATEUR PREMIUM
> Chaque ecran doit inspirer confiance et maitrise immediate.

## 4.1 Composants UI Manquants (P1)

- [x] Sidebar, Header, PageLayout, DataTable, Badge, KPICard basiques
- [ ] **CalendarView.tsx** : vue calendrier semaine/mois (events Cosium)
- [ ] **PrescriptionCard.tsx** : affichage visuel des dioptries OD/OG avec evolution
- [ ] **EquipmentTimeline.tsx** : frise chronologique des equipements optiques
- [ ] **StockGauge.tsx** : jauge visuelle du niveau de stock (vert/orange/rouge)
- [ ] **ClientScoreRadar.tsx** : graphique radar du score client (fidelite, CA, frequence, anciennete)
- [ ] **QuoteComparison.tsx** : tableau comparatif de devis cote a cote
- [ ] **SAVTracker.tsx** : suivi visuel du workflow SAV (stepper horizontal)
- [ ] **VoucherCard.tsx** : carte bon d'achat avec code, montant, date expiration
- [ ] **RenewalBanner.tsx** : bandeau d'alerte renouvellement dans la fiche client

## 4.2 Pages Nouvelles (P1)

- [ ] [NEW] **Page Stock** : `/stock` — catalogue produits, niveaux de stock, alertes rupture
- [ ] [NEW] **Page SAV** : `/sav` — liste SAV avec filtres, detail, KPIs
- [ ] [NEW] **Page Calendrier** : `/calendrier` — vue RDV semaine/mois
- [ ] [NEW] **Page Analyse Cosium** : `/analytics/cosium` — ventilation financiere complete
- [ ] [NEW] **Page Catalogue Optique** : `/catalogue` — montures + verres Cosium
- [ ] [NEW] **Page Admin Data Quality** : `/admin/data-quality` — qualite des donnees synchronisees

## 4.3 UX Polish (P2)

- [ ] **WCAG AA complet** : audit accessibilite, contrastes, navigation clavier
- [ ] **Raccourcis clavier** : Ctrl+K recherche, Ctrl+N nouveau dossier, Ctrl+S sauvegarder
- [ ] **Mode sombre** : theme dark pour les opticiens qui travaillent tard
- [ ] **Onboarding guide** : tutoriel interactif au premier login
- [ ] **Recherche globale enrichie** : rechercher dans clients + factures + devis + SAV + produits
- [ ] **Notifications push** : SSE pour les alertes en temps reel (nouveau SAV, paiement recu, sync termine)
- [ ] **Performance** : React.lazy sur toutes les pages lourdes, skeleton loaders partout

---

# PHASE 5 — MARKETING & CRM AVANCE
> Transformer les donnees en actions commerciales.

## 5.1 Marketing Enrichi [NEW] (P2)

- [x] Marketing service basique + campagnes
- [x] [NEW] **Segments dynamiques** : `GET /api/v1/analytics/dynamic-segments` + widget `DynamicSegmentsPanel` page Marketing (5 segments live : VIP, renouvellement, inactifs >3a, impayes, avec mutuelle). Validé : 20 VIP/450k€, 620 renouvellements, 198 inactifs, 147 impayes, 778 mutuelles.
- [ ] [NEW] **Exploitation bons d'achat** : afficher les vouchers actifs + alerter sur les expirations proches
- [ ] [NEW] **Campagne renouvellement** : workflow automatise (segment → template → envoi → suivi conversion)
- [ ] [NEW] **Historique interactions** : fusionner notes Cosium + emails envoyes + appels + SMS dans une timeline unique
- [ ] [NEW] **ROI par campagne** : mesurer le CA genere par campagne (clients contactes → factures emises)

## 5.2 Fidelisation [NEW] (P2)

- [ ] [NEW] **Dashboard fidelite** : points cumules, parrainages actifs, bons disponibles (depuis Cosium)
- [ ] [NEW] **Alertes parrainage** : notifier quand un parrainage est utilise
- [x] [NEW] **Top clients** : `GET /dashboard/top-clients?limit=N&months=N` + widget `TopClientsCa` dashboard avec barre de progression CA + nb factures + outstanding flag (lien fiche client)

---

# PHASE 6 — MULTI-TENANT & SCALE
> Supporter 50+ magasins d'un meme groupe.

## 6.1 Multi-tenant Robuste (P1)

- [x] Architecture multi-tenant basique (tenant_id, RLS)
- [ ] **Credentials Cosium par tenant** : verifier que chaque tenant a ses propres credentials chiffres
- [ ] **Sync isolee par tenant** : une task Celery par tenant, pas de contamination cross-tenant
- [ ] **Admin groupe** : dashboard agrege (`/admin/group-dashboard`) pour le directeur de groupe
- [ ] **Switch tenant** : `/auth/switch-tenant` fonctionnel avec nouveau JWT
- [ ] [NEW] **Comparatif inter-magasins** : KPIs cote a cote (CA, panier moyen, taux transformation, SAV)
- [ ] [NEW] **Stock inter-magasins** : vue consolidee des stocks avec transfert suggere (magasin A en surplus → B en rupture)

## 6.2 Performance a l'Echelle (P2)

- [ ] **Sync incrementale** : ne synchroniser que les donnees modifiees depuis le dernier sync (delta)
- [ ] **Cache Redis intelligent** : cacher les donnees de reference (produits, sites, payment-types) avec TTL adapte
- [ ] **Pagination serveur** : toutes les listes > 25 items paginées cote serveur
- [ ] **Connection pooling** : optimiser le pool PostgreSQL pour 50 tenants concurrents
- [ ] **Rate limiting Cosium** : respecter les limites de l'API Cosium, backoff exponentiel

---

# PHASE 7 — OBSERVABILITE & MONITORING
> Savoir ce qui se passe en production a tout moment.

## 7.1 Monitoring (P2)

- [x] **Prometheus metrics** : `/api/v1/metrics` enrichi (tenants, users, customers, cosium_invoices, outstanding_balance_eur, action_items_pending + breakdown par type label)
- [ ] **Grafana dashboards** : dashboard ops (infra) + dashboard metier (CA, clients, sync)
- [ ] **Sentry integration** : capture erreurs frontend + backend avec contexte utilisateur
- [ ] **Alerting** : Slack/email si sync echoue, si latence > 5s, si erreur rate > 5%
- [ ] **Health checks** : separer liveness (`/health/live`) de readiness (`/health/ready`)
- [ ] **Logs structures** : JSON logs avec correlation ID par requete

## 7.2 Audit & Conformite (P2)

- [ ] **Audit trail complet** : chaque consultation de donnee sensible logguee
- [ ] **RGPD** : droit a l'oubli, export donnees, consentements traces
- [ ] **Retention policy** : purge automatique des logs > 12 mois, des donnees anonymisees > 36 mois

---

# PHASE 8 — NICE-TO-HAVE / VISION LONG TERME
> Fonctionnalites differenciantes pour la V2+.

## 8.1 Portail Client (P3)

- [ ] **Espace client web** : le client voit ses devis, factures, RDV, prescription
- [ ] **Prise de RDV en ligne** : formulaire lie au calendrier Cosium (lecture seule cote Cosium)
- [ ] **Suivi SAV** : le client suit l'avancement de sa reparation
- [ ] **Signature electronique** : signature devis en ligne (eSignature)

## 8.2 Integrations Externes (P3)

- [ ] **QR Code** : generation QR pour chaque dossier/devis (scan en magasin)
- [ ] **SMS via API** : envoi SMS de rappel RDV / relance impaye
- [ ] **Comptabilite** : export vers logiciel comptable (Sage, Cegid, QuickBooks)
- [ ] **Carte vitale** : lecture carte vitale pour pre-remplir les infos Secu (hardware dependant)

## 8.3 Mobile (P3)

- [ ] **PWA responsive** : version mobile legere pour consultation en magasin (tablette)
- [ ] **Scan produit** : scanner EAN depuis le mobile pour voir le stock et les infos produit

---

# RESUME EXECUTIF

| Phase | Items | Priorite | Estimation |
|-------|-------|----------|------------|
| **Phase 0** — Fondations & dette | ~35 | P0-P2 | 80h |
| **Phase 1** — Cosium Core sync | ~65 | P0-P2 | 150h |
| **Phase 2** — Intelligence metier | ~45 | P0-P2 | 120h |
| **Phase 3** — Copilote IA | ~20 | P1-P2 | 80h |
| **Phase 4** — UX Premium | ~25 | P1-P2 | 60h |
| **Phase 5** — Marketing & CRM | ~12 | P2 | 40h |
| **Phase 6** — Multi-tenant & scale | ~12 | P1-P2 | 50h |
| **Phase 7** — Observabilite | ~10 | P2 | 40h |
| **Phase 8** — Nice-to-have | ~10 | P3 | 60h |
| **TOTAL** | **~234 items** | | **~680h** |

> **Strategie recommandee** : Phase 0 → Phase 1.1 + 1.2 (optique) → Phase 2.1 + 2.2 (dashboard) → le reste par priorite.
> L'objectif est d'avoir un **Cosium Copilot fonctionnel** avec les dossiers optiques et le dashboard intelligent en premier.

---

*Ce document remplace TODO.md, TODO_V2.md, TODO_V3.md, TODO_V4.md et TODO_V5.md.*
*Les anciennes TODOs sont conservees comme archive de ce qui a ete fait.*
