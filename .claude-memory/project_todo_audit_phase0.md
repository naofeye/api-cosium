---
name: Session 2026-04-17 — CI debloquee + 15 items P1 fermes
description: Session marathon : CI rouge depuis 5 jours rétablie (0→965 tests verts), 15 items P1 TODO fermés, 25+ commits. Bilan pour reprendre.
type: project
originSessionId: 2c57be34-b659-475a-8d32-5ded8ad85991
---
**Fichier de référence** : `TODO.md` à la racine. Plus aucun autre TODO.

**État à la fin de session (commit `8c494dd`)** :
- CI : 🟢 green stable (CodeQL + CI)
- Tests : **965 passed, 1 skipped, 2 deselected**
- Dette tests préexistants : **0** (49 → 0)
- Production-ready env test confirmé

**Items P1 fermés (15)** :
1. Content-Disposition RFC 5987 — helper `core/http.py` + migration 10 routers
2. Audit trail DELETE client `force=True` + restreint à admin (clients.py + client_service.py)
3. Baseline coverage CI alignée à 45% (pyproject + ci.yml)
4. `blacklist_access_token` log warning (non silent)
5. MFA/TOTP backup codes : colonne `User.totp_backup_codes_hash_json`, migration `w8x9y0z1a2b3`, service (`generate_backup_codes`, `count_remaining_backup_codes`, `_consume_backup_code_inplace`), `verify_login_code` étendu, 2 endpoints, schema `LoginRequest.totp_code` souple, 18 tests
6. MFA forcée admin : colonne `Tenant.require_admin_mfa`, migration `x9y0z1a2b3c4`, helper `_user_must_have_mfa`, refuse login `MFA_SETUP_REQUIRED`, router `admin_tenant_security.py`, 8 tests
7. Mass-assignment whitelist onboarding_repo : `_ORG_WRITABLE`, `_TENANT_WRITABLE`, `_USER_WRITABLE` + `_filter()`, 4 tests
8. IDOR avatar client : faux positif documenté (tenant_id filtré + storage_key inclut tenant)
9. Rate limit local ≠ test : déjà OK dans code, vérifié
10. Réseau Docker prod isolé : 2 networks (`optiflow_public`, `optiflow_internal` avec `internal: true`) dans `docker-compose.prod.yml`, defense-in-depth
11. Blacklist Sentry alerting : helper `core/sentry_helpers.py::report_incident_to_sentry` + 3 callsites security, refacto security.py
12. Log rotation prod : ancre YAML `x-default-logging` dans compose prod, json-file 50m × 5, 8 services
13. Alerting sync Cosium échec : 4 callsites dans `tasks/sync_tasks.py` (tenant/partial/domain/bulk), 4 tests sentry helpers
14. Skip list tests préexistants : `conftest.py::_PREEXISTING_BROKEN_TESTS` (documenté, puis tous débloqués batch par batch)
15. Smoke tests services (partiel) : `analytics_cosium_service` (4), `client_merge_service` (3), `pec_consolidation_service` (1) dans `tests/test_services_smoke.py`

**Bugs réels prod corrigés (non-tests)** :
- Migration `q2r3s4t5u6v7` : 3 indexes doublons retirés
- Migration `v7w8x9y0z1a2` : transaction PG avortée → SQL brut `DROP CONSTRAINT IF EXISTS` + `cosium_third_party_payments.customer_id` inexistant retiré
- `erp_sync_service.sync_customers` : catch `SQLAlchemyError` → `Exception` générique
- `cosium_document_sync` : catch élargi
- `ocr_service.extract_text_from_pdf` : catch élargi (PDF corrompu = fallback OCR, pas crash)
- `onboarding_service.connect_cosium` : catch élargi (échec auth → BusinessError 400, pas 500)
- Bug hérité passe 8 : `next/dynamic` 2e arg doit être object literal dans `ClientTabs.tsx`
- 9 erreurs ruff accumulées (F823, UP038, I001 × 5, F401)

**Items P1 restants pour prochaine session** :
- Smoke tests 7 services restants (`marketing_service`, `consolidation_service`, `client_360_finance`, `client_360_documents`, `batch_processing_service`, `erp_sync_invoices`, `erp_sync_payments`)
- Tests E2E Playwright frontend (long setup)
- Tests intégration Cosium respx (refacto mock HTTP)
- pip-audit strict (upgrade starlette chain via FastAPI)
- `CREATE TABLE IF NOT EXISTS` refactor Alembic `h3b4c5d6e7f8` (risqué, 20 tables)
- MFA frontend UI (générer codes, afficher, download)

**Points saillants pour reprendre** :
- Helper `core/sentry_helpers.py::report_incident_to_sentry(exc, tag, category=, **context)` réutilisable pour toute nouvelle capture
- Pattern catch élargi avec `# noqa: BLE001` + log `error_type` appliqué partout (précédent trop narrow)
- Pattern mass-assignment : whitelist `frozenset` + helper `_filter()` côté repo
- Tests : `conftest.py` mocke `storage` (MinIO) et `send_email_async.delay` (Celery/Redis) en autouse
- Backup codes accessibles via `POST /auth/mfa/backup-codes/generate` (retour clair 1× seule fois) + `GET /auth/mfa/backup-codes/count`
- Flag MFA enforcement : `PATCH /api/v1/admin/tenant/security {"require_admin_mfa": true}` (role admin, audité)
