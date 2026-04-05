# Iteration 8 -- Accessibility Audit

## Audit scope
All frontend components checked for:
- aria-label on icon-only buttons
- alt text on images
- Label associations for form inputs
- Tab order / tabIndex usage
- Contrast ratios
- Skip-to-content link
- Modal focus trapping and aria roles

## Findings and fixes

### 1. Settings page: password inputs missing labels
**File**: `frontend/src/app/settings/page.tsx`
**Issue**: Two password inputs used only placeholder, no `<label>` or `id` attribute.
**Fix**: Added `<label htmlFor>` elements and `id` attributes to both inputs.
Also added `autoComplete` attributes for better UX.

### 2. Rapprochement page: filter select missing label
**File**: `frontend/src/app/rapprochement/page.tsx`
**Issue**: Select for filtering reconciled/unreconciled had no label.
**Fix**: Added `sr-only` label, `id`, and `aria-label`.

### 3. Renewals page: form inputs missing label associations
**File**: `frontend/src/app/renewals/page.tsx`
**Issue**: Campaign name input and channel select had `<label>` without `htmlFor`.
**Fix**: Added `id` attributes and `htmlFor` to labels.

### 4. ConfirmDialog: no focus trap
**File**: `frontend/src/components/ui/ConfirmDialog.tsx`
**Issue**: Dialog handled Escape key but did not trap Tab key within the dialog.
**Fix**: Added Tab key focus trapping logic that cycles focus between the first
and last focusable elements inside the dialog.

### 5. SearchInput: missing aria-label on input
**File**: `frontend/src/components/ui/SearchInput.tsx`
**Issue**: Input had placeholder but no `aria-label` for screen readers.
**Fix**: Added `aria-label={placeholder}` to the input element.
Also added `aria-hidden="true"` to the decorative Search icon.

### 6. Decorative icons missing aria-hidden
**Files**: rapprochement/page.tsx, renewals/page.tsx, marketing/page.tsx
**Issue**: Multiple decorative icons (next to text) lacked `aria-hidden="true"`.
**Fix**: Added `aria-hidden="true"` to all decorative icons in these files.

## Items verified as already correct

### Skip-to-content link
Present in `frontend/src/app/layout.tsx` -- links to `#main-content`.
Target `id="main-content"` exists in `components/layout/AuthLayout.tsx`.
Uses `sr-only` with `focus:not-sr-only` pattern. OK.

### Icon-only buttons with aria-label (all correct)
- Sidebar collapse button: aria-label (dynamic based on state)
- Header hamburger: aria-label="Ouvrir le menu"
- Header dark mode toggle: aria-label (dynamic)
- Header notifications bell: aria-label="Notifications"
- Header close notifications: aria-label="Fermer"
- Header logout: aria-label="Se deconnecter"
- DataTable pagination: aria-label="Page precedente" / "Page suivante"
- AI Usage month navigation: aria-label="Mois precedent" / "Mois suivant"
- SearchInput clear: aria-label="Effacer la recherche"
- Toast close: aria-label="Fermer"
- OnboardingGuide close: aria-label="Fermer le guide"
- TabDocuments preview close: aria-label="Fermer la previsualisation"
- Actions detail button: aria-label="Voir le detail"
- Statistiques export buttons: aria-label present

### Sidebar navigation links
All nav links have `aria-current="page"` when active.
When sidebar is collapsed, all links get `aria-label={item.label}`.
All icons have `aria-hidden="true"`.

### Images
- TabDocuments preview img: has `alt={previewDoc.filename}`. OK.
- No other `<img>` tags found without alt.
- next/image not used (no images requiring it in current codebase).

### Modal accessibility (ConfirmDialog)
- `role="dialog"` -- present
- `aria-modal="true"` -- present
- `aria-labelledby="confirm-dialog-title"` -- present
- Focus on open -- focuses cancel button
- Escape key -- closes dialog
- Focus trap -- FIXED (was missing, now added)

### Contrast ratios
Key elements verified:
- Primary text: gray-900 on white -- ratio > 12:1 (AAA)
- Secondary text: gray-500 on white -- ratio ~4.6:1 (AA)
- Badges: colored backgrounds with darker text variants -- all AA+
- Active sidebar items: white on blue-600 -- ratio > 4.5:1 (AA)

### Tab order
- No `tabIndex` usage found -- natural DOM order applies
- Focus-visible styles present on all interactive elements (`focus-visible:ring-2`)
- No keyboard traps identified

## Verification results
- TypeScript: 0 errors
- Next.js build: compiled successfully, 41/41 static pages generated
- Pytest: 488 passed, 0 failed
