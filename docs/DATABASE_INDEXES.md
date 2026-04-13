# Stratégie d'indexation BDD OptiFlow

> Tous les indexes sont declares dans les modeles SQLAlchemy via `Index(...)` ou `index=True`.
> Les `(tenant_id, ...)` composites sont OBLIGATOIRES : isolation multi-tenant + perf.

## Principes

1. **Tout `tenant_id` est indexe** (filtre present sur ~100% des queries)
2. **Composites `(tenant_id, status, created_at)`** pour les listes filtrees + triees
3. **`UNIQUE (tenant_id, cosium_id)`** sur tables Cosium pour upsert idempotent
4. **Index partiel** `WHERE deleted_at IS NULL` pour soft-delete
5. **Foreign keys** indexees auto par PostgreSQL si declarees `ForeignKey()`

## Index par table (current state)

| Table | Index principal | Justification |
|---|---|---|
| `customers` | `(tenant_id, deleted_at)` | Liste clients tenant filtree soft-delete |
| `customers` | `(tenant_id, cosium_id)` UNIQUE | Upsert sync Cosium |
| `customers` | `(tenant_id, email)` partial WHERE email NOT NULL | Recherche email |
| `cases` | `(tenant_id, status, created_at)` | Liste filtree par statut |
| `cases` | `(customer_id, tenant_id)` | Cases d'un client |
| `documents` | `(case_id, tenant_id)` | Documents d'un dossier |
| `payments` | `(case_id, tenant_id, status)` | Paiements en attente |
| `notifications` | `(user_id, tenant_id, is_read, created_at DESC)` | Liste notifs non-lues recente |
| `audit_logs` | `(tenant_id, entity_type, entity_id)` | Audit d'une entite |
| `audit_logs` | `(tenant_id, created_at DESC)` | Logs recents |
| `pec_requests` | `(tenant_id, status)` | PEC en attente reponse mutuelle |
| `cosium_invoices` | `(tenant_id, status, created_at)` | Liste factures impayees triee |
| `cosium_invoices` | `(tenant_id, customer_cosium_id)` | Factures d'un client (lookup) |
| `cosium_payments` | `(tenant_id, cosium_id)` UNIQUE | Upsert sync |
| `cosium_payments` | `(tenant_id, customer_id)` | Paiements client |
| `cosium_payments` | `(tenant_id, invoice_cosium_id)` | Reconciliation paiement-facture |
| `cosium_documents` | `(tenant_id, customer_cosium_id)` | Documents d'un client |
| `document_extractions` | `(tenant_id, document_id)` UNIQUE | 1 extraction max par doc |
| `document_extractions` | `(tenant_id, document_type)` | Stats par type OCR |
| `client_mutuelles` | `(customer_id, tenant_id, active)` | Mutuelles actives client |
| `marketing_consents` | `(client_id, tenant_id, channel)` UNIQUE | Upsert opt-in/opt-out |
| `marketing_segments` | `(tenant_id, name)` UNIQUE | Pas de doublons |
| `reminder_plans` | `(tenant_id, is_active)` | Plans actifs cron |
| `bank_transactions` | `(tenant_id, reconciled, date)` | Transactions non rapprochees |
| `tenant_users` | `(user_id, tenant_id)` UNIQUE | 1 record par user-tenant |

## Index a verifier / ajouter (TODO)

- [x] Cosium* (CosiumInvoice, CosiumDocument, CosiumPayment) : `(tenant_id, status, created_at)`
- [x] `marketing_consents (client_id, tenant_id, channel)` UNIQUE
- [ ] `interactions (customer_id, tenant_id, created_at DESC)` — pour timeline client 360
- [ ] `notifications (user_id, tenant_id, is_read, created_at DESC)` — verifier en prod
- [ ] `audit_logs (tenant_id, created_at DESC)` — utile pour /admin/audit-logs

## Comment auditer en prod

```sql
-- Top 20 queries lentes via pg_stat_statements
SELECT query, calls, mean_exec_time, rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Tables sans index sur foreign key
SELECT c.conrelid::regclass AS table_name, a.attname AS column_name
FROM pg_constraint c
JOIN pg_attribute a ON a.attnum = ANY(c.conkey) AND a.attrelid = c.conrelid
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
  );

-- Index inutilises (idx_scan = 0 depuis demarrage stats)
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 20;

-- Tables avec full scans frequents
SELECT relname, seq_scan, seq_tup_read, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan AND seq_scan > 1000
ORDER BY seq_scan DESC;
```

## Ajouter un index en prod (sans downtime)

```python
# Migration Alembic
def upgrade() -> None:
    # CONCURRENTLY = pas de lock table (postgres only)
    op.execute("COMMIT")
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
        "ix_customers_tenant_email ON customers(tenant_id, email) "
        "WHERE email IS NOT NULL"
    )

def downgrade() -> None:
    op.execute("COMMIT")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_customers_tenant_email")
```

## Anti-patterns

```python
# ❌ Index sur colonne ENUM ou booleen seul (cardinalite faible)
Index("ix_users_is_active", User.is_active)  # NON : 99% True

# ✅ Composite avec filtre selectif
Index("ix_users_active_tenant", User.tenant_id, User.is_active)

# ❌ Index sur colonne text large
Index("ix_documents_content", Document.content)  # NON : utiliser FTS GIN

# ✅ FTS GIN si recherche texte
Index("ix_documents_content_fts", func.to_tsvector("french", Document.content),
      postgresql_using="gin")
```

## Maintenance

```bash
# Reindex complet (offline only)
docker compose exec postgres reindexdb -U optiflow

# Vacuum analyze (online)
docker compose exec postgres vacuumdb -U optiflow --analyze

# Stats indexes utilisation
docker compose exec postgres psql -U optiflow -c "
  SELECT relname, idx_scan, idx_tup_read, idx_tup_fetch
  FROM pg_stat_user_indexes
  ORDER BY idx_scan DESC LIMIT 20;
"
```
