# ITERATION 11 - COMPILATION+ (DEEP DIVE)

## Scope
Deeper type checking, Pydantic v2 compliance, SQLAlchemy model consistency, response_model alignment.

## Issues Found

### 11.1 - Missing return type annotation on public function
- **File**: `backend/app/services/cosium_reference_sync.py:38`
- **Issue**: `_get_cosium_client(db, tenant_id)` has no `-> CosiumClient` return type
- **Severity**: Low (private function, but still should be typed)
- **Fix**: Add `-> CosiumClient` return type
- **Status**: [x] FIXED

### 11.2 - Mapped[float] with Numeric columns (documentation)
- **Files**: `models/payment.py`, `models/devis.py`, `models/facture.py`, `models/pec.py`, `models/ai.py`
- **Issue**: `Mapped[float]` used with `Numeric(10,2)` columns. PostgreSQL Numeric returns `Decimal`, not `float`. SQLAlchemy + Pydantic coerce this correctly, but the type annotation is technically incorrect.
- **Severity**: Low (works in practice, Pydantic coerces Decimal -> float)
- **Decision**: Not changing -- would require `from decimal import Decimal` across 20+ files and all schemas. The `float` annotation matches the API contract. Documented as known deviation.
- **Status**: [x] DOCUMENTED (no change needed)

### 11.3 - No deprecated Pydantic v1 patterns found
- No `class Config:` in domain schemas (all use `model_config = ConfigDict(...)`)
- No `.dict()` calls found (all use `.model_dump()`)
- **Status**: [x] CLEAN

### 11.4 - No untyped generic containers found
- No bare `list` or `dict` annotations without type parameters
- **Status**: [x] CLEAN

### 11.5 - All response schemas have `from_attributes=True`
- Verified 38+ response models all have `model_config = ConfigDict(from_attributes=True)`
- **Status**: [x] CLEAN

### 11.6 - Month calculation imprecise in analytics_service.py
- **File**: `backend/app/services/analytics_service.py:227`
- **Issue**: `timedelta(days=30 * i)` for "months ago" is imprecise. 30*5=150 days is not 5 months. Can skip February or double-count months at boundaries.
- **Severity**: Medium (affects CA par mois chart labels/data)
- **Fix**: Use proper month subtraction with `replace(month=...)` arithmetic
- **Status**: [x] FIXED

## Summary
- **Issues found**: 3 (1 type annotation, 1 Mapped[float] documentation, 1 month calculation)
- **Issues fixed**: 2
- **Issues documented**: 1 (Mapped[float] -- no change needed)
