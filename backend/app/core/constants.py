"""Application-wide constants — status strings, roles, pagination defaults.

Import from here instead of using magic strings in services/routers.
Migration to these constants will happen progressively.
"""

# ---------------------------------------------------------------------------
# Statuts dossiers (Case.status)
# ---------------------------------------------------------------------------
STATUS_DRAFT = "draft"
STATUS_EN_COURS = "en_cours"
STATUS_COMPLET = "complet"
STATUS_ARCHIVE = "archive"

# ---------------------------------------------------------------------------
# Statuts devis (Devis.status)
# ---------------------------------------------------------------------------
DEVIS_BROUILLON = "brouillon"
DEVIS_ENVOYE = "envoye"
DEVIS_SIGNE = "signe"
DEVIS_REFUSE = "refuse"

# ---------------------------------------------------------------------------
# Statuts factures (Facture.status)
# ---------------------------------------------------------------------------
FACTURE_EMISE = "emise"
FACTURE_PAYEE = "payee"

# ---------------------------------------------------------------------------
# Statuts PEC (PecRequest.status)
# ---------------------------------------------------------------------------
PEC_SOUMISE = "soumise"
PEC_ACCEPTEE = "acceptee"
PEC_REFUSEE = "refusee"

# ---------------------------------------------------------------------------
# Roles utilisateur
# ---------------------------------------------------------------------------
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
