"""Package cosium_reference : router composite qui agrège les 4 sous-modules.

Sous-modules (tous avec prefix `/api/v1/cosium` + tag `cosium-reference`) :
- `_sync.py` : POST /sync-reference, POST /sync-customer-tags
- `_calendar.py` : GET /calendar-events (list/upcoming/detail) + /calendar-event-categories
- `_entities.py` : GET listings simples (mutuelles, doctors, brands, suppliers,
  tags, sites, banks, companies, users, equipment-types, frame-materials)
- `_data.py` : GET paginés avec recherche (prescriptions, payments, products)

Préserve l'import public `from app.api.routers.cosium_reference import router`
(identique à l'ancien module `cosium_reference.py` mono-fichier 401 L).
"""

from fastapi import APIRouter

from . import _calendar, _data, _entities, _sync

router = APIRouter()
router.include_router(_sync.router)
router.include_router(_calendar.router)
router.include_router(_entities.router)
router.include_router(_data.router)
