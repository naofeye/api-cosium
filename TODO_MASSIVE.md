# TODO MASSIVE — OptiFlow AI

> **Etat** : 640 tests, 44 pages frontend, 35 routers, 52 services, 115k+ enregistrements Cosium, 40 760 documents (10 GB)
> **Score qualite** : 99/100 (audit 20 iterations)
> **V12 PEC Intelligence** : Etapes 1-10 terminees (OCR, parsers, consolidation, PEC)

---

## PRIORITE 1 — BLOQUANTS / CRITIQUES

### 1.1 Contacter Cosium pour acces API propre [ ]
- Le cookie `access_token` expire toutes les ~4-6h
- Demander un acces OAuth2 client_credentials (token permanent)
- Demander pourquoi `/third-party-payments` retourne 500
- Demander comment depasser la limite de 50 items par page sur `/customers`
- **Impact** : elimine le renouvellement manuel de cookie

### 1.2 Deployer sur VPS [ ]
- Commander VPS (Ubuntu 22.04, 4 vCPU, 8 GB RAM, 100 GB SSD)
- DNS : configurer le domaine (A record)
- SSL : certbot + nginx (deja configure dans nginx.conf)
- `.env.production` avec vrais secrets
- Premier deploiement : `./scripts/deploy.sh`
- Smoke test en prod
- **Impact** : rend le produit accessible aux utilisateurs reels

### 1.3 Tiers payant (13 082 enregistrements) [ ]
- Actuellement erreur 500 cote Cosium
- Si Cosium corrige : lancer sync `POST /sync/third-party-payments`
- Enrichira les KPIs financiers (part secu vs mutuelle)
- **Impact** : donnees financieres completes

### 1.4 1 264 clients manquants [ ]
- Limitation pagination Cosium (hard limit 50 items par page)
- Solutions possibles :
  - Demander a Cosium un export CSV/JSON complet
  - Utiliser d'autres filtres API (date de creation, site, etc.)
  - Demander une augmentation de la limite pagination
- **Impact** : base clients complete

---

## PRIORITE 2 — AMELIORATIONS PRODUIT (fort impact utilisateur)

### 2.1 Lancer l'extraction OCR sur les 40 760 documents [ ]
- Dockerfile avec Tesseract deja prepare
- Lancer `POST /documents/{id}/extract` par batch (Celery task)
- Estimer le temps (~1-2s par doc = ~11-22h pour tout)
- Stocker resultats dans `document_extractions`
- **Impact** : permet la consolidation PEC avec donnees reelles

### 2.2 Lancer la detection mutuelles [ ]
- Appeler `POST /admin/detect-mutuelles` pour tous les clients
- Verifiera les TPP et invoices pour identifier les mutuelles
- **Impact** : mutuelle de chaque client identifiee automatiquement

### 2.3 Lancer le re-link factures avec nouveau matching [ ]
- Appeler `POST /sync/invoices` pour re-syncer avec fuzzy + HAL links
- Le matching `_links.customer.href` devrait ameliorer significativement
- Objectif : 53% → 80%+
- **Impact** : vue 360 client plus complete

### 2.4 Enrichir les 3 500 clients restants (opticien/ophtalmo) [ ]
- Appeler `POST /sync/enrich-clients` plusieurs fois (500/batch)
- ~7 batches, ~3 min chaque
- **Impact** : 1 623 → 3 700 clients avec opticien referent

### 2.5 Agenda calendrier visuel [ ]
- Remplacer la liste plate `/agenda` par un vrai calendrier
- Utiliser FullCalendar.js ou react-big-calendar
- Vue semaine/mois avec les RDV Cosium
- Clic sur un RDV → fiche client
- **Impact** : UX quotidienne pour l'opticien

### 2.6 Ameliorer la recherche globale [ ]
- Actuellement : clients + factures + ordonnances
- Ajouter : documents par nom, paiements, RDV
- Raccourci clavier Ctrl+K pour ouvrir la recherche
- **Impact** : productivite utilisateur

---

## PRIORITE 3 — QUALITE & ROBUSTESSE

### 3.1 Tests E2E V12 (Etape 11 du plan) [ ]
- Parcours complet : client → sync → extraire docs → consolider → PEC → corriger → soumettre
- Test avec donnees reelles Cosium
- Test performance (<3s pour consolidation avec 50 docs)
- Verifier regles d'incoherence
- **Impact** : validation metier du module PEC

### 3.2 Sentry monitoring [ ]
- Activer avec un vrai DSN (SENTRY_DSN dans .env)
- Tester capture d'erreur
- Configurer alertes email
- **Impact** : detection proactive des bugs en prod

