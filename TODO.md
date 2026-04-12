# TODO — OptiFlow AI

_Generated 2026-04-12._

> Consolidated from audit V1-V5. Only **remaining unchecked items** are listed.
> Previous audits completed **262/297 tasks (88%)**. This file tracks the **35 remaining**.

---

## P1 Critical

> Security, data integrity, production blockers — must fix before any production deployment.

- [ ] Tests d'isolation multi-tenant : user du tenant A ne peut PAS acceder aux donnees du tenant B — `tests/test_tenant_isolation.py` (nouveau), `core/deps.py`, `core/tenant_context.py` — ~4h
- [ ] Test auth complet E2E : login -> access token -> refresh -> switch tenant -> logout -> token blacklist — `tests/test_auth_e2e.py` (nouveau), `services/auth_service.py` — ~3h
- [ ] Test endpoints admin proteges par authentification admin (403 si non-admin) — `tests/test_admin_auth.py` (nouveau), `api/routers/admin_*.py` — ~2h
- [ ] Deploiement E2E compose prod : tester `docker-compose.prod.yml` + `scripts/deploy.sh` de bout en bout en local — `docker-compose.prod.yml`, `scripts/deploy.sh`, `DEPLOY.md` — ~4h
- [ ] TLS bout en bout : tester la terminaison TLS avec certificat (necessite un vrai domaine ou mkcert) — `nginx/nginx.conf`, `docker-compose.prod.yml` — ~2h
- [ ] Separer les configs DB session API vs Celery : le statement timeout 30s est trop court pour les taches longues — `db/session.py:15` — ~1h

---

## P2 Important

> Architecture, fiabilite, fonctionnalites metier manquantes.

- [ ] Refactorer les repositories pour retirer les `db.commit()` (19 fichiers) — les services doivent gerer le commit, repos utilisent `db.flush()` — `repositories/*.py` (19 fichiers) — ~8h
- [ ] Remplacer les retours `dict` par des schemas Pydantic dans `pec_preparation.py:206,289` — `api/routers/pec_preparation.py`, `domain/schemas/pec_preparation.py` — ~1h
- [ ] Verifier que TOUS les endpoints utilisent des schemas Pydantic pour input ET output (audit systematique) — `api/routers/*.py` — ~3h
- [ ] Celery : toutes les taches qui creent des enregistrements doivent verifier l'existence AVANT insert (idempotence complete) — `tasks/*.py` — ~3h
- [ ] Deleguer l'envoi d'email synchrone dans `reminder_tasks.py` vers une tache email separee — `tasks/reminder_tasks.py`, `tasks/email_tasks.py` — ~2h
- [ ] Batch PEC submission : soumettre plusieurs PEC en une fois — `services/pec_service.py`, `api/routers/pec.py`, `domain/schemas/pec.py` — ~6h
- [ ] Tracking reponse mutuelle avec relance automatique — `services/pec_service.py`, `tasks/pec_tasks.py` (nouveau) — ~6h
- [ ] Tester : deconnexion, expiration token, acces non autorise (flux cookie httpOnly) — `tests/test_auth_cookie.py` (nouveau), `middleware.ts` — ~2h

---

## P3 Moderate

> Qualite code, frontend, ameliorations UX.

- [ ] Extraire les sections formulaire de `clients/[id]/pec-preparation/[prepId]/page.tsx` (650 lignes) — `apps/web/src/app/clients/[id]/pec-preparation/[prepId]/` — ~2h
- [ ] Extraire les panneaux et tableaux de `rapprochement/page.tsx` (390 lignes) — `apps/web/src/app/rapprochement/` — ~1h30
- [ ] Remplacer les `window.confirm()` par le composant `ConfirmDialog` existant — grep `window.confirm` dans `apps/web/src/` — ~1h
- [ ] Remplacer les `window.open()` par des liens Next.js ou des handlers propres — grep `window.open` dans `apps/web/src/` — ~1h
- [ ] Ajouter un type TypeScript strict pour chaque reponse admin — `apps/web/src/lib/types/admin.ts` (nouveau) — ~2h
- [ ] Tester visuellement l'ecran admin apres corrections des contrats front/back — `apps/web/src/app/admin/` — ~1h
- [ ] `batch_tasks.py` : mise a jour du statut en BDD tous les 100 items (progression visible) — `tasks/batch_tasks.py` — ~1h
- [ ] Verifier les index DB sur les colonnes frequemment filtrees : `customer_id`, `created_at`, `status` — `models/*.py`, migration Alembic — ~2h

---

## P4 Low

> Monitoring, observabilite — important pour la production a moyen terme.

- [ ] Ajouter un endpoint `/metrics` Prometheus-compatible — `api/routers/metrics.py` (nouveau), `main.py` — ~4h
- [ ] Monitorer les temps de reponse des endpoints critiques (middleware ou Prometheus histogram) — `core/metrics.py` (nouveau) — ~2h
- [ ] Monitorer la taille de la queue Celery (Flower ou endpoint custom) — `tasks/monitoring.py` (nouveau) — ~2h
- [ ] Ajouter des alertes sur les erreurs 5xx en production (Sentry rules ou webhook) — configuration Sentry/alerting — ~1h
- [ ] Slow query logging PostgreSQL (log_min_duration_statement) — `docker-compose.prod.yml`, `postgresql.conf` — ~30min

---

## P5 Nice-to-have

> Validation avancee, tests de charge, ameliorations progressives.

- [ ] Tester la sync avec un jeu de donnees Cosium realiste (necessite acces live) — `services/erp_sync_service.py` — ~4h
- [ ] Verifier le switch tenant : les donnees changent bien apres switch cote frontend — `apps/web/src/`, `api/routers/auth.py` — ~2h
- [ ] Tester avec 2+ tenants actifs en parallele (concurrence sync + queries) — `tests/test_multi_tenant_parallel.py` (nouveau) — ~4h
- [ ] Verifier que la sync ne cree pas de N+1 queries (SQLAlchemy eager loading) — `services/erp_sync_*.py` — ~2h
- [ ] Profiler les endpoints les plus lents (cProfile ou py-spy) — tous les routers — ~2h
- [ ] Tester un cycle complet backup -> restore -> verification donnees — `scripts/backup_db.sh`, `scripts/restore_db.sh` — ~2h
- [ ] CI : ajouter une verification `.gitignore` (pas d'artefacts commites) — `.github/workflows/ci.yml` — ~30min

---

## Suivi

| Priorite | Description | Taches | Effort estime |
|----------|-------------|--------|---------------|
| P1 Critical | Securite, deploiement, isolation | 6 | ~16h |
| P2 Important | Architecture, fiabilite, PEC | 8 | ~31h |
| P3 Moderate | Qualite code, frontend, UX | 8 | ~11h30 |
| P4 Low | Monitoring, observabilite | 5 | ~9h30 |
| P5 Nice-to-have | Tests avances, performance | 7 | ~16h30 |
| **TOTAL** | | **34** | **~85h** |
