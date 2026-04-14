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
- [ ] [NEW] **Embed complet** : exploiter `?embed=accounting,address,consents,optician,site,tags` pour rapatrier toutes les sous-ressources en un seul appel
- [ ] [NEW] **Cartes de fidelite** : GET `/customers/{id}/fidelity-cards` — sync vers table `client_fidelity_cards`
- [ ] [NEW] **Parrainages** : GET `/customers/{id}/sponsorships` — sync vers table `client_sponsorships`
- [ ] [NEW] **Consentements marketing** : lire les flags `subscribed-to-email/sms/paper` depuis Cosium et les afficher dans OptiFlow (lecture seule)
- [ ] [NEW] **Recherche fuzzy** : exploiter `loose_first_name`, `loose_last_name`, `loose_customer_number` pour la recherche globale
- [ ] [NEW] **Adapter enrichi** : `cosium_customer_to_optiflow()` doit mapper fidelity, sponsorship, consents, tags
- [ ] [NEW] **Migration Alembic** : tables `client_fidelity_cards`, `client_sponsorships` + champs consents sur `clients`

## 1.2 Dossiers Optiques Complets [NEW] (P0)

> C'est LE differenciateur. Recuperer le panier optique complet du client.

- [ ] [NEW] **Spectacle Files** : GET `/end-consumer/spectacles-files/{id}` — dossier lunettes complet
- [ ] [NEW] **Dioptries** : GET `/end-consumer/spectacles-files/{id}/diopters` — sphere, cylindre, axe, addition, prisme
- [ ] [NEW] **Catalogue montures** : GET `/end-consumer/catalog/optical-frames` — avec filtres (marque, type, materiau)
- [ ] [NEW] **Catalogue verres** : GET `/end-consumer/catalog/optical-lenses` — avec options (traitement, teinte, photochromique)
- [ ] [NEW] **Options verres** : GET `/end-consumer/catalog/optical-lenses/{id}/options` — options disponibles par verre
- [ ] [NEW] **Selection client** : GET `/end-consumer/spectacles-files/{id}/selection` — choix en cours du client
- [ ] [NEW] **Adapter** : `cosium_spectacle_to_optiflow()`, `cosium_diopter_to_optiflow()`, `cosium_frame_to_optiflow()`
- [ ] [NEW] **Modeles SQLAlchemy** : `spectacle_files`, `prescriptions_detail`, `optical_frames`, `optical_lenses`
- [ ] [NEW] **Migration Alembic** : 4 nouvelles tables optiques
- [ ] [NEW] **Service** : `spectacle_service.py` — logique de recuperation et mise en cache des dossiers optiques
- [ ] [NEW] **Router** : `GET /api/v1/cosium/spectacles/{customer_id}` — expose les dossiers optiques au frontend
- [ ] [NEW] **Frontend** : onglet "Equipements optiques" dans la fiche client avec historique des montures/verres

## 1.3 Facturation & Paiements Enrichis [NEW] (P1)

- [x] GET `/invoices` — factures basiques
- [x] GET `/invoiced-items` — lignes de facture
- [ ] [NEW] **Paiements facture** : GET `/invoice-payments/{id}` — detail des reglements par facture
- [ ] [NEW] **Liens de paiement** : GET `/invoices/{id}/payment-links` — liens de paiement en ligne si disponibles
- [ ] [NEW] **16 types de documents** : exploiter tous les types (INVOICE, QUOTE, CREDIT_NOTE, DELIVERY_NOTE, SHIPPING_FORM, ORDER_FORM, VALUED_NOTE, RETURN_VOUCHER, SUPPLIER_ORDER_FORM, SUPPLIER_DELIVERY_NOTE, SUPPLIER_INVOICE, SUPPLIER_CREDIT_NOTE, SUPPLIER_VALUED_NOTE, SUPPLIER_RETURN_VOUCHER, STOCK_MOVE, STOCK_MANUAL_UPDATE)
- [ ] [NEW] **Filtres avances** : `hasAdvancePayment`, `settled`, `validationQuoteDateIsPresent`, `archived`
- [ ] [NEW] **Adapter enrichi** : mapper les 16 types + montants detailles (`shareSocialSecurity`, `sharePrivateInsurance`, `outstandingBalance`)
- [ ] [NEW] **Vue comptable** : page "Analyse financiere Cosium" avec ventilation par type de document

## 1.4 SAV / Apres-Vente [NEW] (P1)

> Module entierement nouveau. Permet de suivre les reparations et garanties.

