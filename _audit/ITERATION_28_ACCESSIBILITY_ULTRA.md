# ITERATION 28 - ACCESSIBILITY++ (Ultra-strict)

## Issues Found & Fixed

### 1. `FormField`/`FormInput` - label not linked to input, error not linked via aria-describedby
- **File**: `frontend/src/components/form/FormField.tsx`
- **Severity**: HIGH (WCAG 1.3.1, 3.3.2 violation)
- **Problem**: `FormField` generated `fieldId` and `errorId` but never passed them to child inputs. The `<label htmlFor={fieldId}>` didn't match any input `id`, making the label decorative-only for assistive tech. Error messages weren't linked via `aria-describedby`.
- **Fix**: Implemented React Context (`FormFieldContext`) to pass `fieldId` and `errorId` from `FormField` to `FormInput`. `FormInput` now automatically gets `id={fieldId}`, `aria-describedby={errorId}`, and `aria-invalid` when in error state.

### 2. `ErrorState` icon missing `aria-hidden`
- **File**: `frontend/src/components/ui/ErrorState.tsx`, line ~15
- **Severity**: LOW
- **Problem**: `AlertTriangle` icon was announced by screen readers as redundant decoration.
- **Fix**: Added `aria-hidden="true"`.

### 3. `DataTable` clickable rows not keyboard-accessible
- **File**: `frontend/src/components/ui/DataTable.tsx`, line ~141
- **Severity**: MEDIUM (WCAG 2.1.1 violation)
- **Problem**: Clickable rows (`onRowClick`) only responded to mouse clicks. Keyboard users could not activate rows.
- **Fix**: Added `tabIndex={0}`, `role="button"`, and `onKeyDown` handler for Enter/Space keys when `onRowClick` is provided.

### 4. `ConfirmDialog` missing `aria-describedby`
- **File**: `frontend/src/components/ui/ConfirmDialog.tsx`, line ~85
- **Severity**: LOW (WCAG 1.3.1)
- **Problem**: Dialog had `aria-labelledby` for the title but no `aria-describedby` for the message body, so screen readers only announced the title.
- **Fix**: Added `id="confirm-dialog-description"` to the message `<p>` and `aria-describedby="confirm-dialog-description"` to the dialog.

### 5. `KPICard` trend value conveyed only by color
- **File**: `frontend/src/components/ui/KPICard.tsx`, line ~41
- **Severity**: LOW (WCAG 1.4.1)
- **Problem**: Positive trends shown in green, negative in red, with no text/icon alternative for color-blind users or screen readers.
- **Fix**: Added `aria-label` with "Tendance : hausse/baisse de X%" and `sr-only` text "(hausse)" or "(baisse)".

### 6. `MoneyDisplay` colored amounts conveyed only by color
- **File**: `frontend/src/components/ui/MoneyDisplay.tsx`
- **Severity**: LOW (WCAG 1.4.1)
- **Problem**: When `colored={true}`, positive/negative amounts were only distinguished by green/red color.
- **Fix**: Added `sr-only` text "(positif)" or "(negatif)" for screen readers.

### 7. Dashboard period selector buttons missing `aria-pressed`
- **File**: `frontend/src/app/dashboard/page.tsx`, line ~302
- **Severity**: LOW
- **Problem**: Period selector buttons (toggle group) didn't indicate active state to assistive technology.
- **Fix**: Added `aria-pressed={period === p.key}`.

### 8. PEC page status filter missing `aria-label`
- **File**: `frontend/src/app/pec/page.tsx`, line ~81
- **Severity**: LOW
- **Problem**: Status filter `<select>` had no accessible label.
- **Fix**: Added `aria-label="Filtrer par statut"`.

## Already Correct (verified)
- All sidebar icons have `aria-hidden="true"` and links have `aria-label` in collapsed mode
- `SearchInput` has `aria-label` from placeholder
- `FileUpload` has `aria-label`, keyboard support, and focus-visible ring
- `ConfirmDialog` has focus trap, Escape key, and focus restoration
- `Header` notification button has `aria-haspopup`, `aria-expanded`, and `aria-label`
- `StatusBadge` has `role="status"` and `aria-label`
- All Lucide icons in decorative positions have `aria-hidden="true"`
