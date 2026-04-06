# ITERATION 25 - ROBUSTNESS++ (Ultra-strict)

## Issues Found & Fixed

### 1. Celery task `sync_all_tenants` - no rollback on per-tenant failure
- **File**: `backend/app/tasks/sync_tasks.py`, line ~58
- **Severity**: HIGH
- **Problem**: If `_sync_single_tenant()` failed mid-transaction, the DB session was left in a broken state. The next tenant in the loop would encounter `InvalidRequestError` because the session had a pending failed transaction.
- **Fix**: Added `db.rollback()` in the `except` block for each tenant sync failure.

### 2. Celery task `extract_document` - no rollback on failure
- **File**: `backend/app/tasks/extraction_tasks.py`, line ~31
- **Severity**: MEDIUM
- **Problem**: On extraction failure, the session was closed without rollback, which could leave uncommitted changes from partial operations.
- **Fix**: Added `db.rollback()` before retry.

### 3. Celery task `extract_all_client_documents` - no rollback per-document
- **File**: `backend/app/tasks/extraction_tasks.py`, line ~76
- **Severity**: MEDIUM
- **Problem**: Individual document extraction failures in the batch loop didn't rollback, corrupting the session for subsequent documents.
- **Fix**: Added `db.rollback()` in per-document except block.

### 4. SSE connection handling - ACCEPTABLE
- **Analysis**: SSE uses `MAX_CONNECTION_SECONDS = 300` with auto-reconnect, short-lived DB sessions per poll (5s interval), and heartbeat every 30s. With 100 concurrent connections, this creates 100 coroutines but each only holds a DB session for milliseconds per poll cycle. The pool_size=20 with max_overflow=20 in session.py handles this well. No fix needed.

### 5. Redis reconnection - ACCEPTABLE
- **Analysis**: `redis_cache.py` resets `_redis = None` on connection errors, so the next call retries connection. All Redis operations have try/except with graceful fallback. No fix needed.

### 6. MinIO down resilience - ACCEPTABLE
- **Analysis**: `main.py` startup catches MinIO bucket init failure and logs it without crashing. Document operations raise `BusinessError` with clear messages. The app works fine minus file features. No fix needed.
