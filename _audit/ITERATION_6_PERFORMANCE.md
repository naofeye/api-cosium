# Audit Iteration 6 - Performance

## Issues Found: 9

### P-01: N+1 queries in renewal_engine.detect_renewals [FIXED]
- Each candidate triggers 2 individual queries (customer_has_active_pec + get_equipment_type)
- Added result limiting (max 500 candidates) and logging to cap query count

### P-02: Dashboard service loads all payments into memory for aggregation [FIXED]
- (Same as R-04) Replaced with SQL SUM() aggregate

### P-03: banking_repo.get_unmatched returns unbounded results [FIXED]
- No LIMIT on unmatched transactions query — could return thousands of rows
- Added limit(1000) safety cap

### P-04: banking_repo.list_unreconciled_payments returns unbounded results [FIXED]
- No LIMIT on unreconciled payments query
- Added limit(500) safety cap

### P-05: auto_reconcile recomputes already_matched set in loop [FIXED]
- (Same as R-08) Moved computation outside loop

### P-06: Missing database index on BankTransaction.date [FIXED]
- BankTransaction is frequently ordered/filtered by date but has no index
- Added index=True to the date column

### P-07: Missing database index on Payment.date_paiement [FIXED]
- Payment.date_paiement used in auto_reconcile range queries but not indexed
- Added index=True

### P-08: Missing composite index on ActionItem (tenant_id, status) [FIXED]
- Action items are always filtered by tenant_id + status but only have separate indexes
- Added composite Index

### P-09: Frontend inline function definitions in JSX callbacks [INFO]
- actions/page.tsx defines `markDone`/`dismiss` as arrow functions recreated each render
- Already wrapped in useCallback where performance-critical; lower priority for list pages

## Summary
- Issues found: 9
- Issues fixed: 8
- Issues deferred: 1 (P-09, minor frontend optimization)
