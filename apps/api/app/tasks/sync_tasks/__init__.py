"""Package sync_tasks : tasks Celery de synchronisation ERP.

Extrait de `sync_tasks.py` mono-fichier pour maintenabilité. Chaque sous-module
porte une task Celery autonome (avec son `name="app.tasks.sync_tasks.xxx"`
hardcodé, donc compatible avec le routing `"app.tasks.sync_tasks.*"` et
les beat schedules existants).

Sous-modules (l'import déclenche l'enregistrement des tasks côté Celery) :
- `_sync_all.py` : `sync_all_tenants` (daily 6h) + helper `_sync_single_tenant`
- `_connectivity.py` : `test_cosium_connection` (toutes les 4h) +
  helper `_test_tenant_connection`
- `_bulk_download.py` : `bulk_download_cosium_documents` (on-demand)
- `_prescriptions.py` : `check_expiring_prescriptions` (weekly Monday 10h)

Préserve les imports publics existants :
- `from app.tasks.sync_tasks import sync_all_tenants` (etc.)
- `from app.tasks.sync_tasks import bulk_download_cosium_documents`
  (utilisé dans `routers/cosium_documents.py`)
"""

from ._bulk_download import bulk_download_cosium_documents
from ._connectivity import test_cosium_connection
from ._prescriptions import check_expiring_prescriptions
from ._sync_all import sync_all_tenants

__all__ = [
    "sync_all_tenants",
    "test_cosium_connection",
    "bulk_download_cosium_documents",
    "check_expiring_prescriptions",
]
