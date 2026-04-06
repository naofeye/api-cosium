# ITERATION 29 - DEAD CODE++ & ARCHITECTURE (Ultra-strict)

**Date**: 2026-04-06
**Theme**: Unused schemas, unused components, migration chain, circular deps, unused deps

---

## 1. Unused Pydantic Schemas (defined but never imported elsewhere)

Found **32 unused schema classes** across domain/schemas:

| File | Unused Classes |
|------|---------------|
| admin.py | ServiceStatus, MetricsTotals, MetricsActivity, DataQualityEntity |
| audit.py | AuditLogSearch |
| auth.py | PasswordMixin, TenantInfo, RefreshRequest |
| client_360.py | DossierSummary, DocumentSummary, DevisSummary, FactureSummary, PaiementSummary, PecSummary, ConsentementSummary |
| clients.py | ClientSearch |
| cosium_reference.py | ReferenceSyncResult |
| cosium_sync.py | CosiumPaymentResponse, CosiumPaymentList, CosiumThirdPartyPaymentResponse, CosiumThirdPartyPaymentList, CosiumPrescriptionResponse, CosiumPrescriptionList |
| gdpr.py | GDPRPersonalInfo, GDPRCaseItem, GDPRDocumentItem, GDPRDevisItem, GDPRFactureItem, GDPRPaymentItem, GDPRConsentItem, GDPRInteractionItem |
| pec_preparation.py | UserValidationEntry, UserCorrectionEntry |
| search.py | SearchResultItem |

**Severity**: INFO - Most are sub-schemas used internally via composition (e.g., Client360Response contains DossierSummary etc. via `list[dict]` or embedded). The cosium_sync ones and GDPR ones are prepared for future features. No action needed but could be cleaned up for tidiness.

## 2. Unused Frontend Components

| Component | Status |
|-----------|--------|
| AsyncSelect.tsx | UNUSED - never imported (0 consumers) |
| FileUpload.tsx | UNUSED - never imported (0 consumers) |

**Severity**: LOW - These are reusable components prepared for future use (file upload in documents, async select in forms). Not dead code per se, but could be flagged.

## 3. Alembic Migration Chain

- **Total migrations**: 29
- **Base (root)**: `8a51c08a4f71` (initial_5_tables)
- **Head**: `l7f8g9h0i1j2` (add_document_extractions)
- **Chain integrity**: CLEAN - single linear chain, no forks, no orphans
- All 29 migrations form a single unbroken chain from base to head

## 4. Circular Dependencies

No circular import issues detected. The architecture follows clean layering:
- routers -> services -> repositories -> models
- routers -> domain/schemas
- services -> domain/schemas
- No reverse imports found

## 5. Unused npm Dependencies

| Package | Status |
|---------|--------|
| `@sentry/nextjs` | UNUSED - not imported anywhere in frontend/src/ |
| `autoprefixer` | UNUSED - not referenced in any config (Tailwind v4 uses @tailwindcss/postcss) |

**Note**: `@types/react-big-calendar` is in dependencies (should be devDependencies) but is actually used.

## 6. Unused Python Packages

All packages in requirements.txt are actively imported and used. No unused Python dependencies found.

## Summary

| Category | Found | Severity |
|----------|-------|----------|
| Unused Pydantic schemas | 32 classes | INFO (prepared for future) |
| Unused frontend components | 2 | LOW |
| Migration chain issues | 0 | CLEAN |
| Circular dependencies | 0 | CLEAN |
| Unused npm deps | 2 | LOW |
| Unused Python deps | 0 | CLEAN |
