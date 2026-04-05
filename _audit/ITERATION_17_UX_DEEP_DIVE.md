# Iteration 17 - UX+ Deep Dive

## Date: 2026-04-05

## User Flow Analysis

### Flow 1: Login -> Dashboard -> View Client -> View Factures -> Download PDF
- [x] Login form: has inline validation (zod + onChange mode), submit disabled while invalid, loading state on button
- [x] Login -> Dashboard: redirect to /actions on success, toast not needed (redirect is feedback)
- [x] Dashboard -> Client: click from client list navigates correctly, breadcrumb present
- [x] Client detail: breadcrumb [Clients > Name], KPIs visible, tabs for finances
- [x] Factures tab: clickable rows navigate to /factures/{id}, PDF download button present
- [x] Facture detail: PDF download via downloadPdf() utility, opens in new tab

### Flow 2: Admin -> Sync Cosium -> Check Results -> View Data
- [x] Admin page has CosiumConnection component showing status KPIs
- [x] ManualSync component: individual sync buttons per entity type + "Tout synchroniser"
- [x] Sync results display inline with green/red feedback text
- [x] After sync, data pages (clients, factures) show synced data via SWR
- [x] Sync button shows spinner during sync, disables other buttons

### Flow 3: Create Devis -> Sign -> Generate Facture -> Record Payment
- [x] Devis list -> "Nouveau devis" button -> form with line items
- [x] Form: sticky action bar, disabled submit when invalid, inline validation
- [x] Devis detail: status workflow buttons (Envoyer -> Signer -> Facturer)
- [x] "Generer la facture" button on signed devis, with loading state
- [x] Cancel action uses ConfirmDialog before proceeding
- [x] Facture detail page shows linked devis number for navigation back

### Flow 4: Search Client -> Vue 360 -> Documents -> Download
- [x] GlobalSearch: debounced (300ms), grouped results by type
- [x] Client 360: all tabs (resume, dossiers, finances, documents, marketing, historique)
- [x] Documents tab: preview for images, PDF opens in new tab, download button
- [x] Avatar upload with drag & drop
- [x] Delete client: ConfirmDialog with irreversible warning

### Flow 5: Relances -> Create Plan -> Execute -> Check Stats
- [x] Relances page: KPIs (total impaye, relances envoyees, taux recouvrement)
- [x] Balance agee visualization with color coding
- [x] Tabs: "A relancer" and "Historique"
- [x] Plans page: create plan form, toggle active/inactive, execute button
- [x] Plan execution: spinner on execute button, results feedback

## Fixes Applied

### UX Issues Found & Fixed
1. **Custom tabs missing ARIA roles**: Client detail and relances pages used plain `<button>` for tabs
   - FIXED: Added `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`, `id`
   - Files: `clients/[id]/page.tsx`, `relances/page.tsx`

2. **FileUpload not keyboard accessible**: div-based click area had no keyboard handler
   - FIXED: Added `role="button"`, `tabIndex={0}`, `onKeyDown` for Enter/Space, `focus-visible` styles
   - File: `components/ui/FileUpload.tsx`

3. **GlobalSearch results not accessible as combobox pattern**
   - FIXED: Added `role="combobox"`, `aria-expanded`, `aria-haspopup="listbox"`, `aria-controls` to input
   - Added `role="listbox"`, `role="option"` to results
   - File: `components/layout/GlobalSearch.tsx`

4. **Notification dropdown missing ARIA and Escape-close on keyboard**
   - FIXED: Added `role="dialog"`, `aria-label`, `onKeyDown` Escape handler
   - Added `aria-haspopup="dialog"`, `aria-expanded` to bell button
   - File: `components/layout/Header.tsx`

## Verified OK
- All forms disable submit during processing (Button loading prop used consistently)
- All delete actions go through ConfirmDialog
- Toast messages are consistent (success/error/warning/info variants)
- Mobile sidebar closes after navigation (handleLinkClick -> closeMobile)
- Breadcrumbs present on all detail pages
- Back navigation possible from all detail pages via breadcrumb links
- Empty states with CTAs on all list pages
- Loading/error states on all data pages
