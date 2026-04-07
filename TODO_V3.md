# TODO V3 — OptiFlow AI — Audit post-refactoring final

> **Date** : 2026-04-07
> **Contexte** : Audit V3 avec regard neuf apres V1 (232 taches) et V2 (59 taches)
> **Methode** : Audit backend + frontend + infra par Claude Opus, focus production
> **Regle** : Cocher `[x]` quand termine. Ne jamais supprimer une ligne.

---

## PHASE 1 — CRITIQUE : TRANSACTIONS MANQUANTES (Semaine 1)
> Les repos utilisent db.flush() mais les services ne commitent pas toujours

### 1.1 Services sans db.commit() apres ecriture [CRITIQUE]
- [x] `services/client_mutuelle_service.py` — db.commit() ajoute
- [x] `services/pec_service.py` — db.commit() ajoute
- [x] `services/pec_preparation_service.py` — db.commit() ajoute
- [x] `services/pec_precontrol_service.py` — db.commit() ajoute
- [x] `services/pec_consolidation_service.py` — db.commit() ajoute
- [x] Audite : action_item, case, interaction services — db.commit() ajoute la ou necessaire

### 1.2 Rollback manquant dans les tasks [ELEVE]
- [x] `tasks/batch_tasks.py` — db.rollback() deja present dans le except
- [x] Toutes les tasks Celery font db.rollback() en cas d'erreur

---

## PHASE 2 — CRITIQUE : AUTH FRONTEND INCOHERENT (Semaine 1)
> La detection d'etat auth est desynchronisee apres suppression du cookie fallback

### 2.1 Etat auth frontend [CRITIQUE]
- [x] `lib/auth.ts` — isAuthenticated() utilise `optiflow_authenticated` qui EST toujours set par le backend (auth.py:40-42). C'est correct et coherent : httpOnly `optiflow_token` pour le middleware serveur, `optiflow_authenticated` non-httpOnly pour la detection client-side
- [x] Flux verifie : login → cookies set (token httpOnly + authenticated) → middleware check token → isAuthenticated check authenticated

---

## PHASE 3 — ELEVE : ROBUSTESSE FRONTEND (Semaine 1-2)
> Error boundaries, gestion d'erreurs, securite XSS

### 3.1 Error Boundaries manquantes [ELEVE]
- [x] `components/layout/Header.tsx` — ErrorBoundary ajoute
- [x] `dashboard/page.tsx` — ErrorBoundary sur toutes les sections (TodayAppointments, Charts, Intelligence, Reconciliation, Overdue)
- [x] Imports dynamiques proteges par ErrorBoundary

### 3.2 Gestion d'erreurs silencieuses [MOYEN]
- [x] `devis/new/page.tsx` — `.catch(() => {})` remplace par console.error
- [x] `settings/page.tsx` — `.catch(() => {})` remplace par toast/console.error
- [x] `components/layout/Header.tsx` — gestion d'erreur amelioree
- [x] `dashboard/page.tsx` — SWR `onError` silencieux acceptable (dashboard resilient, ErrorBoundary en place)

### 3.3 XSS et securite [MOYEN]
- [ ] `dashboard/page.tsx:66` — `{aiResponse}` → verifier sanitisation API ou escaper

---

## PHASE 4 — ELEVE : INFRASTRUCTURE PRODUCTION (Semaine 2)
> Backup, scaling, monitoring

### 4.1 Backup et disaster recovery [CRITIQUE]
- [x] `scripts/backup_db.sh` — Verification integrite ajoutee (`pg_restore --list`)
- [x] `scripts/restore_db.sh` — `--no-owner` + gestion d'erreur transactionnelle
- [x] Retention augmentee de 30 a 90 jours
- [ ] Ajouter backup automatique MinIO dans le script deploy

### 4.2 Scaling [ELEVE]
- [x] `nginx/nginx.conf` — `worker_connections` augmente a 4096
- [x] `backend/app/db/session.py` — Pool augmente a 50+50=100
- [x] Section "Scaling horizontal" ajoutee dans DEPLOY.md (replicas, workers, PgBouncer, Redis Sentinel)
- [x] Cache-Control `max-age=31536000, immutable` ajoute pour `/_next/static/` dans nginx

### 4.3 CI/CD ameliorations [MOYEN]
- [x] `.github/workflows/ci.yml` — Job `frontend-build` ajoute (`npm run build`)
- [ ] `.github/workflows/ci.yml` — Ajouter execution des tests frontend (`npm run test`)
- [x] `.github/workflows/ci.yml` — `npm audit --audit-level=high` ajoute

---

## PHASE 5 — MOYEN : SCHEMAS ET CONTRATS API (Semaine 2-3)

### 5.1 Validation Pydantic [MOYEN]
- [x] `pec_consolidation_service.py` — `_profile_to_dict()` fait json.loads() sur des donnees serialisees depuis les memes schemas Pydantic, risque faible, acceptable

### 5.2 Soft deletes non enforces [MOYEN]
- [x] Index `deleted_at` ajoute sur Customer et Case
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
