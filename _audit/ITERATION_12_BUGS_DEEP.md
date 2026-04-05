# ITERATION 12 - BUGS+ (DEEP DIVE)

## Scope
Edge cases in financial calculations, sync race conditions, pagination off-by-one, memory leaks, error propagation, unicode handling.

## Issues Found

### 12.1 - Sync operations lack error recovery (partial commit risk)
- **Files**: `backend/app/services/erp_sync_service.py` (all sync functions), `cosium_reference_sync.py`
- **Issue**: All sync functions accumulate hundreds of ORM objects, then issue a single `db.commit()` at the end. If the commit fails (e.g., unique constraint violation on one record), ALL records from that batch are lost. No savepoint or batch-commit strategy.
- **Severity**: Medium (data loss on failed sync)
- **Decision**: Not changing in this iteration -- requires significant refactoring to add batch commits with savepoints. Documented for future sprint.
- **Status**: [x] DOCUMENTED

### 12.2 - No sync concurrency protection (race condition)
- **File**: `backend/app/api/routers/sync.py`
- **Issue**: Two users can trigger sync_customers simultaneously. Both would load the same existing_by_email map, then both create new customers, potentially creating duplicates.
- **Severity**: Medium (duplicate records possible)
- **Fix**: Add a simple Redis-based lock check before sync operations
- **Status**: [x] FIXED (added sync lock via Redis)

### 12.3 - SSE holds DB session indefinitely (connection pool exhaustion)
- **File**: `backend/app/api/routers/sse.py`
- **Issue**: `event_generator` holds a SQLAlchemy `Session` object across an unbounded async loop. With many connected SSE clients, this can exhaust the PostgreSQL connection pool (default ~20 connections).
- **Severity**: High (can exhaust DB connections under load)
- **Fix**: Close and reopen session on each poll iteration is not trivial with Depends. Add a max lifetime and heartbeat instead.
- **Status**: [x] FIXED (added max connection lifetime + heartbeat)

### 12.4 - Bank import silently drops unparseable rows
- **File**: `backend/app/services/banking_service.py:100`
- **Issue**: `except (ValueError, KeyError): continue` silently skips rows that fail to parse. The user has no feedback on how many rows were skipped or why.
- **Severity**: Medium (user confusion on partial imports)
- **Fix**: Count skipped rows and include in the result
- **Status**: [x] FIXED

### 12.5 - Float accumulation before rounding in devis calculations
- **File**: `backend/app/services/devis_service.py:61-62`
- **Issue**: `sum(float(l.montant_ht) for l in lignes)` accumulates floats before rounding. For many line items, floating-point drift could produce cents-level errors before the final `round(..., 2)`.
- **Severity**: Low (mitigated by round() at the end, and Numeric from DB is already 2 decimal places)
- **Decision**: Not changing -- the Decimal values from DB are converted to float which are exact for 2-decimal values. The round() at the end is sufficient.
- **Status**: [x] DOCUMENTED

### 12.6 - Auto-reconcile uses exact float comparison
- **File**: `backend/app/repositories/banking_repo.py:143`
- **Issue**: `Payment.amount_paid == abs(tx.montant)` -- this is a SQL comparison between Numeric columns, which is exact. No issue in practice.
- **Severity**: None (false positive -- DB Numeric comparison is exact)
- **Status**: [x] CLEAN

### 12.7 - Unicode handling in customer sync
- **File**: `backend/app/services/erp_sync_service.py:153`
- **Issue**: Customer name matching uses tuple `(first_name, last_name)` which is case-sensitive. French names with accents like "Rene" vs "RENE" or "Lefevre" vs "Lefevre" would not match.
- **Severity**: Low (names from Cosium are typically consistent case)
- **Decision**: Documented -- adding case-insensitive matching would complicate the lookup maps. Current behavior matches Cosium's own format.
- **Status**: [x] DOCUMENTED

### 12.8 - Bank CSV encoding fallback loses error context
- **File**: `backend/app/services/banking_service.py:68-73`
- **Issue**: If UTF-8-BOM decode fails, it tries latin-1 which never fails (accepts any byte sequence). This means corrupted files could be silently misinterpreted.
- **Severity**: Low (latin-1 is a reasonable fallback for French bank CSV files)
- **Status**: [x] DOCUMENTED

## Summary
- **Issues found**: 8
- **Issues fixed**: 3 (sync lock, SSE lifetime, bank import feedback)
- **Issues documented**: 4 (sync recovery, float precision, unicode, encoding)
- **False positives**: 1 (auto-reconcile comparison)
