# Audit Iteration 3 - SECURITY

## Issues Found: 7

### S1 - FIXED - Exception details leaked to users in AI provider
- File: `backend/app/integrations/ai/claude_provider.py:69`
- Issue: `str(e)` returned in user-visible text: `f"[Erreur IA] {str(e)}"`
- Fix: Replaced with generic user-friendly message

### S2 - FIXED - Raw exception in Cosium connection test response
- File: `backend/app/api/routers/admin_health.py:152`
- Issue: `error=f"Erreur de connexion: {error_msg[:100]}"` exposes internal error to API response
- Fix: Replaced with generic connection error message

### S3 - FIXED - Raw exception in BusinessError (onboarding connect)
- File: `backend/app/services/onboarding_service.py:128`
- Issue: `BusinessError(f"Connexion ERP echouee : {e}")` could leak internal details
- Fix: Replaced with generic message, original error still in logs

### S4 - FIXED - Raw exception in BusinessError (onboarding sync)
- File: `backend/app/services/onboarding_service.py:157`
- Issue: `BusinessError(f"Synchronisation echouee : {e}")` could leak internal details
- Fix: Replaced with generic message, original error still in logs

### S5 - FIXED - Raw str(e) in sync API response
- File: `backend/app/api/routers/sync.py:163,172`
- Issue: Exception messages returned directly in dict response to API caller
- Fix: Log the error, return generic messages to user

### S6 - ACCEPTED - Hardcoded seed password
- File: `backend/app/seed.py:49`
- Issue: `hash_password("Admin123")` hardcoded for dev seed
- Status: Acceptable for development seed data only

### S7 - MITIGATED - Default JWT secret
- File: `backend/app/core/config.py:12`
- Issue: `jwt_secret: str = "change-me-super-secret"` as default
- Status: Already mitigated by startup check in main.py (line 140) that blocks production start

### Verified OK
- No SQL injection risks found (no raw SQL with f-strings/format)
- CORS not wildcard (uses settings.cors_origins split by comma)
- .gitignore covers .env, __pycache__, .next, node_modules
- No password_hash exposed in any Pydantic response schema
- All endpoints use get_tenant_context or require_tenant_role (both enforce JWT auth)
- Auth endpoints (login, refresh, forgot-password, reset-password, logout) correctly unauthenticated
- Health check endpoint intentionally unauthenticated (load balancer)
- Signup endpoint intentionally unauthenticated (registration)
- All POST/PUT/PATCH endpoints use Pydantic models for input validation
