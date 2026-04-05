# ITERATION 13 — SECURITY+ (DEEP DIVE)

## Issues Found

### SEC-13-01 [HIGH] IDOR: notification mark_read missing user_id check
- **File**: `backend/app/repositories/notification_repo.py` (mark_read)
- **File**: `backend/app/services/notification_service.py` (mark_read)
- **File**: `backend/app/api/routers/notifications.py` (mark_read endpoint)
- **Issue**: mark_read only filters by tenant_id + notification_id, not user_id. A user in the same tenant can mark another user's notifications as read.
- **Fix**: Pass user_id through the chain and add it to the WHERE clause.

### SEC-13-02 [MEDIUM] Missing role enforcement on sensitive financial endpoints
- **File**: `backend/app/api/routers/banking.py`
- **Issue**: All banking endpoints (create payment, import statement, reconcile, manual match) use `get_tenant_context` — any authenticated user with any role (including viewer) can create payments and import bank statements.
- **Fix**: Restrict create/import/reconcile to admin+manager, read-only to all roles.

### SEC-13-03 [MEDIUM] Missing role enforcement on marketing campaign send
- **File**: `backend/app/api/routers/marketing.py`
- **Issue**: Campaign send uses `get_tenant_context` — any role can send mass emails.
- **Fix**: Restrict create/send to admin+manager.

### SEC-13-04 [MEDIUM] Missing role enforcement on client delete
- **File**: `backend/app/api/routers/clients.py`
- **Issue**: DELETE /clients/{id} uses `get_tenant_context` — any role can delete clients.
- **Fix**: Restrict delete to admin+manager.

### SEC-13-05 [LOW] Missing role enforcement on exports
- **File**: `backend/app/api/routers/exports.py`
- **Issue**: FEC export and balance exports use `get_tenant_context` — any role can export all data.
- **Fix**: Restrict to admin+manager.

### SEC-13-06 [LOW] Content-Disposition header injection in document download
- **File**: `backend/app/services/document_service.py`
- **Issue**: Filename from DB is used directly in Content-Disposition header without sanitizing quotes/newlines.
- **Fix**: Sanitize filename to remove control characters and quotes.

### SEC-13-07 [LOW] Bank statement import has no file extension check
- **File**: `backend/app/api/routers/banking.py` + `backend/app/services/banking_service.py`
- **Issue**: import_statement accepts any file, no .csv extension check (unlike client CSV import which validates).
- **Fix**: Add .csv extension validation.

## Items Verified OK

- JWT: Expiry enforced via PyJWT decode, startup check for default secret in prod
- Bcrypt: Proper passlib usage, password_hash never in response schemas
- CORS: Origins from settings, credentials allowed, not wildcard
- File upload: Extension + MIME whitelist + size limit in document_service
- Mass assignment: No tenant_id/role in create schemas (Pydantic blocks extra fields by default)
- Cosium client: Only get() + authenticate(), no write methods
- Security headers: X-Content-Type-Options, X-Frame-Options, HSTS, etc.
- Rate limiting: Login, signup, GDPR, imports all rate-limited
- Error handling: Generic 500 handler hides internal details
- Export entity_type: Whitelisted via ENTITY_CONFIGS dict
- All repositories filter by tenant_id (no cross-tenant data leak)
- Password reset: Token hashed with SHA-256, single-use, 1h expiry, email not revealed
- Refresh tokens: Properly revoked on password change/logout
