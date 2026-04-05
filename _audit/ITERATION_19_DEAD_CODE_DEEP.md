# ITERATION 19 — DEAD CODE+ (DEEP DIVE)

**Date** : 2026-04-05
**Scope** : Architecture-level dead code, over/under-abstraction, unused schemas/relationships

---

## 1. Pass-through services (over-abstraction)

Checked all 37 services. `payment_service.py` (19 lines) is thin but does add logging + schema mapping. `cosium_invoice_service.py` (39 lines) similarly adds logging + pagination schema. `dashboard_service.py` adds Redis caching. `completeness_service.py` has real logic (document matching).

**Verdict** : No pure pass-through services. All add at least logging + schema validation or business logic. Architecture is sound.

## 2. Repeated code patterns (under-abstraction)

- `model_validate()` pattern appears 49 times across services — this is a standard Pydantic pattern, not duplication.
- `raise NotFoundError()` pattern appears 38 times — standard error handling, not duplication.
- No 3+ identical code blocks found that warrant extraction.

**Verdict** : No actionable under-abstraction.

## 3. SQLAlchemy relationships

All 10 relationships defined in models (Case ↔ Document, Devis, Facture, Payment, PecRequest) are used by `client_360_service.py` with `selectinload()`. All relationships use `lazy="noload"` to prevent N+1 by default.

**Verdict** : All relationships are actively used. No dead relationships.

## 4. Unused Pydantic schemas

**7 schemas are truly unused** (defined but never referenced outside their own class definition, not even as nested types):

| Schema | File | Status |
|--------|------|--------|
| `AuditLogSearch` | audit.py | Unused — intended for future search filter |
| `RefreshRequest` | auth.py | Unused — refresh is via httpOnly cookie, no body needed |
| `SyncResult` | auth.py | Unused — replaced by SyncResultResponse in sync.py |
| `ClientSearch` | clients.py | Unused — search uses query params instead |
| `CosiumPaymentList` | cosium_sync.py | Unused — sync stores raw, no list endpoint |
| `CosiumThirdPartyPaymentList` | cosium_sync.py | Unused — same |
| `CosiumPrescriptionList` | cosium_sync.py | Unused — same |

**Severity** : INFO — these are dead code but harmless. They represent planned-but-unimplemented features.

## 5. Test utility functions

`conftest.py` (102 lines) defines 5 fixtures: `db`, `default_tenant`, `client`, `seed_user`, `auth_headers`. All are used across the 71 test files. No unused test helpers found.

## 6. Unused CSS classes

- `.table-responsive` class in `globals.css` (line 108-111) is not referenced by any TSX file.
- All dark mode CSS overrides are actively used.

**Severity** : INFO — minor dead CSS.

## 7. package.json scripts

All 8 npm scripts are functional:
- `dev`, `build`, `start`, `lint` — standard Next.js
- `format`, `format:check` — Prettier
- `typecheck` — TypeScript
- `test`, `test:watch` — Vitest

## 8. Alembic migration chain

All 24 migrations form a **clean linear chain** from `8a51c08a4f71` (initial) to `5ae5ee2cc95d` (latest). No orphans, no forks, no cycles detected.

---

## Summary

| Category | Issues | Severity |
|----------|--------|----------|
| Over-abstraction (pass-through) | 0 | — |
| Under-abstraction (duplication) | 0 | — |
| Unused relationships | 0 | — |
| Unused Pydantic schemas | 7 | INFO |
| Unused test helpers | 0 | — |
| Unused CSS | 1 | INFO |
| Package scripts broken | 0 | — |
| Migration chain issues | 0 | — |

**Total issues** : 8 (all informational)
**Score impact** : 0 (no functional issues)
