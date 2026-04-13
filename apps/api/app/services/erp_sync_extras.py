"""
Service de synchronisation ERP -> OptiFlow : facade.

Decoupage en modules specialises :
- erp_sync_products.py
- erp_sync_payments.py
- erp_sync_third_party.py
- erp_sync_prescriptions.py
- _erp_sync_helpers.py (BATCH_SIZE, helpers parsing/lookup/commit)

SYNCHRONISATION UNIDIRECTIONNELLE : ERP -> OptiFlow uniquement.
Aucune ecriture vers l'ERP. Voir CLAUDE.md (regle Cosium read-only).

Re-exports pour compatibilite ascendante :
  from app.services.erp_sync_extras import sync_payments, ...
  from app.services import erp_sync_extras
  erp_sync_extras.sync_products(...)
"""

from app.services._erp_sync_helpers import BATCH_SIZE  # noqa: F401
from app.services.erp_sync_payments import sync_payments  # noqa: F401
from app.services.erp_sync_prescriptions import sync_prescriptions  # noqa: F401
from app.services.erp_sync_products import sync_products  # noqa: F401
from app.services.erp_sync_third_party import sync_third_party_payments  # noqa: F401