- [ ] [NEW] **Liste SAV** : GET `/after-sales-services` — recherche avec filtres (statut, date, site, reparateur)
- [ ] [NEW] **Detail SAV** : GET `/after-sales-services/{id}` — detail complet du dossier
- [ ] [NEW] **Workflow statuts** : pending → processing → resolved → finished (lecture seule)
- [ ] [NEW] **Adapter** : `cosium_after_sales_to_optiflow()`
- [ ] [NEW] **Modele** : `after_sales_services` (id, customer_id, status, site_id, repairer, created_at, resolved_at)
- [ ] [NEW] **Migration Alembic** : table `after_sales_services`
- [ ] [NEW] **Service** : `after_sales_service.py`
- [ ] [NEW] **Router** : `GET /api/v1/cosium/sav` + `GET /api/v1/cosium/sav/{id}`
- [ ] [NEW] **Frontend** : page "SAV" dans la sidebar + onglet SAV dans la fiche client
- [ ] [NEW] **KPI dashboard** : nombre de SAV en cours, delai moyen de resolution, taux de cloture

## 1.5 Calendrier & Rendez-vous [NEW] (P1)

- [ ] [NEW] **Evenements** : GET `/calendar-events` — avec filtres date ISO 8601 (`from_start_date`, `to_end_date`)
- [ ] [NEW] **Categories** : GET `/calendar-event-categories` — types de RDV (examen, livraison, ajustement...)
- [ ] [NEW] **Detail evenement** : GET `/calendar-events/{id}` — avec client lie
- [ ] [NEW] **Recurrence** : mapper les patterns de recurrence (frequence, jour, heure)
- [ ] [NEW] **Adapter enrichi** : `adapt_calendar_event()` existe mais doit gerer recurrence + filtres date
- [ ] [NEW] **Sync incrementale** : ne recuperer que les events modifies depuis le dernier sync
- [ ] [NEW] **Frontend** : vue calendrier (semaine/mois) avec evenements colores par categorie
- [ ] [NEW] **Widget dashboard** : "Prochains RDV" avec nom client + type + heure

## 1.6 Notes CRM [NEW] (P2)

- [ ] [NEW] **Liste notes** : GET `/notes` — notes avec statuts et apparences
- [ ] [NEW] **Notes par client** : GET `/notes?customerId={id}` — historique CRM du client
- [ ] [NEW] **Statuts notes** : GET `/notes/statuses` — reference des statuts possibles
- [ ] [NEW] **Adapter** : `cosium_note_to_optiflow()`
- [ ] [NEW] **Modele** : `cosium_notes` (id, customer_id, content, status, appearance, created_at)
- [ ] [NEW] **Migration Alembic** : table `cosium_notes`
- [ ] [NEW] **Frontend** : integration dans la timeline client (onglet "Activite")

## 1.7 Operations Commerciales [NEW] (P2)

- [ ] [NEW] **Avantages** : GET `/commercial-operations/{id}/advantages` — promotions actives
- [ ] [NEW] **Bons d'achat** : GET `/commercial-operations/{id}/vouchers` — bons utilisables par client
- [ ] [NEW] **Paniers** : GET `/commercial-operations/{id}/carts` — paniers en cours
- [ ] [NEW] **Adapter** : `cosium_commercial_op_to_optiflow()`
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
- [ ] [NEW] **Alertes renouvellement** : detecter les clients dont l'equipement a > 2 ans (via spectacle files + date facture)
- [ ] [NEW] **Alertes SAV** : SAV en attente depuis > X jours
- [ ] [NEW] **Alertes RDV** : clients avec RDV demain (rappel automatique)
- [ ] [NEW] **Alertes bons d'achat** : bons expirant dans < 30 jours
- [ ] [NEW] **Alertes devis non transformes** : devis envoyes depuis > 15 jours sans signature
- [ ] [NEW] **Alertes impaye** : factures avec `outstandingBalance > 0` et date > 30 jours
- [ ] [NEW] **Priorisation IA** : classer les actions par urgence et impact financier
- [ ] [NEW] **Widget sidebar** : compteur d'actions par categorie (badge rouge)

## 2.2 Dashboard Cockpit Opticien (P0)

