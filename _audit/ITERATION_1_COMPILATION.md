# Audit Iteration 1 - Compilation

## Date: 2026-04-05

## Issues Found: 19 total

### Ruff Lint Errors (17)
| # | File | Code | Description | Fix |
|---|------|------|-------------|-----|
| 1 | domain/schemas/cosium_reference.py | I001 | Unsorted imports | Auto-fixed (--fix) |
| 2 | domain/schemas/cosium_sync.py | I001 | Unsorted imports | Auto-fixed (--fix) |
| 3 | integrations/cosium/adapter_reference.py | F401 | Unused import `re` | Auto-fixed (--fix) |
| 4 | integrations/cosium/adapter_reference.py | UP038 | Use X|Y in isinstance | Auto-fixed (--unsafe-fixes) |
| 5 | models/__init__.py | I001 | Unsorted imports | Auto-fixed (--fix) |
| 6 | services/erp_sync_service.py | F401 | Unused import `relativedelta` | Auto-fixed (--fix) |
| 7 | services/export_service.py | I001 | Unsorted imports | Auto-fixed (--fix) |
| 8-12 | models/case.py | F821 | Undefined names (Document, Devis, Facture, Payment, PecRequest) | Added noqa: F821 (SQLAlchemy string refs) |
| 13-17 | models/devis.py, document.py, facture.py, payment.py, pec.py | F821 | Undefined name `Case` | Added noqa: F821 (SQLAlchemy string refs) |

### Ruff Errors Found Post-Fix (2)
| # | File | Code | Description | Fix |
|---|------|------|-------------|-----|
| 18 | services/banking_service.py | B904 | raise without from in except | Added `from None` |
| 19 | services/renewal_engine.py | N806 | Uppercase variable in function | Renamed MAX_CANDIDATES -> max_candidates |

### TypeScript Errors (1)
| # | File | Description | Fix |
|---|------|-------------|-----|
| 1 | tests/components/ExportCsv.test.ts:12 | Type mismatch: `(blob: Blob)` vs `(obj: Blob | MediaSource)` | Changed param type to `Blob | MediaSource` with cast |

### TypeScript `any` Types: 0 found

## Result: 19 found, 19 fixed, 0 remaining
