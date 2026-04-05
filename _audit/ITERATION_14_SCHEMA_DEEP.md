# ITERATION 14 — SCHEMA+ (DEEP DIVE)

## Issues Found

### SCH-14-01 [MEDIUM] Dashboard endpoint role restriction blocks actions page
- **File**: `backend/app/api/routers/dashboard.py`
- **File**: `frontend/src/app/actions/page.tsx`
- **Issue**: `/dashboard/summary` requires admin+manager role, but the actions/home page calls it for all users. Operators/viewers will get a 403.
- **Fix**: Relax dashboard/summary to all authenticated users (get_tenant_context).

### SCH-14-02 [LOW] Bank import endpoint should validate file extension
- Already covered in SEC-13-07, listing here for completeness.

## Items Verified OK

- All frontend useSWR calls match valid backend URL paths
- Frontend handles null/undefined data with guards (error/loading/empty states)
- Status strings are consistent between frontend badges and backend logic
- Dates are ISO format from backend, frontend formats them correctly
- Response schemas use ConfigDict(from_attributes=True) properly
- No migrations to check (project uses create_all, Alembic not yet configured)
- Financial amounts use float consistently (both backend schemas and frontend display)
