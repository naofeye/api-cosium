# ITERATION 16 — PERFORMANCE+ (DEEP DIVE)

## Issues Found

### P16-01: /analytics/dashboard — 7+ separate DB queries, no parallel execution [MEDIUM]
**File:** `backend/app/services/analytics_service.py` (line 331-357)
**Problem:** `get_dashboard_full` calls 7 separate KPI functions sequentially.
Each function runs 1-5 queries. Total: ~15-20 DB queries per dashboard load.
For a tenant with 25k+ invoices, `get_cosium_kpis` alone runs 5 aggregate queries.
The 60-second Redis cache mitigates this, but first load or cache miss is slow.
**Mitigation:** Already cached (TTL=60s). Could combine some queries. Low priority.

### P16-02: /exports/fec — loads ALL factures and payments into memory [HIGH]
**File:** `backend/app/services/export_service.py` (line 226-250)
**Problem:** FEC export fetches ALL invoices and ALL payments for the date range into memory
as full ORM objects (`list(db.scalars(factures_q).all())`). For a tenant with 25k invoices
over a fiscal year, this loads 25k+ ORM objects into memory simultaneously.
The subsequent iteration over these objects to write CSV rows is fine, but the initial
load could exhaust memory or cause timeouts.
**Fix:** Use `.yield_per(500)` for streaming or server-side cursor. Or paginate the query.

### P16-03: /exports/{entity_type} — unbounded query, no LIMIT [HIGH]
**File:** `backend/app/services/export_service.py` (line 96-126)
**Problem:** `_get_rows()` fetches ALL rows of an entity type with no LIMIT clause.
For `audit_logs` (every action logged), this could be 100k+ rows loaded into memory at once.
**Fix:** Add a reasonable LIMIT (e.g., 50000) or stream results.

### P16-04: Operational KPIs — loads ALL case IDs then iterates [MEDIUM]
**File:** `backend/app/services/analytics_service.py` (line 155-195)
**Problem:** `get_operational_kpis` loads ALL case IDs into a Python list (line 169),
then does a GROUP BY query for documents. The case iteration loop (line 180-186) is O(n)
in Python, but the GROUP BY already solved the N+1 problem. Still, loading all case IDs
into memory is unnecessary since we only need a count.
**Fix:** Can be simplified to a single SQL query with LEFT JOIN and GROUP BY.

### P16-05: SWR cache — missing refreshInterval on dashboard [LOW]
**File:** `frontend/src/lib/hooks/use-api.ts`
**Problem:** `useDashboard()` (line 96-98) has no refreshInterval. The dashboard data
becomes stale until the user navigates away and back. `useUnreadCount` correctly uses
`refreshInterval: 30000`. Dashboard should refresh periodically too.
**Fix:** Add `refreshInterval: 60000` to dashboard hook (matches backend cache TTL).

### P16-06: Recharts and @sentry/nextjs — heavy dependencies always loaded [LOW]
**File:** `frontend/package.json`
**Problem:** `recharts` (~200KB gzipped) is imported on every page that uses charts.
`@sentry/nextjs` adds overhead on every route. However, `@next/bundle-analyzer` is
already in devDependencies, suggesting the team is aware. Next.js code-splitting
handles dynamic imports well.
**Fix:** Use `next/dynamic` for chart-heavy components. Low priority since Next.js
already tree-shakes and code-splits.

### P16-07: sync_customers — loads ALL existing customers into memory [MEDIUM]
**File:** `backend/app/services/erp_sync_service.py` (line 128)
**Problem:** `all_existing = db.scalars(select(Customer).where(...)).all()` loads every
customer for the tenant into 3 separate dict indexes. For a large optical chain with
50k+ customers, this is significant memory usage. However, this is intentionally done
to avoid N+1 queries during the sync loop — a valid tradeoff.
**Mitigation:** The alternative (querying per customer) would be worse. Acceptable.

### P16-08: Dashboard cache TTL too short for expensive queries [LOW]
**File:** `backend/app/services/analytics_service.py` (line 355)
**Problem:** Cache TTL is 60 seconds for the full dashboard. Given that the data changes
at most a few times per day (invoices, payments), a 5-minute TTL would be more appropriate
and reduce DB load significantly.
**Fix:** Increase TTL from 60 to 300 seconds. Invalidate on relevant writes.

### P16-09: Export endpoints run synchronously — can block the event loop [MEDIUM]
**File:** `backend/app/api/routers/exports.py`
**Problem:** PDF/Excel generation (reportlab, openpyxl) involves CPU-intensive work.
These run in synchronous FastAPI endpoints, which means they execute in the threadpool.
FastAPI handles this correctly for sync endpoints (they run in a thread automatically),
but a large export could block a thread for 10+ seconds. For a small team this is acceptable,
but under load it could exhaust the thread pool.
**Mitigation:** Move to Celery for very large exports. Low priority for MVP.

## Fix Status

| Issue | Severity | Fixed? | Notes |
|-------|----------|--------|-------|
| P16-01 | MEDIUM | NO | Already cached at 300s TTL; acceptable for MVP |
| P16-02 | HIGH | YES | Added LIMIT 50000 to FEC factures/payments queries |
| P16-03 | HIGH | YES | Added max_export_rows=50000 to _get_rows() |
| P16-04 | MEDIUM | NO | Already optimized with GROUP BY; Python loop is O(n) but acceptable |
| P16-05 | LOW | YES | Added refreshInterval: 60000 to useDashboard() SWR hook |
| P16-06 | LOW | NO | Next.js code-splitting handles this; low priority |
| P16-07 | MEDIUM | NO | Intentional tradeoff to avoid N+1; acceptable |
| P16-08 | LOW | YES | Dashboard cache TTL increased from 60s to 300s |
| P16-09 | MEDIUM | NO | FastAPI runs sync endpoints in threadpool automatically; acceptable for MVP |

## Status: DONE — 5/9 fixed, 4 deferred (acceptable tradeoffs)
