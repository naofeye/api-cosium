# ITERATION 27 - UX++ (Ultra-strict)

## Issues Found & Fixed

### 1. New devis form submit button missing `loading` prop
- **File**: `frontend/src/app/devis/new/page.tsx`, line ~250
- **Severity**: LOW
- **Problem**: Submit button used `disabled={!isValid || isSubmitting}` but didn't pass `loading={isSubmitting}` to show the spinner animation. User couldn't tell if the form was submitting or simply disabled.
- **Fix**: Changed to `disabled={!isValid} loading={isSubmitting}`.

### 2. All forms verified for submit button state
- **Login page**: Uses `loading={isSubmitting}` and `disabled={!isValid}` -- OK
- **New case page**: Uses `loading={isSubmitting}` and `disabled={!isValid}` -- OK
- **New client page**: Uses `loading={isSubmitting}` and `disabled={!isValid}` -- OK
- **New devis page**: Fixed (see above)

### 3. All empty states verified
- `DataTable`: Built-in empty state with customizable title, description, icon, and CTA action -- OK
- `Clients page`: Custom empty state with "Synchroniser Cosium" and "Creer un client" buttons -- OK
- `PEC page`: "Aucune demande de PEC" with description -- OK
- `Factures page`: "Aucune facture" with description -- OK

### 4. All error states verified
- `DataTable`: Built-in error state with retry button (via `onRetry` prop) -- OK
- `Dashboard`: `ErrorState` with retry via `mutate()` -- OK
- All list pages use DataTable which handles error state internally -- OK

### 5. Toast auto-dismiss verified
- `Toast.tsx`: `TOAST_DURATION_MS = 5000` (5 seconds) with exit animation -- OK
- Manual close via X button with timer cleanup -- OK
- Global API error events automatically create error toasts -- OK

### 6. Date formatting verified
- `formatDate()` in `lib/format.ts` uses `Intl.DateTimeFormat("fr-FR")` with DD/MM/YYYY -- OK
- `DateDisplay` component wraps `formatDate()` consistently -- OK
- `formatDateTime()` for timestamps also uses fr-FR format -- OK
