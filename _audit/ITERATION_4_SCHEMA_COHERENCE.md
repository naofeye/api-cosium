# Audit Iteration 4 - SCHEMA COHERENCE

## Issues Found: 3

### C1 - FIXED - Frontend User type has extra created_at field
- File: `frontend/src/lib/types.ts`
- Issue: `User` interface had `created_at: string` but backend `UserMeResponse` (auth.py) only returns id, email, role, is_active
- Fix: Removed `created_at` from frontend `User` interface

### C2 - FIXED - Frontend Customer type missing deleted_at field
- File: `frontend/src/lib/types.ts`
- Issue: Frontend `Customer` interface was missing `deleted_at: string | null` that backend `ClientResponse` includes
- Fix: Added `deleted_at: string | null` to frontend `Customer` interface

### C3 - NOTED - Two PaymentResponse classes
- Files: `backend/app/domain/schemas/payments.py` and `backend/app/domain/schemas/banking.py`
- Issue: Two classes named `PaymentResponse` in different modules
- Status: Intentional - payments.py has slim 5-field version for case summary, banking.py has full 11-field version
- Frontend correctly maps: `PaymentItem` -> payments.py, `PaymentFull` -> banking.py

### Verified OK
- All API endpoint URLs in frontend match backend router paths
- No circular imports in backend models (models/__init__.py uses clean re-exports)
- Auth schemas match: TokenResponse, TenantInfo, LoginResponse fields align
- Case schemas match: CaseResponse, CaseDetail fields align
- Devis schemas match: DevisResponse, DevisDetail, DevisLigne fields align
- Facture schemas match: FactureResponse, FactureDetail fields align
- PEC schemas match: PecResponse fields align
- Notification/ActionItem schemas match
- Campaign/Segment schemas match
- BankTransaction schema matches
- Interaction schema matches
- Dashboard schema matches
- All response_model decorators on routers match what services return
- Database model field types match Pydantic schema types
