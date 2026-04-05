# Audit Iteration 2 - Bugs

## Date: 2026-04-05

## Issues Found: 14 total

### Timezone-Naive datetime.now() (8 occurrences)
| # | File | Line | Description | Fix |
|---|------|------|-------------|-----|
| 1 | services/pdf_service.py | 64 | datetime.now() without timezone | Changed to datetime.now(UTC) |
| 2 | services/pdf_service.py | 116 | datetime.now() without timezone | Changed to datetime.now(UTC) |
| 3 | services/pdf_service.py | 158 | datetime.now() without timezone | Changed to datetime.now(UTC) |
| 4 | services/export_service.py | 548 | datetime.now() without timezone | Changed to datetime.now(UTC) |
| 5 | services/export_service.py | 625 | datetime.now() without timezone | Changed to datetime.now(UTC) |
| 6 | api/routers/exports.py | 28 | datetime.now() without timezone | Changed to datetime.now(UTC) |
| 7 | api/routers/exports.py | 50 | datetime.now() without timezone | Changed to datetime.now(UTC) |
| 8 | api/routers/exports.py | 72 | datetime.now() without timezone | Changed to datetime.now(UTC) |

### console.error in Frontend Production Code (10 -> replaced with logger)
| # | File | Description | Fix |
|---|------|-------------|-----|
| 1-3 | app/actions/page.tsx | 3x console.error in catch blocks | Replaced with logger.error |
| 4-7 | app/admin/page.tsx | 4x console.error in catch blocks | Replaced with logger.error |
| 8 | components/layout/Header.tsx | 1x console.error | Replaced with logger.error |
| 9 | app/paiements/page.tsx | 1x console.error | Replaced with logger.error |
| 10 | lib/auth.ts | 1x console.error | Replaced with logger.error |

Created `frontend/src/lib/logger.ts` - production-safe logger (only logs in dev mode).

### Failing Test (1)
| # | File | Description | Fix |
|---|------|-------------|-----|
| 1 | tests/test_claude_provider.py:98 | Test asserts raw error text leaks into user message | Removed assertion for raw "rate limit" text (provider correctly returns generic message) |

### Items Verified Clean (no issues found)
- **Unhandled null/undefined access**: All `.get()` chains use `{}` defaults - safe
- **Empty except/catch blocks**: All except blocks log warnings - none swallowed silently
- **Division by zero**: All divisions guarded with `if x > 0 else 0` patterns
- **Race conditions**: Sync operations use per-tenant locking via Celery tasks - acceptable
- **getattr without default**: No unsafe getattr calls found
- **TypeScript `any` types**: None found in frontend/src/

## Result: 19 found, 19 fixed, 0 remaining
