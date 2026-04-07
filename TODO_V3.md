# TODO V3 — OptiFlow AI — Audit post-refactoring final

> **Date** : 2026-04-07
> **Contexte** : Audit V3 avec regard neuf apres V1 (232 taches) et V2 (59 taches)
> **Methode** : Audit backend + frontend + infra par Claude Opus, focus production
> **Regle** : Cocher `[x]` quand termine. Ne jamais supprimer une ligne.

---

## PHASE 1 — CRITIQUE : TRANSACTIONS MANQUANTES (Semaine 1)
> Les repos utilisent db.flush() mais les services ne commitent pas toujours

### 1.1 Services sans db.commit() apres ecriture [CRITIQUE]
- [ ] `services/client_mutuelle_service.py` — `add_client_mutuelle()`, `delete_client_mutuelle()`, `detect_client_mutuelles()` : ajouter db.commit() en fin de fonction
- [ ] `services/pec_service.py` — `create_pec()`, `update_pec_status()`, `create_relance()` : ajouter db.commit()
- [ ] `services/pec_preparation_service.py` — `prepare_pec()`, `validate_field()` : ajouter db.commit()
- [ ] `services/pec_precontrol_service.py` — `add_document()`, `create_pec_from_preparation()` : ajouter db.commit()
- [ ] `services/pec_consolidation_service.py` — `correct_field()`, `refresh_preparation()` : ajouter db.commit()
- [ ] Auditer : `action_item_service`, `case_service`, `interaction_service`, `notification_service`, `reminder_service`, `ocam_operator_service` — verifier qu'ils commitent

### 1.2 Rollback manquant dans les tasks [ELEVE]
- [ ] `tasks/batch_tasks.py` — Ajouter `db.rollback()` dans le `except` du processus batch
- [ ] Verifier que toutes les tasks Celery font `db.rollback()` en cas d'erreur avant retry

---

## PHASE 2 — CRITIQUE : AUTH FRONTEND INCOHERENT (Semaine 1)
> La detection d'etat auth est desynchronisee apres suppression du cookie fallback

### 2.1 Etat auth frontend [CRITIQUE]
- [ ] `lib/auth.ts:19` — `isAuthenticated()` verifie encore `optiflow_authenticated` cookie → aligner avec middleware.ts qui utilise `optiflow_token` uniquement
- [ ] Verifier le flux complet : login → cookie set → middleware check → isAuthenticated() → pages protegees

---

## PHASE 3 — ELEVE : ROBUSTESSE FRONTEND (Semaine 1-2)
> Error boundaries, gestion d'erreurs, securite XSS

### 3.1 Error Boundaries manquantes [ELEVE]
- [ ] `components/layout/Header.tsx` — Wrapper ErrorBoundary (SWR notifications + trial info peuvent crasher)
- [ ] `dashboard/page.tsx` — Wrapper ErrorBoundary sur DashboardCharts, PayersTable, RecentActivity (pas seulement KPIs)
- [ ] Wrapper ErrorBoundary sur les imports dynamiques (charts section)

### 3.2 Gestion d'erreurs silencieuses [MOYEN]
- [ ] `devis/new/page.tsx` — `.catch(() => {})` silencieux → ajouter toast d'erreur
- [ ] `settings/page.tsx` — `.catch(() => {})` silencieux → ajouter toast d'erreur
- [ ] `components/layout/Header.tsx` — `.catch(() => {})` → ajouter log ou toast
- [ ] `dashboard/page.tsx` — `onError: () => {}` SWR silencieux → ajouter toast warning

### 3.3 XSS et securite [MOYEN]
- [ ] `dashboard/page.tsx:66` — `{aiResponse}` rendu sans echappement HTML → verifier que l'API sanitise ou ajouter escaping cote client

---

## PHASE 4 — ELEVE : INFRASTRUCTURE PRODUCTION (Semaine 2)
> Backup, scaling, monitoring

### 4.1 Backup et disaster recovery [CRITIQUE]
- [ ] `scripts/backup_db.sh` — Ajouter verification d'integrite apres backup (`pg_restore --list`)
- [ ] `scripts/restore_db.sh` — Ajouter `--no-owner` et gestion d'erreur transactionnelle
- [ ] Augmenter la retention de 30 jours a 90 jours
- [ ] Ajouter backup automatique MinIO dans le script deploy