### 3.3 Backup automatise [ ]
- Cron pg_dump quotidien (scripts/backup.sh existe)
- Backup MinIO (10 GB de documents)
- Retention 30 jours
- Test de restauration
- **Impact** : protection des donnees

### 3.4 Tests frontend manquants [ ]
- Couvrir les nouvelles pages V12 (PEC, mutuelles)
- Tests E2E Playwright ou Cypress
- Objectif : 80%+ couverture frontend
- **Impact** : prevention regressions

---

## PRIORITE 4 — FONCTIONNALITES NOUVELLES

### 4.1 Dashboard PEC [ ]
- Vue synthetique de toutes les PEC en cours
- Taux d'acceptation, delais moyens, montants recuperes
- Filtre par statut, mutuelle, periode
- **Impact** : pilotage PEC

### 4.2 Notifications intelligentes [ ]
- Ordonnance expirante → notif "Client X a une ordonnance de plus de 2 ans"
- Impaye > 60 jours → notif "Relance recommandee pour Client Y"
- Cookie Cosium expire → notif admin (deja fait)
- **Impact** : proactivite metier

### 4.3 Import/Export ameliore [ ]
- Import clients depuis CSV/Excel (formulaire)
- Export personnalise (choix des colonnes)
- Export CERFA ou formulaires OCAM pre-remplis
- **Impact** : productivite

### 4.4 Multi-langue preparation [ ]
- Extraire toutes les strings hardcodees
- Installer next-intl ou react-i18next
- Francais par defaut, anglais en option
- **Impact** : scalabilite internationale

### 4.5 Extraction IA (Claude) pour documents [ ]
- Remplacer regex par appel Claude pour parsing documents
- Meilleure precision sur formats varies d'ordonnances
- Plus robuste que l'OCR + regex
- **Impact** : qualite extraction x10

### 4.6 Pre-remplissage formulaires OCAM [ ]
- Generer PDF formulaires PEC pre-remplis
- Adapter selon le portail OCAM cible (Almerys, Visilab, etc.)
- **Impact** : gain de temps enorme pour l'opticien

### 4.7 Mode hors-ligne [ ]
- Service Worker pour cache des donnees clients
- Consultation des fiches sans connexion
- Sync quand la connexion revient
- **Impact** : usage en mobilite

---

## PRIORITE 5 — POLISH & DETAILS

### 5.1 Animations page transitions [ ]
- Transitions entre pages (Next.js layout animations)
- Loading bar en haut de page pendant la navigation
- **Impact** : sensation premium

### 5.2 Raccourcis clavier [ ]
- Ctrl+K : recherche globale
- Ctrl+N : nouveau client/dossier/devis
- Ctrl+S : sauvegarder formulaire
- **Impact** : power users

### 5.3 Historique PEC / Machine learning [ ]
- Apprendre des PEC precedentes du meme client/mutuelle
- Suggerer les montants probables (part secu, mutuelle)
- **Impact** : intelligence predictive

### 5.4 Connexion directe portails OCAM [ ]
- API directe vers Almerys, Visilab, etc.
- Pre-remplissage automatique sans copier-coller
- Phase 2 (necessite partenariats)
- **Impact** : automatisation complete

---

## METRIQUES ACTUELLES

| Metrique | Valeur |
|----------|--------|
| Tests backend | 640 |
| Pages frontend | 44 |
| Routers API | 35 |
| Services | 52 |
| Models | 20 |
| Commits | 45 |
| Score qualite | 99/100 |
| Donnees Cosium | 115 712 enregistrements |
| Documents PDF | 40 760 (10 GB) |
| Clients | 3 729 / 4 993 (75%) |
| Factures liees | 13 263 / 25 162 (53%) |
| Mutuelles detectees | 0 (a lancer) |
| Extractions OCR | 0 (a lancer) |

---

## ORDRE D'EXECUTION RECOMMANDE

### Cette semaine
1. Contacter Cosium (1.1)
2. Lancer detection mutuelles (2.2)
3. Lancer enrichissement opticien restant (2.4)
4. Lancer extraction OCR batch (2.1)

### Semaine prochaine
5. Deployer VPS (1.2)
6. Tests E2E V12 (3.1)
7. Sentry monitoring (3.2)
8. Agenda calendrier visuel (2.5)

### Mois prochain
9. Dashboard PEC (4.1)
10. Notifications intelligentes (4.2)
11. Extraction IA Claude (4.5)
12. Pre-remplissage OCAM (4.6)
