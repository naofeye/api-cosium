# RBAC — Roles & Permissions OptiFlow

> Roles definis dans `app/models/tenant_user.py` (champ `role`).
> Les endpoints utilisent `require_tenant_role(*allowed_roles)` pour enforcer.

## Roles disponibles

| Role | Description | Cas d'usage |
|------|-------------|-------------|
| `admin` | Acces complet sur le tenant | Gerant magasin |
| `manager` | Lecture + ecriture metier, pas d'admin tech | Responsable comptable |
| `operator` | Operations courantes (clients, devis, paiements) | Opticien, secretaire |
| `viewer` | Lecture seule | Stagiaire, consultation client |

Plus le role `is_group_admin` (booleen sur `User`) pour la gestion **multi-tenant** (vue groupe). Independant des roles tenant.

## Matrice permissions par module

| Module / endpoint | viewer | operator | manager | admin | group_admin |
|---|:-:|:-:|:-:|:-:|:-:|
| **Auth** |
| `/auth/login`, `/refresh`, `/logout` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/auth/switch-tenant` | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Clients** |
| `GET /clients`, `GET /clients/:id` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /clients`, `PATCH /clients/:id` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `DELETE /clients/:id` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `POST /clients/import` (CSV) | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Devis & Factures** |
| `GET /devis`, `GET /factures` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /devis`, `PATCH /devis/:id` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `POST /factures` | ❌ | ✅ | ✅ | ✅ | ✅ |
| **PEC** |
| `GET /pec`, `GET /pec-preparations` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /pec`, `POST /pec-preparations/*/submit` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `PATCH /pec/*/status`, `POST /pec-preparations/*/correct-field` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `POST /payer-organizations` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `GET /pec-preparations/export` | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Batch operations** |
| `GET /batch`, `GET /batch/*` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /batch/create`, `POST /batch/*/process`, `POST /batch/*/prepare-pec` | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Reconciliation** |
| `GET /reconciliation/*` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /reconciliation/link-payments`, `POST /reconciliation/run` | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Documents** |
| `GET /cases/*/documents`, `GET /documents/*/download` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /cases/*/documents` (upload) | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Interactions** |
| `GET /clients/*/interactions`, `GET /clients/*/timeline` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /interactions`, `POST /clients/*/send-email` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `DELETE /interactions/*` | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Relances (reminders)** |
| `GET /reminders/*` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /reminders` (create), `POST /reminders/*/send` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `POST /reminders/plans`, `POST /reminders/plans/*/execute`, `PATCH /reminders/plans/*/toggle` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `POST /reminders/auto-generate`, `POST /reminders/templates` | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Consents** |
| `GET /clients/*/consents` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `PUT /clients/*/consents/*` | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Paiements & Banking** |
| `GET /banking/transactions` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /banking/import-statement` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `POST /banking/match` | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Marketing** |
| `GET /marketing/*` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /marketing/campaigns` | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Cosium sync** |
| `GET /cosium-*` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /cosium/sync` | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Admin tenant** |
| `GET /admin/users` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `POST /admin/users`, `PATCH/DELETE /admin/users/:id` | ❌ | ❌ | ❌ | ✅ | ✅ |
| `GET /audit-logs` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `GET /admin/data-quality` | ❌ | ❌ | ✅ | ✅ | ✅ |
| `GET /admin/metrics` (cache 5min) | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Health** |
| `GET /admin/health` | ✅ public (no auth) |
| **Group admin** (multi-tenant) |
| `GET /admin/group-dashboard` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `GET /admin/tenants` | ❌ | ❌ | ❌ | ❌ | ✅ |

## Implementation

```python
# Endpoint admin-only sur un tenant
@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
    db: Session = Depends(get_db),
) -> User:
    return user_service.deactivate(db, tenant_ctx.tenant_id, user_id)

# Endpoint manager+ (manager OU admin)
@router.post("/sync/cosium")
def sync_cosium(
    tenant_ctx: TenantContext = Depends(require_tenant_role("manager", "admin")),
) -> SyncResponse: ...

# Endpoint group admin (multi-tenant)
@router.get("/group-dashboard")
def group_dashboard(
    user: User = Depends(require_group_admin),
) -> GroupDashboardResponse: ...
```

## Tests

`tests/test_admin_auth.py` valide :
- 401/403 sans token sur `/admin/*`
- 401/403 avec un user `operator` sur `/admin/users`, `/audit-logs`

`tests/test_tenant_isolation.py` valide :
- User tenant A ne voit jamais les donnees tenant B (filter `tenant_id` partout)

## Anti-patterns INTERDITS

```python
# ❌ Pas de check de role en dur dans le router
@router.get("/sensitive")
def sensitive(user: User = Depends(get_current_user)):
    if user.role != "admin":  # NON
        raise HTTPException(403)

# ✅ Toujours via dependency injection
@router.get("/sensitive")
def sensitive(ctx = Depends(require_tenant_role("admin"))): ...
```

## Changements

Pour ajouter un role :
1. Ajouter le role dans `app/models/tenant_user.py` (constantes)
2. Mettre a jour la matrice ci-dessus
3. Ajouter un test dans `tests/test_admin_auth.py` parametrise
4. Communiquer aux clients (impact UI : selection role dans `/admin/users`)
