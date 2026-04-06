# ITERATION 26 - PERFORMANCE++ (Ultra-strict)

## Issues Found & Fixed

### 1. Missing composite index on `notifications` for SSE polling
- **File**: `backend/app/models/notification.py`
- **Severity**: MEDIUM
- **Problem**: SSE polling runs `WHERE tenant_id = ? AND user_id = ? AND id > ?` every 5 seconds per connected user. Without a composite index, this causes sequential scans as the table grows.
- **Fix**: Added `Index("ix_notifications_tenant_user_id", "tenant_id", "user_id", "id")` and `Index("ix_notifications_tenant_user_unread", "tenant_id", "user_id", "is_read")` for the unread count query.

### 2. Missing composite index on `reminders` for overdue check
- **File**: `backend/app/models/reminder.py`
- **Severity**: MEDIUM
- **Problem**: The `check_overdue_invoices` task queries `WHERE tenant_id = ? AND target_type = ? AND target_id = ? AND created_at >= ?` to detect existing reminders. Without a composite index, this degrades as reminders accumulate.
- **Fix**: Added `Index("ix_reminders_tenant_target_created", "tenant_id", "target_type", "target_id", "created_at")`.

### 3. `ActivityChart` (Recharts) not lazy-loaded on admin page
- **File**: `frontend/src/app/admin/page.tsx`
- **Severity**: LOW
- **Problem**: `ActivityChart` imports Recharts (~200KB gzipped) and was directly imported, increasing the admin page's initial bundle size.
- **Fix**: Changed to `dynamic()` import with SSR disabled and skeleton loading fallback.

### 4. DB session handling - ACCEPTABLE
- **Analysis**: `get_db()` uses generator with `finally: db.close()`. Celery tasks all use `SessionLocal()` with `try/finally: db.close()`. Pool settings (`pool_size=20`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=1800`) are well-configured. No issues found.

### 5. SWR refresh intervals - ACCEPTABLE
- **Analysis**: Dashboard refreshes at 60s, unread count at 30s, calendar at 120s. These are reasonable for a business app. Individual entity pages don't set `refreshInterval` (manual refetch only). No over-fetching found.
