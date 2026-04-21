---
name: Session 2026-04-18 — 14 commits refacto + quasi tous P1 fermés
description: Suite session 2026-04-17. Série 7 splits fichiers >400 L + 7 P1 fermés + 5 P2 fermés. CI verte apres follow-up 2026-04-19, main à `6e000e3` (branche main supprimee 2026-04-19 — cf. project_branch_unified_main.md).
type: project
originSessionId: 78e8037f-0ea8-4de6-a636-c3826a097607
---
**Continuité** : session suivant 2026-04-17 (voir `project_todo_audit_phase0.md`).

**État à la fin de la session (commit `d7394db`) — CI ROUGE** (découvert 2026-04-19) :
- Les 3 derniers splits (sync_tasks, TabResume, TabCosiumDocuments) utilisaient tous `from .` / `from ._module` → violait `test_no_relative_imports_in_app` (charte CLAUDE.md).
- Split de `sync.py` avait déplacé `acquire_lock` vers `_helpers.py`, cassant les 2 `@patch("app.api.routers.sync.acquire_lock")` de `test_sync_transactions.py`.
- Fix appliqué 2026-04-19 (commits `a37b109` + `6e000e3`) : imports absolus + patch repointé vers `_helpers.acquire_lock`. CI 9/9 + CodeQL verts.

**État à la fin (commit `6e000e3`, 2026-04-19)** :
- CI : 🟢 verte (CI + CodeQL)
- Tests : 160/160 vitest + 1015 pytest passed verts
- Pre-commit hooks installés et actifs sur chaque commit (scope défensif)

**P1 fermés cette session (7)** :
1. Banking CSV magic bytes (`_validate_csv_signature` + 4 tests)
2. Harmoniser `max_length=100` search params routers Cosium (13 occurrences)
3. Smoke tests 7 services restants (`test_services_smoke_extra.py`, 29 tests)
4. Tests intégration Cosium respx (`test_cosium_client_respx.py`, 20 tests, `respx==0.23.1`)
5. MFA frontend UI complet (`MfaSection` + login flow + admin toggle `require_admin_mfa` + `qrcode.react`)
6. Migration `CREATE TABLE IF NOT EXISTS` : accepté comme bootstrap via **ADR 0007**
7. 49 tests préexistants cassés (dict `_PREEXISTING_BROKEN_TESTS` vide, CI verte)
8. pip-audit strict : déjà en place, cloturé dans TODO

**P2 fermés cette session (5+)** :
- Zod schemas facture/rapprochement/relance (schemas + tests + intégration devis/rapprochement)
- Pre-commit hooks activés (scope défensif)
- Celery beat schedule volatile (volume nommé)
- Logging analytics Cosium (`logger.info` avec `tenant_id + elapsed_ms`)
- `web.depends_on api.service_healthy` prod
- Lazy-loading `dynamic()` étendu aux tabs relances + cases
- Frontend P2 quick fixes (Escape modal, isNaN guards, double-clic relances)
- 4 logs silent fallbacks (main health, rate_limiter, redis_cache, auth_service lockout)

**Série fichiers >400 L : 7/7 FERMÉS** ✅
- Backend : `main.py` (432→228) / `cosium_reference/` (401→package 4 modules) / `sync/` (420→package 5 + orchestration `erp_sync_service.sync_all`) / `analytics_cosium_extras/` (481→package 4) / `sync_tasks/` (440→package 4)
- Frontend : `TabResume.tsx` (560→98 + `_resume/` 7 fichiers) / `TabCosiumDocuments.tsx` (432→173 + `_cosium_documents/` 4 fichiers)

**Tentative Playwright E2E abandonnée** : setup livré + workflow_dispatch uniquement. 6 fix successifs pour cookies cross-origin / hydration React 19 / GET natif submit → revert propre. Voir `feedback_tunnel_avoid.md`.

**P1 restants (1 item non-critique)** : splash screens iOS PWA.
**DIFFERE-PROD (5 items)** : TLS, server_name nginx, passwords prod BDD/MinIO/Grafana, rotation creds Cosium, Sentry DSN prod.
**P2 restants** : ~23 items (ocr_service split 383 L, seed_demo → tests/factories, `except Exception` bare 11 restants, RSC-first, Grafana dashboards, ESLint strict, etc.).

**Patterns acquis** :
- **Split Python** : transformer `xxx.py` en package `xxx/` avec `_sub.py` privés + `__init__.py` re-export pour préserver imports publics. Validé 5 fois backend.
- **Split React** : sous-dossier `_<domain>/` avec types.ts + shared.tsx + composants spécifiques. Validé 2 fois frontend.
- **Celery tasks** : `name="app.tasks.xxx"` hardcodé dans chaque `@task(...)` rend le refacto trivial (routing + beat schedules par name, pas par module path).
- **Harness Write retry** : sur fichiers lus en plusieurs Read, le Write peut échouer "File has not been read yet" → re-Read une ligne pour déclencher refresh, puis re-Write.

**Repère architecture** : `docs/adr/0007-alembic-bootstrap-migration-accepted.md` acte la règle : aucune future migration ne doit utiliser `CREATE TABLE IF NOT EXISTS`. Voir aussi `feedback_adr_0007_migration_rule.md`.
