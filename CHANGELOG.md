# Changelog

## v1.3.0 — Templates, Aide & Consolidation (2026-04-04)

### Nouvelles fonctionnalites
- **Templates email HTML Jinja2** : base.html, password_reset.html, welcome.html, relance.html avec design professionnel OptiFlow (en-tete bleu, boutons CTA, footer)
- **Page Aide** : centre d'aide avec FAQ accordeons (6 questions), raccourcis clavier, contact support — accessible depuis la sidebar
- **Utilitaire render_email** : `integrations/email_templates.py` pour rendre les templates avec contexte Jinja2

### Securite
- **Deps vulnerables mises a jour** : cryptography 44.0.3 → 46.0.6 (CVE-2026-26007, CVE-2026-34073), PyJWT 2.10.1 → 2.12.0 (CVE-2026-32597), python-multipart 0.0.20 → 0.0.22 (CVE-2024-24486)

### Documentation
- **HISTORIQUE_TODO.md** : synthese des 11 iterations de developpement (V1 a V11)
- **CHANGELOG v1.3.0** ajoutee
- **README.md** mis a jour (306+ tests, 126 endpoints, templates email, page aide)
- Nettoyage TODO_V2 a V10 (archives dans HISTORIQUE_TODO.md, V11 reste active)

### Qualite
- Auth service refactore : utilise le template Jinja2 pour l'email de reinitialisation au lieu de HTML inline
- Sidebar enrichie : lien "Aide" avec icone HelpCircle

---

## v1.2.0 — Securite & Robustesse (2026-04-04)

### Securite
- **Swagger desactive en production** : `docs_url` et `redoc_url` a `None` quand `APP_ENV` n'est pas local/development/test
- **Rate limiting etendu** : `/api/v1/onboarding/signup` (5 req/min), `/api/v1/ai/copilot/query` (30 req/min) en plus de login et refresh
- **Auth httpOnly** : documentation du flow cookie-based dans CONTRIBUTING.md
- **Encryption Fernet** : documentation du chiffrement des credentials Cosium

### Tests
- **279 tests backend** (88% couverture, +51 tests)
- **70+ tests frontend** (10 fichiers vitest)
- `test_deps.py` : 8 tests couvrant `get_current_user` (token valide, absent, expire, invalide, user inactif) et `require_role` (admin OK, operator 403)
- `test_claude_provider.py` : 8 tests couvrant le provider IA (sans cle, avec mock Anthropic, contexte, erreurs API)

### Documentation
- CHANGELOG v1.2.0 ajoutee
- CONTRIBUTING.md enrichi (sections Auth httpOnly, Encryption)
- README.md mis a jour (compteurs tests, couverture)

---

## v1.1.0 — Polish & Uniformite (2026-04-04)

### Nouvelles fonctionnalites
- **Recherche globale** : barre de recherche dans le Header, resultats en temps reel (clients, dossiers, devis, factures)
- **PDF devis/factures** : generation avec reportlab, boutons telecharger sur les pages detail
- **Endpoint recherche** : `GET /api/v1/search?q=` multi-entites

### Qualite du code
- **0 fichier frontend > 300 lignes** : onboarding (842→89), clients/[id] (644→247), cases/[id] (449→122), + 5 autres pages decoupees en composants
- **16 pages migrees SWR** (dont Header) — cache, deduplication, auto-refresh notifications
- **11 schemas Zod** pour la validation des formulaires
- **247 tests backend** (86% couverture), **70 tests frontend** (10 fichiers)
- **Securite** : JWT check au startup, metrics scope par tenant, GDPR role-checked, nginx headers, Docker non-root
- **Edge cases** : guards division par zero, channels vides, user_id propages dans les services IA
- **Architecture decisions** documentees dans `docs/ARCHITECTURE_DECISIONS.md`

---

## v1.0.0 — Production Ready (2026-04-04)

### Fonctionnalites metier
- **CRM Client** : CRUD complet, recherche paginee, vue 360 avec historique
- **Gestion documentaire (GED)** : upload MinIO, categorisation, completude
- **Devis** : creation avec lignes, calculs automatiques (HT/TTC/RAC), workflow statut
- **Factures** : generation depuis devis signe, numerotation sequentielle
- **PEC (tiers payant)** : soumission, workflow statut, historique, relances
- **Paiements** : enregistrement, cle d'idempotence, ventilation multi-factures
- **Rapprochement bancaire** : import CSV, matching auto/manuel
- **Relances** : plans parametrables, templates, priorisation intelligente, envoi email
- **Marketing CRM** : segments, campagnes email/SMS, consentements RGPD
- **Dashboard** : KPIs financiers, balance agee, performance mutuelles, graphiques Recharts
- **IA Copilote** : 4 modes (dossier, financier, documentaire, marketing), RAG Cosium
- **Renouvellements** : detection IA, scoring, campagnes proactives

### Architecture et qualite
- **Multi-tenant** : isolation complete par magasin, switch tenant, dashboard reseau
- **Onboarding** : wizard 5 etapes, connexion Cosium, import automatique
- **Facturation SaaS** : Stripe (trial → paiement → acces), tracking IA, quotas
- **Multi-ERP** : abstraction ERPConnector, Cosium lecture seule verifie
- **230 tests backend** (pytest, couverture 82%), **36 tests frontend** (vitest)
- **TypeScript strict**, React Hook Form + Zod, SWR cache
- **Linting** : ruff (backend), prettier + tsc (frontend)
- **CI/CD** : GitHub Actions (lint + test + build)
- **Securite** : cookies httpOnly, RBAC, rate limiting, security headers, audit Cosium
- **Logging** : structlog JSON, request_id correlation
- **Error handling** : exceptions metier, format standardise, Error Boundaries React
- **Accessibilite** : focus-visible, aria-label, aria-live, modales accessibles
- **Documentation** : README, CONTRIBUTING, openapi.json, audit securite Cosium