- [x] 6 KPIs basiques
- [ ] [NEW] **KPI Cosium live** : CA du jour/semaine/mois (depuis invoices Cosium)
- [ ] [NEW] **KPI Panier moyen** : montant moyen par facture optique
- [ ] [NEW] **KPI Taux de transformation** : devis → facture (QUOTE → INVOICE)
- [ ] [NEW] **KPI Delai PEC** : temps moyen de reponse mutuelles
- [ ] [NEW] **KPI SAV** : nombre en cours, delai moyen, taux satisfaction
- [ ] [NEW] **KPI Renouvellements** : clients eligibles ce mois vs contactes vs convertis
- [ ] [NEW] **KPI Stock** : alertes rupture (stock < seuil) via `latent-sales` vs `stock`
- [ ] [NEW] **Graphique CA comparatif** : mois actuel vs mois precedent vs annee precedente (Recharts)
- [ ] [NEW] **Graphique mix produits** : repartition montures/verres/lentilles/accessoires
- [ ] [NEW] **Graphique balance agee** : `outstandingBalance` par tranche (0-30j, 30-60j, 60-90j, 90j+)

## 2.3 Fiche Client 360° Ultime (P1)

- [x] Fiche client basique avec onglets
- [ ] [NEW] **Onglet Equipements** : historique complet des montures + verres + dioptries (timeline visuelle)
- [ ] [NEW] **Onglet Prescriptions** : evolution des dioptries dans le temps (graphique Recharts)
- [ ] [NEW] **Onglet Fidelite** : carte de fidelite, points, parrainages, bons actifs
- [ ] [NEW] **Onglet RDV** : historique et prochains rendez-vous depuis le calendrier Cosium
- [ ] [NEW] **Onglet SAV** : dossiers SAV avec statut et timeline
- [ ] [NEW] **Onglet Notes** : notes CRM Cosium integrees dans l'activite
- [ ] [NEW] **Score client** : algorithme de scoring (frequence achat, panier moyen, anciennete, PEC ok, renouvellement)
- [ ] [NEW] **Alerte proactive** : bandeau en haut de la fiche si action requise (renouvellement, impaye, SAV en attente)

## 2.4 Analyse Financiere Avancee (P1)

- [x] Rapprochement bancaire basique
- [ ] [NEW] **Ventilation par tiers** : part Secu (`shareSocialSecurity`) vs mutuelle (`sharePrivateInsurance`) vs reste a charge
- [ ] [NEW] **Analyse par type document** : INVOICE vs QUOTE vs CREDIT_NOTE — taux de credit notes (indicateur qualite)
- [ ] [NEW] **Acomptes** : suivi des factures `hasAdvancePayment=true` — encaisse vs restant
- [ ] [NEW] **Ventes latentes** : produits en devis non factures (`latent-sales`) — potentiel CA a convertir
- [ ] [NEW] **Export FEC enrichi** : inclure les donnees Cosium dans l'export comptable
- [ ] [NEW] **Previsionnel tresorerie** : basee sur les echeances PEC + paiements attendus

## 2.5 Gestion de Stock Intelligente [NEW] (P2)

- [ ] [NEW] **Vue stock global** : GET `/products/{id}/stock` pour tous les produits actifs
- [ ] [NEW] **Stock par site** : GET `/products/{id}/stocks-by-site` pour les groupes multi-magasins
- [ ] [NEW] **Alertes rupture** : stock < seuil configurable par famille produit
- [ ] [NEW] **Ventes latentes** : GET `/products/{id}/latent-sales` — produits reserves dans des devis
- [ ] [NEW] **Stock disponible reel** : stock physique - ventes latentes = dispo reel
- [ ] [NEW] **Catalogue montures** : navigation dans le catalogue Cosium avec filtres (marque, type, prix)
- [ ] [NEW] **Catalogue verres** : navigation verres avec options et traitements
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
- [ ] [NEW] **Segments dynamiques** : bases sur les donnees Cosium (dernier achat > 2 ans, progressifs, < 40 ans...)
- [ ] [NEW] **Exploitation bons d'achat** : afficher les vouchers actifs + alerter sur les expirations proches
- [ ] [NEW] **Campagne renouvellement** : workflow automatise (segment → template → envoi → suivi conversion)
- [ ] [NEW] **Historique interactions** : fusionner notes Cosium + emails envoyes + appels + SMS dans une timeline unique
- [ ] [NEW] **ROI par campagne** : mesurer le CA genere par campagne (clients contactes → factures emises)

## 5.2 Fidelisation [NEW] (P2)

- [ ] [NEW] **Dashboard fidelite** : points cumules, parrainages actifs, bons disponibles (depuis Cosium)
- [ ] [NEW] **Alertes parrainage** : notifier quand un parrainage est utilise
- [ ] [NEW] **Top clients** : classement par CA, frequence, anciennete — pour actions VIP

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

- [ ] **Prometheus metrics** : latence API, taux erreur, duree sync Cosium, taille queue Celery
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
