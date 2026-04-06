# ITERATION 24 - SCHEMA++ Audit

## Issues Found

### 24-1 [MEDIUM] Frontend Customer type missing fields from backend ClientResponse
- File: frontend/src/lib/types/client.ts
- Missing: cosium_id, customer_number, street_number, street_name, optician_name, ophthalmologist_id, mobile_phone_country, site_id
- Impact: Client detail pages won't show Cosium sync data, address components, etc.
- FIX: Add missing fields to Customer interface

### 24-2 [LOW] Frontend AuditLog type missing user_email field
- File: frontend/src/lib/types/index.ts - AuditLog interface
- Backend AuditLogResponse has user_email: str | None
- Impact: Audit log display can't show who performed the action by email
- FIX: Add user_email to AuditLog interface

### 24-3 [CRITICAL] Frontend hooks call non-existent backend endpoints
- useCosiumPrescriptions() calls /cosium/prescriptions -> backend has NO /cosium/prescriptions endpoint
- useCosiumPayments() calls /cosium/payments -> backend has NO /cosium/payments endpoint
- Impact: These pages will get 404 errors
- FIX: Add /prescriptions and /payments endpoints to cosium_reference router

### 24-4 [MEDIUM] Frontend CosiumPaymentItem type doesn't match backend CosiumPaymentResponse
- Frontend: { id, amount, type, due_date, issuer_name, bank, site_name, payment_number }
- Backend CosiumPaymentResponse: { id, tenant_id, cosium_id, payment_type_id, amount, original_amount, type, due_date, issuer_name, bank, site_name, comment, payment_number, invoice_cosium_id, synced_at }
- Impact: Extra backend fields ignored (OK), but frontend type is a subset
- Note: This is fine for display purposes

### 24-5 [MEDIUM] Frontend CosiumPrescription type doesn't match backend CosiumPrescriptionResponse
- Frontend missing: tenant_id, cosium_id, file_date, customer_cosium_id, customer_id, spectacles_json, synced_at
- Impact: Prescription detail won't have all data available
- FIX: Add missing fields to CosiumPrescription interface