### 4.2 Scaling [ELEVE]
- [ ] `nginx/nginx.conf:2` — Augmenter `worker_connections` de 1024 a 4096
- [ ] `backend/app/db/session.py` — Augmenter `pool_size=50, max_overflow=50` (40 actuel trop bas)
- [ ] Documenter la strategie de scaling horizontal dans DEPLOY.md (multi-instances API + load balancer)
- [ ] Ajouter `Cache-Control` headers pour les assets statiques Next.js dans nginx

### 4.3 CI/CD ameliorations [MOYEN]
- [ ] `.github/workflows/ci.yml` — Ajouter `npm run build` dans le job frontend (verifier que le build passe)
- [ ] `.github/workflows/ci.yml` — Ajouter execution des tests frontend (`npm run test`)
- [ ] `.github/workflows/ci.yml` — Ajouter `npm audit --audit-level=high` et `pip audit` pour les vulnerabilites

---

## PHASE 5 — MOYEN : SCHEMAS ET CONTRATS API (Semaine 2-3)

### 5.1 Validation Pydantic [MOYEN]
- [ ] `services/pec_consolidation_service.py:57` — `_profile_to_dict()` peut retourner des dicts qui ne matchent pas `UserValidationEntry`/`UserCorrectionEntry` → ajouter validation ou `model_construct()`

### 5.2 Soft deletes non enforces [MOYEN]
- [ ] Ajouter un index sur `deleted_at` pour les modeles avec soft-delete (Customer, Case)
- [ ] Verifier que tous les services filtrent bien `deleted_at IS NULL` sur les queries de lecture

---

## PHASE 6 — MOYEN : TESTS MANQUANTS (Semaine 3-4)

### 6.1 Tests critiques absents [MOYEN]
- [ ] Creer `tests/test_pec_preparation.py` — Workflow PEC complet (prepare, validate, correct, precontrol, submit)
- [ ] Creer `tests/test_payment_service.py` — Creation/modification/rapprochement paiements
- [ ] Creer `tests/test_cosium_invoice_sync.py` — Sync factures Cosium (incremental, full)
- [ ] Creer `tests/test_transaction_integrity.py` — Verifier que les services commitent correctement (post-migration flush)

### 6.2 Tests qui necessitent Docker [MOYEN]
- [ ] Tester un deploiement E2E avec docker-compose.prod.yml
- [ ] Tester TLS de bout en bout (necessite vrai domaine)
- [ ] Tester cycle backup → restore → verification donnees
- [ ] Tester multi-tenant parallele (2+ tenants)
- [ ] Tester sync Cosium avec donnees realistes
- [ ] Profiler les endpoints les plus lents

---

## PHASE 7 — FAIBLE : MONITORING ET OBSERVABILITE (Ongoing)

### 7.1 Monitoring [FAIBLE]
- [ ] Ajouter endpoint `/metrics` Prometheus-compatible
- [ ] Monitorer temps de reponse endpoints critiques
- [ ] Monitorer taille queue Celery
- [ ] Ajouter alertes sur erreurs 5xx
- [ ] Ajouter slow query logging (queries > 1s)

### 7.2 Accessibilite frontend [FAIBLE]
- [ ] `notifications/page.tsx:344` — Ajouter aria-label sur boutons icone-only
- [ ] `relances/templates/page.tsx:187` — Ajouter label associe au checkbox
- [ ] `renewals/page.tsx:229` — Ajouter label associe au checkbox

---

## SUIVI GLOBAL

| Phase | Description | Taches | Priorite |
|-------|-------------|--------|----------|
| Phase 1 | Transactions manquantes | 8 | CRITIQUE |
| Phase 2 | Auth frontend incoherent | 2 | CRITIQUE |
| Phase 3 | Robustesse frontend | 9 | ELEVE |
| Phase 4 | Infrastructure production | 10 | ELEVE |
| Phase 5 | Schemas et contrats API | 3 | MOYEN |
| Phase 6 | Tests manquants | 10 | MOYEN |
| Phase 7 | Monitoring et accessibilite | 8 | FAIBLE |
| **TOTAL** | | **50** | |

---

## POINTS POSITIFS CONFIRMES (pas de regression)

- 0 `except Exception` non justifie
- 0 `HTTPException` dans les services
- 0 `print()` dans le backend
- 0 `any` dans le TypeScript
- 0 endpoint sans authentification (sauf /health, correct)
- Secrets valides en production (model_validator)
- Logging masque les champs sensibles
- Token blacklist Redis operationnelle
- 18 tests de regression securite
- CI GitHub Actions 5 jobs
- DEPLOY.md precis et a jour
- Architecture service/repo/router respectee
- Cosium 100% lecture seule confirme
- Tous les imports et re-exports corrects apres refactoring
