# ITERATION 22 - BUGS++ Audit

## Issues Found

### 22-1 [MEDIUM] Timezone inconsistency: client_repo.delete() and client_mutuelle_repo.update() use aware datetime
- File: backend/app/repositories/client_repo.py line 70 - datetime.now(UTC) produces aware datetime
- File: backend/app/repositories/client_mutuelle_repo.py line 74 - same issue
- DB columns are DateTime (naive). PostgreSQL will strip tzinfo, but reads come back naive.
- Should use datetime.now(UTC).replace(tzinfo=None) for consistency
- Severity: Medium (works in PostgreSQL but could cause comparison bugs)
- FIX: Add .replace(tzinfo=None) to both

### 22-2 [OK] Division by zero in percentage calculations
- All division operations checked - all have proper guards (total > 0 checks, or iterate over non-empty lists)
- analytics_service.py, consolidation_service.py, admin_health.py all safe

### 22-3 [OK] Edge case: 0 invoices/prescriptions for client
- client_360_service builds empty lists; frontend handles empty arrays
- UI won't crash on empty data
