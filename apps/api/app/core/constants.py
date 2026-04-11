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
PEC_EN_ATTENTE = "en_attente"
PEC_ACCEPTEE = "acceptee"
PEC_REFUSEE = "refusee"
PEC_PARTIELLE = "partielle"
PEC_CLOTUREE = "cloturee"
PEC_PRETE = "prete"

# ---------------------------------------------------------------------------
# Statuts reconciliation
# ---------------------------------------------------------------------------
RECON_SOLDE = "solde"
RECON_SOLDE_NON_RAPPROCHE = "solde_non_rapproche"
RECON_PARTIELLEMENT_PAYE = "partiellement_paye"
RECON_EN_ATTENTE = "en_attente"
RECON_INCOHERENT = "incoherent"
RECON_INFO_INSUFFISANTE = "info_insuffisante"

# ---------------------------------------------------------------------------
# Niveaux de confiance reconciliation
# ---------------------------------------------------------------------------
CONFIDENCE_CERTAIN = "certain"
CONFIDENCE_PROBABLE = "probable"
CONFIDENCE_PARTIEL = "partiel"
CONFIDENCE_INCERTAIN = "incertain"

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
