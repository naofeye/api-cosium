"""Package sync : router composite qui agrège les 3 sous-modules.

Sous-modules (tous avec prefix `/api/v1/sync` + tag `sync`) :
- `_meta.py` : GET /status, GET /erp-types, POST /seed-demo
- `_domains.py` : 9 POST per-domain (customers, invoices, products,
  invoiced-items, payments, third-party-payments, prescriptions,
  enrich-clients, import-cosium-quotes). Chacun avec lock Redis
  dédié + cache invalidation.
- `_all.py` : POST /all — orchestration multi-domaine déléguée à
  `erp_sync_service.sync_all()`.

Préserve l'import public `from app.api.routers.sync import router`
(identique à l'ancien module `sync.py` mono-fichier 420 L).
"""

from fastapi import APIRouter

from . import _all, _domains, _meta

router = APIRouter()
router.include_router(_meta.router)
router.include_router(_domains.router)
router.include_router(_all.router)
