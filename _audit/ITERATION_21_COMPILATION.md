# ITERATION 21 - COMPILATION++ Audit

## Issues Found

### 21-1 [LOW] cosium_reference router returns list[dict] in 5 endpoints (banks, companies, users, equipment-types, frame-materials)
- File: backend/app/api/routers/cosium_reference.py, lines 268, 290, 316, 342, 361
- Violates "no dict in API responses" rule
- Severity: Low (works but not type-safe)

### 21-2 [LOW] Several routers return `dict` instead of Pydantic model
- Files: admin_health.py, cosium_documents.py, pec_preparation.py, sync.py
- Severity: Low (works but not type-safe)

### 21-3 [OK] All Response schemas used with model_validate have from_attributes=True
- Verified: CaseResponse, ClientResponse, DocumentResponse, PaymentResponse, BankTransactionResponse, etc.
- All checked - no missing from_attributes on ORM-mapped schemas

### 21-4 [OK] No SQLAlchemy legacy .query() usage
- All code uses select() style (SQLAlchemy 2.0 compatible)

### 21-5 [OK] All response_model declarations match return types
- Verified across all routers
