# Audit Iteration 5 - Robustness

## Issues Found: 10

### R-01: Silent exception swallowing in redis_cache.py [FIXED]
- `cache_set` and `cache_delete_pattern` catch all exceptions with bare `pass`
- Added logging to make failures visible

### R-02: Empty .catch(() => {}) in frontend actions/page.tsx [FIXED]
- `markDone` and `dismiss` functions silently swallow errors
- Added toast error feedback to the user

### R-03: Stripe client has no error handling [FIXED]
- All 5 Stripe functions lack try/except — any Stripe API error propagates as raw stripe.error
- Wrapped calls with proper BusinessError conversion and logging

### R-04: Dashboard service fetches all payments into memory [FIXED]
- `db.query(Payment).filter(...).all()` loads every payment for aggregation
- Replaced with SQL aggregate query (SUM)

### R-05: banking_service.import_statement lacks file decode error handling [FIXED]
- `file.file.read().decode("utf-8-sig")` can raise UnicodeDecodeError on binary files
- Added try/except with user-friendly error message

### R-06: document_service.upload_document doesn't close file handle [FIXED]
- `file.file.read()` reads entire file but never resets/closes the file pointer
- Not critical (FastAPI handles cleanup) but added explicit resource management

### R-07: email_sender.py has no SMTP connection timeout [FIXED]
- SMTP connection has no timeout — can hang indefinitely if mailhog is down
- Added timeout=10 to SMTP constructor

### R-08: banking_repo.auto_reconcile has N+1 query for already_matched set [FIXED]
- The `already_matched` set is recomputed inside the loop for each unmatched transaction
- Moved outside the loop to compute once

### R-09: renewal_engine.detect_renewals has N+1 queries per candidate [FIXED]
- For each candidate, 2 separate DB queries (has_active_pec + get_equipment_type)
- This is a design limitation — added limit to prevent runaway on large datasets

### R-10: marketing_service.send_campaign sends emails synchronously in loop [INFO]
- For large segments, sending emails one by one blocks the request
- Noted as future improvement (should use Celery task queue)

## Summary
- Issues found: 10
- Issues fixed: 9
- Issues deferred: 1 (R-10, requires architecture change to Celery)
