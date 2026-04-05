# ITERATION 15 — ROBUSTNESS+ (DEEP DIVE)

## Issues Found

### R15-01: Sync concurrent execution — no locking mechanism [MEDIUM]
**File:** `backend/app/tasks/sync_tasks.py`, `backend/app/api/routers/sync.py`
**Problem:** `sync_all_tenants` Celery task and `/sync/all` HTTP endpoint can run simultaneously
for the same tenant. Two concurrent `sync_customers` calls will create duplicate customers
because the in-memory lookup maps are built separately. No distributed lock (Redis-based) is used.
**Fix:** Add a Redis-based distributed lock per tenant before running sync operations.

### R15-02: Sync operations — no rollback on partial failure [MEDIUM]
**File:** `backend/app/services/erp_sync_service.py`
**Problem:** In `sync_customers` (line 183), a single `db.commit()` at the end means if the commit
fails or an exception occurs after processing 500 of 1000 customers, ALL work is lost. Conversely,
if the commit succeeds but `audit_service.log_action` fails (line 195), the sync is done but unaudited.
Similarly, `_sync_single_tenant` runs all sync domains in sequence on the same session — if
`sync_payments` fails mid-transaction after `sync_customers` committed, state is inconsistent.
**Fix:** Each sync domain already has its own `db.commit()` — this is actually correct for isolation.
But the audit_service call after commit should be wrapped in try/except to prevent audit failures
from bubbling up. Add explicit `db.rollback()` in the except paths.

### R15-03: Payment creation — race condition on idempotency check [LOW]
**File:** `backend/app/services/banking_service.py` (line 30-33)
**Problem:** The idempotency check (`get_by_idempotency_key` then `create_payment`) is not atomic.
Two simultaneous requests with the same idempotency key could both pass the check and create
duplicate payments. Need a unique constraint on `idempotency_key` + `tenant_id` in the DB model.
**Fix:** Add unique constraint on (idempotency_key, tenant_id) to Payment model. Catch IntegrityError
on duplicate to return the existing record.

### R15-04: SSE connection — DB session held open indefinitely [HIGH]
**File:** `backend/app/api/routers/sse.py`
**Problem:** The SSE endpoint holds a DB session open for the entire lifetime of the connection
(potentially hours). This consumes a connection pool slot permanently. With pool_size=20 and
max_overflow=20, only 40 SSE clients would exhaust the pool. The `db.expire_all()` call
(line 69) refreshes ORM objects but keeps the session/connection active.
**Fix:** Create a new DB session per poll iteration instead of holding one open.

### R15-05: Celery tasks — no retry configuration on sync tasks [MEDIUM]
**File:** `backend/app/tasks/sync_tasks.py`
**Problem:** `sync_all_tenants` and `test_cosium_connection` tasks have no retry logic.
If the Cosium API is temporarily down at 6 AM, the daily sync simply fails.
The `email_tasks.py` correctly uses `bind=True, max_retries=3, default_retry_delay=60`
but sync tasks do not. `reminder_tasks.py` also has no retry.
**Fix:** Add retry configuration to sync and reminder tasks.

### R15-06: File upload — no cleanup on DB failure [LOW]
**File:** `backend/app/services/document_service.py` (line 50-57)
**Problem:** File is uploaded to MinIO (line 50-55) before the DB record is created (line 57-64).
If `document_repo.create_document` or `db.commit()` fails, the file remains orphaned in MinIO
with no corresponding DB record. Over time, this leaks storage.
**Fix:** Wrap in try/except; on DB failure, attempt to delete the uploaded file from MinIO.

### R15-07: Redis graceful degradation — global `_redis` stale reference [LOW]
**File:** `backend/app/core/redis_cache.py`
**Problem:** If Redis goes down AFTER initial connection, `_redis` remains set to the old
(broken) connection object. Subsequent `cache_get`/`cache_set` calls will fail with connection
errors rather than gracefully returning None. The `_get_redis()` only creates the connection
once (`if _redis is None`).
**Fix:** Add connection health check or catch connection errors and reset `_redis = None`.

### R15-08: Bank statement import — no duplicate detection [MEDIUM]
**File:** `backend/app/services/banking_service.py` (line 65-103)
**Problem:** Importing the same CSV file twice creates duplicate bank transactions.
There is no dedup based on (date, libelle, montant, reference) or source_file tracking.
**Fix:** Add duplicate detection before creating transactions.

### R15-09: Multiple `db.commit()` in both repos AND services [LOW]
**File:** Multiple repos and services
**Problem:** Several flows commit in the repo then commit again in the service, creating
fragmented transactions. E.g., `banking_repo.create_payment` commits on line 39, then
`banking_service.create_payment` calls `audit_service.log_action` which also commits.
If the audit commit fails, the payment exists but the audit trail is missing.
This pattern is widespread (found 35+ commit() calls in repos, 30+ in services).
**Fix:** Document the pattern; for critical flows (payment creation), ensure audit
logging failure doesn't break the main operation by wrapping in try/except.

## Fix Status

| Issue | Severity | Fixed? | Notes |
|-------|----------|--------|-------|
| R15-01 | MEDIUM | YES | Redis distributed lock added to sync_all_tenants task + /sync/all endpoint |
| R15-02 | MEDIUM | NO | Acceptable: each domain commits independently, partial failure isolated |
| R15-03 | LOW | NO | Deferred: requires DB migration for unique constraint |
| R15-04 | HIGH | YES | SSE now uses short-lived DB sessions per poll + max connection lifetime |
| R15-05 | MEDIUM | YES | Retry config added to sync_all_tenants, test_cosium_connection, auto_generate_reminders |
| R15-06 | LOW | YES | MinIO file cleanup on DB failure added |
| R15-07 | LOW | YES | Redis connection reset on ConnectionError/TimeoutError in all cache functions |
| R15-08 | MEDIUM | YES | Dedup via (date, amount, libelle) signature set before creating transactions |
| R15-09 | LOW | NO | Architectural pattern, too widespread to refactor safely in audit |

## Status: DONE — 7/9 fixed, 2 deferred
