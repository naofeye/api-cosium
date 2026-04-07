# TODO V5 — OptiFlow AI — Audit adversarial + qualite + UX

> **Date** : 2026-04-07
> **Contexte** : 5e audit — pentest, qualite code, et vision produit utilisateur
> **Methode** : Pentest adversarial + audit qualite code + audit UX opticien
> **Regle** : Cocher `[x]` quand termine.

---

## PHASE 1 — CRITIQUE : SECURITE (Semaine 1)
> Vulnerabilites exploitables trouvees par pentest

### 1.1 JWT Role Mismatch [CRITIQUE]
- [x] `services/auth_service.py:116` — Le JWT encode `user.role` (global) au lieu de `tenant_user.role` (par tenant) → utiliser le role du TenantUser default_tenant
- [x] `services/admin_user_service.py:68` — A la creation d'un user, `User.role` prend la valeur du payload mais devrait toujours etre "user" (le role reel est dans TenantUser)

### 1.2 Race condition signup [ELEVE]
- [x] `services/onboarding_service.py` — La generation de slug unique n'est pas atomique → ajouter UNIQUE constraint sur tenant.slug + try/catch/retry

### 1.3 File upload magic bytes [MOYEN]
- [ ] `services/document_service.py` — Validation par extension + MIME seulement → ajouter verification magic bytes avec `python-magic` ou signature manuelle

### 1.4 Rate limiting manquant [MOYEN]
- [x] `core/rate_limiter.py` — Ajouter rate limit sur PEC status change, batch task submission, et bulk import

---

## PHASE 2 — ELEVE : INTEGRITE DES DONNEES (Semaine 1-2)
> Validation metier manquante

### 2.1 Validation devis mathematique [CRITIQUE]
- [x] `domain/schemas/devis.py` — Ajouter validateur : `part_secu + part_mutuelle + reste_a_charge == montant_ttc`
- [x] `domain/schemas/devis.py` — Limiter `taux_tva` entre 0 et 30 (pas 150%)
- [x] Frontend `devis/new/page.tsx` — Ajouter validation temps reel que les parts = total TTC

### 2.2 Protection suppression client [ELEVE]
- [x] `services/client_service.py` — Avant soft-delete, verifier s'il y a des cases actives (non archivees) et avertir
- [x] Frontend — Ajouter dialog de confirmation listant les entites liees (X cases, Y documents, Z paiements)

### 2.3 Calculs financiers Decimal dans services [ELEVE]
- [x] `services/analytics_kpi_service.py` — Remplacer `float()` par `Decimal()` dans tous les calculs financiers
- [x] `services/reconciliation_service.py` — Idem
- [x] Grep `float(` dans tous les services financiers et convertir

### 2.4 deleted_at dans l'API response [MOYEN]
- [x] `domain/schemas/clients.py` — Retirer `deleted_at` du schema `ClientResponse`

---

## PHASE 3 — ELEVE : UX CRITIQUE (Semaine 2-3)
> Ce qu'un opticien remarquerait immediatement

### 3.1 Barre de recherche globale [ELEVE]
- [x] GlobalSearch.tsx existe deja (229 lignes) avec Ctrl+K, debounce, resultats groupes
- [x] Integre dans Header.tsx avec keyboard listener Ctrl+K/Cmd+K

### 3.2 Merge client preview [ELEVE]
- [x] DuplicatesPanel: dialog de preview avec resume conserver/supprimer + liste transferts
- [x] Bouton Annuler visible + spinner disable pendant fusion

### 3.3 Notifications visibles [ELEVE]
- [x] Header a deja : icone cloche + badge non-lus + dropdown notifications + mark-as-read (verifie dans le code)
- [x] Panneau dropdown avec list, navigation, close Escape (deja implement dans Header.tsx)
- [x] Utilise SWR avec refreshInterval 30s pour le compteur non-lus

### 3.4 Sync errors visibles [MOYEN]
- [x] Frontend admin sync — Quand `has_errors=True`, afficher un banner rouge "Sync incomplete" avec details
- [x] Backend sync router — Retourner HTTP 207 au lieu de 200 quand `has_errors=True`

---

## PHASE 4 — MOYEN : QUALITE CODE (Semaine 3-4)
> Maintenabilite et patterns

