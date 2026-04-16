# TODO MASTER V2 — OptiFlow AI : Le Cosium Copilot

> **Vision** : Transformer OptiFlow en **copilote intelligent** de reference pour opticiens, branche sur Cosium en temps reel.
> Ce document consolide les 5 TODOs (V1-V5), les 5 rapports d'audit, et l'analyse approfondie du DOC API Cosium.
> **Perimetre** : Optique uniquement (pas d'audio/audiologie).
> **Cible** : Desktop + Mobile PWA, rendu professionnel et fluide.
> **Derniere mise a jour** : 2026-04-15

---

## LEGENDE

- `[ ]` A faire
- `[x]` Fait (herite des TODOs V1-V5)
- `[!]` BLOQUANT pour la production
- `[BUG]` Bug identifie lors de l'audit de code
- `[SEC]` Faille de securite identifiee
- `[PERF]` Probleme de performance
- `[NEW]` Nouveau item issu du DOC API ou de l'audit
- `[PWA]` Concerne la Progressive Web App
- Priorite : P0 (bloquant) > P1 (haute) > P2 (moyenne) > P3 (nice-to-have)

---

# ═══════════════════════════════════════════════
# PHASE 0 — URGENCES : BUGS, SECURITE & PRODUCTION
# ═══════════════════════════════════════════════
> Tout corriger AVANT de construire quoi que ce soit de nouveau.
> Estimation : ~80h

## 0.1 BUGS CRITIQUES BACKEND [!] (P0)

- [x] [BUG] **JWT sans verification tenant** : verif effectuee au niveau `get_current_user()` (`core/deps.py:54-65`) et `get_tenant_context()` (`core/tenant_context.py:50-60`). Les dependencies FastAPI verifient user.is_active + TenantUser.is_active. CORRIGE.
- [x] [BUG] **Password reset token rejouable** : `models/user.py:25` — champ `used` verifie (`auth_service.py:266`) et mis a jour (`auth_service.py:281`). CORRIGE.
- [x] [BUG] **Pas de rollback explicite** : rollback centralise dans `db/session.py:get_db()` (except Exception: db.rollback()). Toute exception remontant d'un service declenche un rollback avant fermeture. CORRIGE.
- [x] [BUG] **Rate limiter bloquant si Redis down** : `acquire_lock()` (`core/redis_cache.py:92-119`) et rate limiter (`core/rate_limiter.py:76,87`) ont tous deux un fallback in-memory avec warning log. CORRIGE.
- [x] [BUG] **Token blacklist inoperante sans Redis** : `security.py:is_token_blacklisted()` fail-closed en prod (retourne True + warning) et fail-open en dev/test/local. Evite que tokens revoques passent en prod. CORRIGE.
- [x] [BUG] **Commit dans boucle sync docs** : `cosium_document_sync.py:149` — commit batche par 50. CORRIGE.
- [x] [BUG] **Celery healthcheck casse** : `docker-compose.yml:99` — remplace `$$HOSTNAME` par `$$(hostname)` (command substitution fonctionne en sh/dash, pas $HOSTNAME). CORRIGE.
- [x] [BUG] **Tenant isolation manquante** : `facture_repo.py:90-110` — filtrage `tenant_id` verifie OK. Reste a auditer TOUS les autres repos.
- [x] [BUG] **Metrique merge client fausse** : `client_merge_service.py:102-115` — count des PEC est fait AVANT le transfert des cases (commentaire "bug fix" explicite). CORRIGE.

## 0.2 FAILLES DE SECURITE [!] (P0)

- [ ] [SEC] [DIFFERE-PROD] **Credentials Cosium dans .env committe** : `.env` contient login/password Cosium en clair dans le repo Git. Environnement TEST, conservation autorisee. A traiter au passage en prod uniquement (revocation compte `AFAOUSSI` + `git filter-branch`).
- [x] [SEC] **Cle de chiffrement derivee du JWT** : `core/encryption.py:13-17` — fail-fast en production/staging si ENCRYPTION_KEY absent. Fallback SHA256(JWT_SECRET) UNIQUEMENT en dev/test avec warning. CORRIGE.
- [x] [SEC] JWT role mismatch corrige (User.role → TenantUser.role)
- [x] [SEC] Race condition signup corrigee (unique slug)
- [x] [SEC] File upload magic bytes ajoutes
- [x] [SEC] Rate limiting PEC/batch/import
- [x] [SEC] Email header injection sanitise
- [x] [SEC] float → Decimal sur tables financieres
- [x] [SEC] **Auth fallback cookie non-httpOnly** : `middleware.ts:5` utilise UNIQUEMENT `optiflow_token` httpOnly pour la protection serveur. Le flag client `optiflow_authenticated` (auth.ts:19) est purement UX, pas de bypass possible (backend et middleware ignorent ce flag). CORRIGE.
- [x] [SEC] **Session revocation absente** : `refresh_token_repo.revoke_all_for_user()` appele a login (auth_service.py:112), switch-tenant (ligne 188), change-password (ligne 218), reset-password (ligne 282). Politique definie : 1 session active par user. CORRIGE.
- [x] [SEC] **CORS allow_credentials trop permissif** : `main.py:163-169` — origines parsees depuis settings.cors_origins (pas de wildcard `*`). FastAPI refuse `*` + credentials. Methodes limitees (GET/POST/PUT/DELETE/OPTIONS). Headers whitelistes. OK tant que cors_origins est explicite en prod. CORRIGE.
- [ ] [SEC] **CSP unsafe-inline** : `next.config.ts:22-23` — `script-src 'self' 'unsafe-inline' 'unsafe-eval'`. Migrer vers nonces CSP.
- [x] [SEC] **Pas de validation taille fichier** : `document_service.py:47-49` applique `settings.max_upload_size_mb * 1024 * 1024`. Validation post-lecture memoire (ameliorable via nginx `client_max_body_size` pour pre-filtrage). CORRIGE.
- [ ] [SEC] **Pas d'idempotence** : payments/banking OK (`banking_service.py:29-34` `idempotency_key`), reminder_tasks/sync_tasks OK. Manque PEC, factures, devis. PARTIEL.
- [x] [SEC] **/docs et /openapi.json exposes en prod** : `main.py:89-95` — `docs_url` et `redoc_url` = None si app_env pas dans (local, development, test). OpenAPI JSON inaccessible hors dev. CORRIGE.
- [ ] [SEC] **Audit OWASP Top 10** : pass complet headers, CSRF, rate-limit login, injection.

## 0.3 DEPLOIEMENT & INFRASTRUCTURE [!] (P0)

- [x] [BUG] **deploy.sh casse** : plus de reference a `backup_db.sh`, backup integre (ligne 37-40), tests nginx/direct OK (ligne 62,81). CORRIGE.
- [ ] [BUG] [DIFFERE-PROD] **HTTPS desactive** : bloc SSL commente dans `config/nginx/nginx.conf:122-198`. Template pret, a decommenter + configurer cert Let's Encrypt au passage en prod (domaine requis).
- [ ] [BUG] **Bootstrap unsafe** : `main.py:286-322` plus de `create_all()`, warnings seulement, seed conditionnel dev. Manque fail-fast strict en prod si schema incoherent.
- [ ] [BUG] [DIFFERE-PROD] **Passwords BDD par defaut** : `POSTGRES_PASSWORD:-optiflow` et MinIO `minioadmin:minioadmin`. OK pour env test actuel, a override obligatoirement au passage en prod.
- [ ] [BUG] **Prometheus scrape 404** : `prometheus.yml:17` pointe vers `/api/v1/metrics` qui n'existe pas.
- [ ] [BUG] [DIFFERE-PROD] **Grafana password par defaut** : `docker-compose.monitoring.yml:21` — `admin/admin`. Override par `GF_SECURITY_ADMIN_PASSWORD` au passage en prod.
- [ ] **Celery beat heartbeat** : monitoring du scheduler (alerte si beat mort > 5min)
- [x] **Redis eviction policy** : `docker-compose.yml:redis` — `--maxmemory 256mb --maxmemory-policy allkeys-lru`. CORRIGE.
- [ ] **MinIO backup automation** : script vers stockage off-site
- [x] **Require ENCRYPTION_KEY strict** en prod : `core/encryption.py:13-17` fail-fast RuntimeError si absent en production/staging. CORRIGE (doublon item 11).
- [ ] [DIFFERE-PROD] **server_name explicite** dans Nginx prod (pas `_` catch-all `nginx.conf:49`). A configurer avec le vrai domaine au passage en prod.
- [x] **client_max_body_size** : present sur `/api/` (25M, nginx.conf:85). Frontend Next.js ne recoit pas d'uploads directs (tous via /api), pas necessaire sur `/`. CORRIGE.
- [ ] **ON DELETE CASCADE** : aucun FK n'a de cascade → orphelins en BDD. Ajouter sur toutes les FK.
- [ ] **Indexes manquants** : `(tenant_id, created_at)` sur documents, `(tenant_id, status)` sur cases, `(tenant_id, date_paiement)` sur payments.
- [ ] **Soft-delete inconsistant** : `Customer` a `deleted_at`, mais `Facture`, `Devis` non. Harmoniser.

## 0.4 CONTRATS FRONTEND/BACKEND (P1)

- [ ] [BUG] **Admin dashboard casse** : frontend attend `health.services` / `"healthy"`, backend renvoie `components` / `"ok"`.
- [ ] [BUG] **metrics.totals.users absent** du backend.
- [ ] [BUG] **Cosium admin tenant-unaware** : `_check_cosium_status()` utilise credentials globaux.
- [ ] [BUG] **Page /admin/data-quality** referencee mais inexistante.
- [ ] [BUG] **README.md mensonger** : annonce 740 tests (115 reels), 53 services (96 reels).
- [x] **Clean .gitignore** : `.gitignore:52` `*.tsbuildinfo`, `.gitignore:71` `apps/api/celerybeat-schedule*`. Aucun de ces fichiers n'est tracke (verifie via git ls-files). CORRIGE.

## 0.5 TESTS & VALIDATION (P1)

- [ ] Deploy E2E : `docker compose -f docker-compose.prod.yml up` sans erreur
- [ ] TLS termination : certificat valide, redirect HTTP→HTTPS
- [ ] Backup → drop → restore → verify
- [ ] Multi-tenant isolation : 2 tenants, zero fuite
- [ ] Cosium sync E2E : mock server → sync → verify
- [ ] Celery task profiling : temps/memoire
- [ ] Load test : 50 users concurrents < 3s
- [ ] Test payment_service.py (creation, modification, rapprochement)
- [ ] Test cosium_invoice_sync.py (incremental, full)
- [ ] CI coverage threshold : passer de `--cov-fail-under=0` a `70`
- [ ] CI security scanning : retirer `|| true` sur `pip-audit`
- [ ] Alembic rollback + data integrity test

---

# ═══════════════════════════════════════════════
# PHASE 1 — PWA & RESPONSIVE : MOBILE-FIRST
# ═══════════════════════════════════════════════
> OptiFlow doit fonctionner aussi bien sur PC que sur telephone.
> Estimation : ~60h

## 1.1 Infrastructure PWA [NEW] (P0)

- [ ] [PWA] **Creer manifest.json** : nom app, icones 192x192 + 512x512, theme_color, background_color, display: "standalone", start_url: "/dashboard"
- [ ] [PWA] **Generer icones app** : favicon, apple-touch-icon, icones PWA (192, 384, 512)
- [ ] [PWA] **Installer next-pwa** (`@ducanh2912/next-pwa`) et configurer dans `next.config.ts`
- [ ] [PWA] **Service Worker** : cache des assets statiques, fallback offline, strategie stale-while-revalidate pour API
- [ ] [PWA] **Page offline** : ecran elegant quand pas de connexion ("Vous etes hors ligne. Reconnectez-vous pour continuer.")
- [ ] [PWA] **Viewport meta** : ajouter dans `layout.tsx` : `viewport: { width: "device-width", initialScale: 1, minimumScale: 1, viewportFit: "cover" }`
- [ ] [PWA] **Splash screens** : iOS splash screens pour iPad et iPhone
- [ ] [PWA] **Install prompt** : banniere native "Ajouter a l'ecran d'accueil" avec detection beforeinstallprompt
- [ ] [PWA] **Web Vitals monitoring** : integrer `next/vitals` pour mesurer LCP, FID, CLS en production

## 1.2 Layout Responsive (P0)

- [ ] [BUG] **Sidebar tablette cassee** : `AuthLayout.tsx:52` — entre 768-1023px, sidebar cachee mais `lg:ml-64` applique → contenu decale. Ajouter breakpoint `md:ml-16` pour sidebar collapsed.
- [ ] **Sidebar mobile** : hamburger menu avec overlay sombre, slide-in depuis la gauche, fermeture au clic exterieur et au swipe
- [ ] **Bottom navigation mobile** : barre de navigation fixe en bas sur mobile (5 icones : Accueil, Clients, Devis, Notifications, Plus)
- [ ] [PWA] **Safe area** : respecter `env(safe-area-inset-bottom)` pour iPhone avec encoche
- [ ] **Header responsive** : masquer la barre de recherche sur mobile, icone loupe a la place
- [ ] **PageLayout responsive** : titre + actions en colonne sur mobile, sticky footer avec `bottom: calc(64px + env(safe-area-inset-bottom))`
- [ ] **Max-width desktop** : contenu centre `max-w-[1440px]` pour ecrans ultrawide

## 1.3 Composants Responsive (P1)

- [ ] [BUG] **DataTable mobile** : `DataTable.tsx:174-209` — padding trop large, colonnes non masquees. Creer vue "cards" sur mobile au lieu du tableau.
- [ ] **Pagination mobile** : simplifier (precedent/suivant au lieu de numeros de page)
- [ ] **Formulaires mobile** : inputs pleine largeur, labels au-dessus, zones de tap 48px minimum
- [ ] [BUG] **Sticky footer formulaires** : conflit avec bottom nav mobile. Ajuster `bottom-20` sur mobile.
- [ ] **Modales mobile** : plein ecran sur mobile (sheet from bottom), modale classique sur desktop
- [ ] **KPICards mobile** : grille 2 colonnes au lieu de 4, texte reduit
- [ ] **Graphiques responsive** : `Recharts` avec `ResponsiveContainer` + taille de police adaptative
- [ ] **Boutons touch-friendly** : minimum 44px de zone de tap partout. Audit de tous les boutons icones.
- [ ] [BUG] **Collapse sidebar bouton trop petit** : `Sidebar.tsx:50-63` — `p-1.5` = ~24px. Passer a `p-3` minimum.

## 1.4 Images & Performance Mobile (P1)

- [ ] [PERF] **Remplacer `<img>` par `next/image`** : `clientsColumns.tsx`, `AvatarUpload.tsx`, `TabDocuments.tsx` — pas de lazy loading, pas de WebP.
- [ ] **Configurer `images.domains`** dans `next.config.ts` pour MinIO et sources externes.
- [ ] **Font-display swap** : eviter le flash de texte invisible.
- [ ] **React.lazy** sur toutes les pages avec graphiques (dashboard, analytics, rapprochement).
- [ ] **Prefetch** : `Link prefetch={true}` sur les items de la sidebar.
- [ ] **SWR dedup** : augmenter `dedupingInterval` de 2s a 5s pour eviter les requetes doubles.
- [ ] **Bundle analyzer** : activer `@next/bundle-analyzer` pour identifier les gros modules.

---

# ═══════════════════════════════════════════════
# PHASE 2 — COSIUM CORE : SYNCHRONISATION COMPLETE
# ═══════════════════════════════════════════════
> Exploiter TOUS les endpoints GET de Cosium pour une copie locale riche.
> Estimation : ~150h

## 2.1 Client Cosium Enrichi [NEW] (P0)

- [x] GET `/customers` — recherche basique (nom, email, tel)
- [ ] [NEW] **Embed complet** : `?embed=accounting,address,consents,optician,site,tags` en un seul appel
- [ ] [NEW] **Recherche fuzzy** : `loose_first_name`, `loose_last_name`, `loose_customer_number`
- [ ] [NEW] **Cartes fidelite** : GET `/customers/{id}/fidelity-cards` → table `client_fidelity_cards`
- [ ] [NEW] **Parrainages** : GET `/customers/{id}/sponsorships` → table `client_sponsorships`
- [ ] [NEW] **Consentements marketing** : lire flags `subscribed-to-email/sms/paper` (lecture seule)
- [ ] [NEW] **Adapter enrichi** : mapper fidelity, sponsorship, consents, tags
- [ ] [NEW] **Migration Alembic** : tables `client_fidelity_cards`, `client_sponsorships` + champs consents

## 2.2 Dossiers Optiques Complets [NEW] (P0)

> LE differenciateur. Le panier optique complet du client.

- [ ] [NEW] **Spectacle Files** : GET `/end-consumer/spectacles-files/{id}` — dossier lunettes complet
- [ ] [NEW] **Dioptries** : GET `/end-consumer/spectacles-files/{id}/diopters` — sphere, cylindre, axe, addition, prisme
- [ ] [NEW] **Catalogue montures** : GET `/end-consumer/catalog/optical-frames` — filtres marque, type, materiau
- [ ] [NEW] **Catalogue verres** : GET `/end-consumer/catalog/optical-lenses` + options (traitement, teinte)
- [ ] [NEW] **Selection client** : GET `/end-consumer/spectacles-files/{id}/selection`
- [ ] [NEW] **Adapters** : `cosium_spectacle_to_optiflow()`, `cosium_diopter_to_optiflow()`, `cosium_frame_to_optiflow()`
- [ ] [NEW] **Modeles SQLAlchemy** : `spectacle_files`, `prescriptions_detail`, `optical_frames`, `optical_lenses`
- [ ] [NEW] **Migration Alembic** : 4 nouvelles tables optiques
- [ ] [NEW] **Service** : `spectacle_service.py`
- [ ] [NEW] **Router** : `GET /api/v1/cosium/spectacles/{customer_id}`
- [ ] [NEW] **Frontend** : onglet "Equipements optiques" dans fiche client

## 2.3 Facturation & Paiements Enrichis [NEW] (P1)

- [x] GET `/invoices` + GET `/invoiced-items`
- [ ] [NEW] **Paiements facture** : GET `/invoice-payments/{id}` — detail reglements
- [ ] [NEW] **Liens paiement** : GET `/invoices/{id}/payment-links`
- [ ] [NEW] **16 types documents** : exploiter tous les types (INVOICE, QUOTE, CREDIT_NOTE, DELIVERY_NOTE, etc.)
- [ ] [NEW] **Filtres avances** : `hasAdvancePayment`, `settled`, `validationQuoteDateIsPresent`
- [ ] [NEW] **Adapter enrichi** : mapper `shareSocialSecurity`, `sharePrivateInsurance`, `outstandingBalance`

## 2.4 SAV / Apres-Vente [NEW] (P1)

- [ ] [NEW] **Liste SAV** : GET `/after-sales-services` — filtres statut, date, site, reparateur
- [ ] [NEW] **Detail SAV** : GET `/after-sales-services/{id}`
- [ ] [NEW] **Adapter** : `cosium_after_sales_to_optiflow()`
- [ ] [NEW] **Modele** : `after_sales_services`
- [ ] [NEW] **Service** : `after_sales_service.py`
- [ ] [NEW] **Router** : `GET /api/v1/cosium/sav`
- [ ] [NEW] **Frontend** : page SAV sidebar + onglet SAV fiche client + KPIs

## 2.5 Calendrier & RDV [NEW] (P1)

- [ ] [NEW] **Evenements** : GET `/calendar-events` — filtres date ISO 8601
- [ ] [NEW] **Categories** : GET `/calendar-event-categories`
- [ ] [NEW] **Recurrence** : mapper patterns de recurrence
- [ ] [NEW] **Sync incrementale** : events modifies depuis le dernier sync
- [ ] [NEW] **Frontend** : vue calendrier semaine/mois + widget "Prochains RDV" dashboard

## 2.6 Notes CRM [NEW] (P2)

- [ ] [NEW] GET `/notes` + GET `/notes?customerId={id}` + GET `/notes/statuses`
- [ ] [NEW] **Adapter** + **Modele** + **Migration** + integration timeline client

## 2.7 Operations Commerciales [NEW] (P2)

- [ ] [NEW] GET `/commercial-operations/{id}/advantages` + `/vouchers` + `/carts`
- [ ] [NEW] **Adapter** + **Modele** + section "Avantages actifs" fiche client + alertes expiration

## 2.8 Sites & Multi-magasins Enrichis [NEW] (P2)

- [x] GET `/sites` basique
- [ ] [NEW] **Stock par site** : GET `/products/{id}/stocks-by-site` — inventaire multi-site
- [ ] [NEW] **Dashboard comparatif** inter-magasins (CA, clients, SAV, stock)

---

# ═══════════════════════════════════════════════
# PHASE 3 — INTELLIGENCE METIER
# ═══════════════════════════════════════════════
> Transformer les donnees brutes en insights actionnables.
> Estimation : ~120h

## 3.1 File d'Actions Intelligente (P0)

- [x] Action items basiques
- [ ] [NEW] **Alertes renouvellement** : equipement > 2 ans (via spectacle files + date facture)
- [ ] [NEW] **Alertes SAV** : SAV en attente > X jours
- [ ] [NEW] **Alertes RDV** : clients avec RDV demain (rappel)
- [ ] [NEW] **Alertes bons d'achat** : expirant < 30 jours
- [ ] [NEW] **Alertes devis** : envoyes > 15 jours sans signature
- [ ] [NEW] **Alertes impaye** : `outstandingBalance > 0` et date > 30 jours
- [ ] [NEW] **Priorisation IA** : classer par urgence et impact financier
- [ ] [NEW] **Widget sidebar** : compteurs par categorie avec badge rouge

## 3.2 Dashboard Cockpit Opticien (P0)

- [x] 6 KPIs basiques
- [ ] [NEW] **CA live** : jour/semaine/mois depuis invoices Cosium
- [ ] [NEW] **Panier moyen** : montant moyen par facture optique
- [ ] [NEW] **Taux transformation** : devis → facture
- [ ] [NEW] **Delai PEC** : temps moyen reponse mutuelles
- [ ] [NEW] **KPI SAV** : en cours, delai moyen, satisfaction
- [ ] [NEW] **KPI Renouvellements** : eligibles vs contactes vs convertis
- [ ] [NEW] **Alertes stock** : rupture via `latent-sales` vs `stock`
- [ ] [NEW] **Graphique CA comparatif** : M/M-1/A-1 (Recharts)
- [ ] [NEW] **Graphique mix produits** : montures/verres/lentilles/accessoires
- [ ] [NEW] **Balance agee** : `outstandingBalance` par tranche (0-30j, 30-60j, 60-90j, 90j+)

## 3.3 Fiche Client 360° Ultime (P1)

- [x] Fiche client basique avec onglets
- [ ] [NEW] **Onglet Equipements** : historique montures + verres + dioptries (timeline visuelle)
- [ ] [NEW] **Onglet Prescriptions** : evolution dioptries dans le temps (graphique)
- [ ] [NEW] **Onglet Fidelite** : carte, points, parrainages, bons actifs
- [ ] [NEW] **Onglet RDV** : historique et prochains (calendrier Cosium)
- [ ] [NEW] **Onglet SAV** : dossiers avec statut et timeline
- [ ] [NEW] **Onglet Notes** : notes CRM Cosium dans l'activite
- [ ] [NEW] **Score client** : scoring (frequence, panier, anciennete, PEC, renouvellement)
- [ ] [NEW] **Alerte proactive** : bandeau si action requise

## 3.4 Analyse Financiere Avancee (P1)

- [x] Rapprochement bancaire basique
- [ ] [NEW] **Ventilation tiers** : Secu vs mutuelle vs reste a charge
- [ ] [NEW] **Analyse par type** : INVOICE vs QUOTE vs CREDIT_NOTE
- [ ] [NEW] **Acomptes** : suivi `hasAdvancePayment=true`
- [ ] [NEW] **Ventes latentes** : potentiel CA a convertir
- [ ] [NEW] **Previsionnel tresorerie** : echeances PEC + paiements attendus

## 3.5 Gestion Stock Intelligente [NEW] (P2)

- [ ] [NEW] **Stock global** + **par site** + **alertes rupture** + **ventes latentes**
- [ ] [NEW] **Stock disponible reel** : physique - latentes = dispo
- [ ] [NEW] **Catalogue navigable** : montures + verres avec filtres
- [ ] [NEW] **Frontend** : page Stock dans sidebar

---

# ═══════════════════════════════════════════════
# PHASE 4 — COPILOTE IA
# ═══════════════════════════════════════════════
> L'IA au service de l'opticien.
> Estimation : ~80h

## 4.1 Assistant IA Contextuel (P1)

- [x] Service IA basique
- [ ] [NEW] **Contexte enrichi** : equipements, prescriptions, SAV, fidelite
- [ ] [NEW] **Suggestion renouvellement** : "equipement 3 ans, myopie -0.50 en 2 ans, proposer bilan"
- [ ] [NEW] **Suggestion upsell** : "verres basiques, addition +2.00 → progressifs anti-lumiere bleue"
- [ ] [NEW] **Resume pre-RDV** : brief du client (dernier achat, prescription, PEC, notes)
- [ ] [NEW] **Analyse devis** : coherence prescription vs verres choisis
- [ ] [NEW] **Chatbot opticien** : "combien de SAV ce mois ?", "quel CA verres progressifs ?"

## 4.2 IA Renouvellement Proactif (P1)

- [x] Renewal engine basique
- [ ] [NEW] **Scoring** : anciennete equipement + evolution dioptries + derniere visite + age
- [ ] [NEW] **Segmentation auto** : cohortes (urgent, bientot, pas encore)
- [ ] [NEW] **Templates personnalises** : email/SMS avec nom + equipement + duree
- [ ] [NEW] **Timing optimal** : meilleur moment pour contacter (historique reponses)
- [ ] [NEW] **A/B testing** : messages differents → mesurer conversion

## 4.3 IA Aide au Devis (P2)

- [ ] [NEW] **Simulation remboursement** : dioptries + mutuelle → reste a charge estime
- [ ] [NEW] **Recommandation produit** : prescription → montures/verres adaptes du catalogue
- [ ] [NEW] **Comparaison devis** : options et montants cote a cote
- [ ] [NEW] **Detection anomalie** : prix anormal pour la prescription

## 4.4 IA Analyse Business (P2)

- [ ] [NEW] **Rapport hebdo auto** : resume CA, tendances, alertes
- [ ] [NEW] **Detection tendances** : evolution mix produit, panier, frequentation
- [ ] [NEW] **Benchmark inter-magasins** : KPIs compares (groupes multi-sites)
- [ ] [NEW] **Prevision CA** : modele predictif + saisonnalite

---

# ═══════════════════════════════════════════════
# PHASE 5 — UX PREMIUM & POLISH
# ═══════════════════════════════════════════════
> Chaque ecran doit inspirer confiance et maitrise immediate.
> Estimation : ~80h

## 5.1 Composants UI Manquants (P1)

- [ ] **CalendarView.tsx** : vue calendrier semaine/mois
- [ ] **PrescriptionCard.tsx** : dioptries OD/OG avec evolution
- [ ] **EquipmentTimeline.tsx** : frise chronologique equipements optiques
- [ ] **StockGauge.tsx** : jauge stock (vert/orange/rouge)
- [ ] **ClientScoreRadar.tsx** : radar score client
- [ ] **QuoteComparison.tsx** : comparatif devis cote a cote
- [ ] **SAVTracker.tsx** : stepper horizontal workflow SAV
- [ ] **VoucherCard.tsx** : carte bon d'achat (code, montant, expiration)
- [ ] **RenewalBanner.tsx** : bandeau alerte renouvellement

## 5.2 Nouvelles Pages (P1)

- [ ] [NEW] `/stock` — catalogue produits, niveaux stock, alertes rupture
- [ ] [NEW] `/sav` — liste SAV + detail + KPIs
- [ ] [NEW] `/calendrier` — vue RDV semaine/mois
- [ ] [NEW] `/analytics/cosium` — ventilation financiere complete
- [ ] [NEW] `/catalogue` — montures + verres Cosium navigables
- [ ] [NEW] `/admin/data-quality` — qualite donnees synchronisees

## 5.3 Accessibilite & Polish (P2)

- [ ] **WCAG AA** : audit contrastes, navigation clavier, focus visible
- [ ] [BUG] **ARIA dropdown** : `Header.tsx:202` — `aria-haspopup="dialog"` devrait etre `"menu"`
- [ ] **aria-describedby** sur tous les champs de formulaire
- [ ] **Raccourcis clavier** : Ctrl+K recherche, Ctrl+N nouveau, Ctrl+S sauvegarder
- [ ] **Dark mode** : toggle + tokens coherents
- [ ] **Onboarding** : tutoriel interactif premier login
- [ ] **Recherche globale enrichie** : clients + factures + devis + SAV + produits
- [ ] **Notifications push** : SSE temps reel (nouveau SAV, paiement, sync)
- [ ] [BUG] **SSEListener sans ErrorBoundary** : `AuthLayout.tsx:49` — crash possible de toute l'app. Wrapper dans `<ErrorBoundary>`.
- [ ] **Messages erreur humains** : mapper 5xx → "Erreur serveur. Reessayez dans quelques minutes."
- [ ] [PERF] **SWR retry** : ajouter exponential backoff (pas retry immediat)
- [ ] **Print styles** : `@media print` pour devis, factures, fiches client

## 5.4 TypeScript & Code Quality Frontend (P2)

- [ ] **ESLint strict** : `no-explicit-any` passer de "warn" a "error"
- [ ] **exhaustive-deps** : passer de "warn" a "error"
- [ ] **Centraliser types** : inline types → `lib/types/`
- [ ] **Zod schemas manquants** : facture, rapprochement, relance
- [ ] **Bannir `any` restants**
- [ ] **ESLint bloquant en CI** : retirer `ignoreDuringBuilds: true` de `next.config.ts`
- [ ] **Sentry production** : wirer `sentry.client.config.ts` au DSN reel
- [ ] **Web Vitals** : LCP, FID, CLS monitorees

---

# ═══════════════════════════════════════════════
# PHASE 6 — MARKETING & CRM AVANCE
# ═══════════════════════════════════════════════
> Estimation : ~40h

- [x] Marketing service basique + campagnes
- [ ] [NEW] **Segments dynamiques** : dernier achat > 2 ans, progressifs, < 40 ans...
- [ ] [NEW] **Bons d'achat Cosium** : afficher vouchers actifs + alertes expiration
- [ ] [NEW] **Campagne renouvellement** : workflow segment → template → envoi → conversion
- [ ] [NEW] **Timeline unifiee** : notes Cosium + emails + appels + SMS
- [ ] [NEW] **ROI par campagne** : CA genere par campagne
- [ ] [NEW] **Dashboard fidelite** : points, parrainages, bons (depuis Cosium)
- [ ] [NEW] **Top clients** : classement CA, frequence, anciennete → actions VIP

---

# ═══════════════════════════════════════════════
# PHASE 7 — MULTI-TENANT & SCALE
# ═══════════════════════════════════════════════
> Supporter 50+ magasins.
> Estimation : ~50h

- [x] Architecture multi-tenant basique (tenant_id, RLS)
- [ ] **Credentials Cosium par tenant** : verifier isolation chiffrement Fernet
- [ ] **Sync isolee** : une task Celery par tenant, zero contamination
- [ ] **Admin groupe** : `/admin/group-dashboard` agrege
- [ ] **Switch tenant** : `/auth/switch-tenant` avec nouveau JWT
- [ ] [NEW] **Comparatif inter-magasins** : KPIs cote a cote
- [ ] [NEW] **Stock inter-magasins** : vue consolidee + transfert suggere
- [ ] **Sync incrementale** : delta depuis dernier sync
- [ ] **Cache Redis** : reference data (produits, sites, payment-types) TTL 24h
- [ ] **Connection pooling** : optimiser pour 50 tenants concurrents
- [ ] **Rate limiting Cosium** : backoff exponentiel
- [ ] [PERF] **N+1 queries** : `client_service.py:52-56` — `calculate_client_completeness()` appele N fois. Batch.
- [ ] [PERF] **COUNT(*) lent** : `client_repo.search():31` — utiliser pattern LIMIT+1 au lieu de full count.
- [ ] [PERF] **time.sleep() bloquant** : `cosium/client.py:129,158,190` — bloque le worker thread. Utiliser asyncio.

---

# ═══════════════════════════════════════════════
# PHASE 8 — OBSERVABILITE & MONITORING
# ═══════════════════════════════════════════════
> Estimation : ~40h

- [ ] **Prometheus middleware** : implementer `/api/v1/metrics` (Counter, Histogram)
- [ ] **Grafana dashboards** : ops (infra) + metier (CA, sync, clients)
- [ ] **Sentry** : capture erreurs frontend + backend avec contexte
- [ ] **Alerting** : Slack/email si sync echoue, latence > 5s, erreur > 5%
- [ ] **Health checks** : separer `/health/live` de `/health/ready`
- [ ] [BUG] **Health check session leak** : `main.py:335-358` — `db.execute(text("SELECT 1"))` sans commit/close
- [ ] **Logs structures JSON** : correlation ID par requete
- [ ] **Request/response logging** : middleware avec masquage PII
- [ ] [BUG] **Masquage PII incomplet** : `core/logging.py:18-33` — ne masque que les cles, pas les valeurs contenant "password:xxx"
- [ ] **Log rotation** : taille + temps
- [ ] **Audit trail complet** : chaque consultation donnee sensible logguee
- [ ] **RGPD** : droit a l'oubli, export, consentements
- [ ] **Retention** : purge auto logs > 12 mois

---

# ═══════════════════════════════════════════════
# PHASE 9 — BACKEND POLISH & ARCHITECTURE
# ═══════════════════════════════════════════════
> Estimation : ~50h

## 9.1 Architecture (P2)

- [ ] [BUG] **OAuth2PasswordBearer duplique** : `core/deps.py:14` + `core/tenant_context.py:14` — centraliser dans `get_token_from_request()`
- [ ] [BUG] **PecService erreur inversee** : `pec_service.py:81` — `BusinessError("FACTURE_NOT_FOUND", "...")` avec args inverses
- [ ] **Services mixent audit + events** : separer avec event bus
- [ ] **Repos return types incoherents** : standardiser (ORM objects, services convertissent)
- [ ] **Services mixent objets et primitifs** : toujours utiliser schemas en entree
- [ ] **CosiumClient non injectable** : instancie globalement (ligne 294). Utiliser factory + injection.
- [ ] **Refresh token rotation** : chaque refresh = nouveau token, ancien invalide
- [ ] **RBAC par ressource** : `@require_resource_ownership("client", client_id)` sur endpoints sensibles
- [ ] **Timeout par appel Cosium** : pas de timeout global client (60s), timeout par endpoint

## 9.2 Code Quality (P2)

- [ ] **Dead code** : passer ruff pour supprimer le code mort
- [ ] **Docstrings** : 96 services sans docstring
- [ ] **Type hints return** : partout
- [ ] **Prefixer methodes privees** : `_x` → `__x`
- [ ] **Validations Pydantic** : min/max/regex sur tous les champs
- [ ] **`__all__`** : definir les exports publics de chaque module
- [ ] **Recherche sans limite** : `client_repo.py:20-30` — pas de `max_length` sur query. Ajouter `len(query) > 100 → erreur`.

## 9.3 PEC V12 Intelligence [NEW] (P1)

- [ ] [NEW] **Liaison 100% factures** : fuzzy matching via `_links.customer.href` (8h)
- [ ] [NEW] **Table client_mutuelles** : relation N-N (2h)
- [ ] [NEW] **Auto-detection mutuelle** : depuis TPP/invoices/documents (4h)
- [ ] [NEW] **OCR pipeline** : Tesseract + pdfplumber (6h)
- [ ] [NEW] **Classification documents** : ordonnance, devis, attestation, etc. (3h)
- [ ] [NEW] **Parsers structures** : 6 types de documents (12h)
- [ ] [NEW] **Consolidation multi-source** (8h)
- [ ] [NEW] **Detection incoherences** + alertes (4h)
- [ ] [NEW] **PEC assistant frontend** : onglet interactif fiche client (8h)

---

# ═══════════════════════════════════════════════
# PHASE 10 — VISION LONG TERME
# ═══════════════════════════════════════════════
> Estimation : ~80h

## 10.1 Portail Client (P3)

- [ ] Espace client web : devis, factures, RDV, prescription
- [ ] Prise de RDV en ligne
- [ ] Suivi SAV public
- [ ] Signature electronique devis

## 10.2 Integrations Externes (P3)

- [ ] QR Code par dossier/devis
- [ ] SMS rappel RDV / relance impaye
- [ ] Export comptable Sage/Cegid/QuickBooks
- [ ] Carte vitale (hardware dependant)
- [ ] Webhooks entrants
- [ ] Connecteur Zapier/Make
- [ ] API publique v1

## 10.3 Mobile Avance (P3)

- [ ] [PWA] Mode hors-ligne enrichi : consultation fiches clients cachees
- [ ] [PWA] Scan EAN depuis camera : stock + infos produit
- [ ] [PWA] Notifications push natives (via service worker)

## 10.4 DX & Tooling (P3)

- [ ] Storybook UI components
- [ ] openapi-typescript client auto-genere
- [ ] Semantic versioning CI tags
- [ ] Prettier + Ruff pre-commit hooks
- [ ] Bootstrap script nouveau dev
- [ ] VS Code debug profiles
- [ ] Seed data generator
- [ ] Suite E2E Playwright

---

# ═══════════════════════════════════════════════
# RESUME EXECUTIF
# ═══════════════════════════════════════════════

| Phase | Items | Effort | Priorite |
|-------|-------|--------|----------|
| **Phase 0** — Urgences (bugs, secu, prod) | ~50 | 80h | P0 [!] |
| **Phase 1** — PWA & Responsive | ~35 | 60h | P0-P1 |
| **Phase 2** — Cosium Core sync | ~55 | 150h | P0-P2 |
| **Phase 3** — Intelligence metier | ~40 | 120h | P0-P1 |
| **Phase 4** — Copilote IA | ~20 | 80h | P1-P2 |
| **Phase 5** — UX Premium & Polish | ~35 | 80h | P1-P2 |
| **Phase 6** — Marketing & CRM | ~10 | 40h | P2 |
| **Phase 7** — Multi-tenant & Scale | ~15 | 50h | P1-P2 |
| **Phase 8** — Observabilite | ~15 | 40h | P2 |
| **Phase 9** — Backend Polish & PEC V12 | ~25 | 50h | P1-P2 |
| **Phase 10** — Vision long terme | ~20 | 80h | P3 |
| **TOTAL** | **~320 items** | **~830h** | |

---

## CHEMIN CRITIQUE RECOMMANDE

```
Semaine 1-2  : Phase 0 (bugs critiques + securite + deploy)
Semaine 3-4  : Phase 1 (PWA + responsive)
Semaine 5-8  : Phase 2.1 + 2.2 (clients enrichis + dossiers optiques)
Semaine 9-10 : Phase 3.1 + 3.2 (file d'actions + dashboard cockpit)
Semaine 11-12: Phase 5 (UX polish) + Phase 7 (scale)
Semaine 13+  : Phases 4, 6, 8, 9, 10 par priorite
```

> **Objectif** : un Cosium Copilot PWA fonctionnel, securise, avec dossiers optiques
> et dashboard intelligent en **12 semaines**.

---

*Ce document remplace TODO.md, TODO_V2.md, TODO_V3.md, TODO_V4.md, TODO_V5.md et l'ancien TODO_MASTER.md.*
*Les anciennes TODOs sont conservees comme archive historique.*
