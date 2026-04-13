# ADR-0002 — Multi-tenant via `tenant_id` colonne (vs schemas séparés vs DBs séparées)

**Date** : 2026-04-11
**Statut** : Accepted

## Contexte

OptiFlow vise un modèle SaaS multi-tenant : 1 tenant = 1 magasin opticien.
Roadmap : 50+ tenants à terme, dont certains regroupés en organizations (réseaux franchisés).

## Options évaluées

### A. Database par tenant
- **+** Isolation totale (zero risque cross-tenant)
- **+** Possible per-tenant scaling
- **−** Migrations à appliquer N fois
- **−** Coût opérationnel (50 connexions, 50 backups)
- **−** Pas de queries cross-tenant pour group admin

### B. Schema PostgreSQL par tenant
- **+** Isolation forte
- **−** Migrations N fois (slightly easier que A)
- **−** Connection pooling complexe (search_path)
- **−** Pas natif SQLAlchemy

### C. **Colonne `tenant_id` partout (CHOIX)**
- **+** 1 BDD, 1 schema, queries simples
- **+** Group admin via `WHERE tenant_id IN (...)`
- **+** Scaling vertical PostgreSQL OK jusqu'à 1000+ tenants
- **−** Risque de bug cross-tenant si dev oublie le filter (mitigation: tests)

## Décision

Option C : `tenant_id` sur toutes les tables business + filtre OBLIGATOIRE dans toutes
les queries (enforced par tests + RLS PostgreSQL en backup).

## Implémentation

- Modèles : `tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)`
- Index composite `(tenant_id, ...)` sur tous les filtres fréquents
- `TenantContext` dependency injection : extrait du JWT, propagé dans toutes les routes
- `tests/test_tenant_isolation.py` : 3 tests vérifient qu'un user tenant A ne peut PAS voir tenant B
- Soft enforcement en CI : `test_architecture.py` vérifie pas de queries sans tenant_id

## Conséquences

**Positives**
- Simplicité opérationnelle (1 backup, 1 migration)
- Group admin natif
- Connection pooling standard

**Négatives**
- Risque cross-tenant si bug applicatif (mitigé par tests + RLS futur)
- Backup full-tenant impossible sans dump filtré

## À surveiller

- Si > 500 tenants : envisager partitioning PostgreSQL par `tenant_id`
- Activation Row-Level Security PostgreSQL en backup applicatif (à faire P2)