### 4.1 Constants pour les magic strings [MOYEN]
- [x] Creer `core/constants.py` avec STATUS_DRAFT, STATUS_PENDING, ROLE_ADMIN, etc.
- [ ] Mettre a jour les 30+ fichiers qui hardcodent `"draft"`, `"admin"`, `"pending"`

### 4.2 Base repository pattern [MOYEN]
- [x] Creer `repositories/base_repo.py` avec `get_by_id()`, `create()`, `update()` generiques
- [ ] Refactorer les 10+ repos avec le pattern duplique

### 4.3 Return type hints manquants [FAIBLE]
- [ ] Ajouter `-> None` ou type de retour sur les 13+ fonctions dans export_pdf_*, ai_context_repo

### 4.4 Reconciliation complexity [FAIBLE]
- [ ] `reconciliation_service.py:223-292` — Extraire la determination de statut dans une state machine

---

## PHASE 5 — MOYEN : FONCTIONNALITES MANQUANTES (Semaine 4+)
> Ce que l'opticien attend

### 5.1 Undo / Restore client [MOYEN]
- [ ] Frontend — Page admin pour voir les clients supprimes et les restaurer
- [x] Bouton "Restaurer" dans la liste des clients supprimes

### 5.2 Export ameliore [MOYEN]
- [ ] Export Excel (pas seulement CSV) pour factures et clients
- [x] Export FEC (Fichier d'Echanges Comptables) pour l'administration fiscale
- [x] Vue impression avec logo/branding pour devis et factures

### 5.3 PEC ameliore [MOYEN]
- [ ] Precontrol : permettre "exception approuvee" pour overrider un check
- [ ] Batch PEC submission (soumettre plusieurs PEC en une fois)
- [ ] Tracking reponse mutuelle avec relance automatique

### 5.4 Onboarding ameliore [FAIBLE]
- [ ] Tooltips sur les pages principales ("Commencez par creer un dossier")
- [ ] Lien "Ou trouver mes identifiants Cosium ?" dans l'etape de connexion
- [ ] Indication raccourcis clavier (press ? pour voir)

---

## PHASE 6 — FAIBLE : TESTS ET MONITORING (Ongoing)

### 6.1 Tests Docker [FAIBLE]
- [ ] Deploiement E2E compose prod
- [ ] TLS bout en bout
- [ ] Cycle backup → restore
- [ ] Multi-tenant parallele
- [ ] Sync Cosium realiste
- [ ] Profiler endpoints

### 6.2 Monitoring [FAIBLE]
- [ ] Prometheus metrics endpoint
- [ ] Monitorer temps de reponse
- [ ] Monitorer queue Celery
- [ ] Alertes 5xx
- [ ] Slow query logging

---

## SUIVI GLOBAL

| Phase | Description | Taches | Priorite |
|-------|-------------|--------|----------|
| Phase 1 | Securite (pentest) | 5 | CRITIQUE |
| Phase 2 | Integrite des donnees | 8 | ELEVE |
| Phase 3 | UX critique | 8 | ELEVE |
| Phase 4 | Qualite code | 4 | MOYEN |
| Phase 5 | Fonctionnalites manquantes | 9 | MOYEN |
| Phase 6 | Tests et monitoring | 11 | FAIBLE |
| **TOTAL** | | **45** | |

---

## RESUME DES FINDINGS V5 (INEDITS)

### Pentest (3 critiques)
1. **JWT role mismatch** — Le JWT contient `User.role` (global "admin") au lieu de `TenantUser.role` (reel)
2. **Race condition signup** — Generation slug non atomique, duplicates possibles
3. **File upload** — Validation extension seulement, pas de magic bytes

### UX opticien (5 critiques)
4. **Pas de recherche globale** — L'API existe mais pas de barre de recherche dans le header
5. **Merge sans preview** — Transfere des centaines d'entites sans resume
6. **Notifications invisibles** — L'API existe, le frontend ne l'affiche pas
7. **Devis sans validation math** — `part_secu + mutuelle + RAC` peut depasser le total TTC
8. **Suppression client sans warning** — Pas d'avertissement sur les entites liees

### Qualite code (2 moyens)
9. **30+ magic strings** — Statuts, roles, limites hardcodes partout
10. **10+ repos dupliques** — Meme pattern get_by_id copie-colle
