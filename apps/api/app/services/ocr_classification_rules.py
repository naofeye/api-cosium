"""OCR document classification keyword rules.

Extracted from ocr_handlers.py to keep files under 300 lines.
Each rule is a (document_type, keywords) tuple where keywords are regex patterns.
"""

CLASSIFICATION_RULES: list[tuple[str, list[str]]] = [
    (
        "ordonnance",
        [
            "ordonnance", "prescription", "sphere", r"sph[eè]re", "cylindre",
            "addition", r"\bOD\b", r"\bOG\b", "acuite", "correction", "dioptrie",
            "oeil droit", "oeil gauche", "vision de loin", "vision de pr", "ophtalmolog",
        ],
    ),
    (
        "devis",
        [
            "devis", "montant ttc", "montant ht", "reste a charge",
            r"reste\s*[àa]\s*charge", r"part\s+(secu|mutuelle)", "total ttc",
            "monture", "verres", "equipement optique", "bon de commande",
            r"base\s+de\s+remboursement",
        ],
    ),
    (
        "attestation_mutuelle",
        [
            "attestation", "mutuelle", "organisme complementaire", "numero adherent",
            r"n[°o]\s*adherent", "droits ouverts", "date de validite", "tiers payant",
            "carte tiers", r"\bamc\b", r"b[eé]n[eé]ficiaire",
        ],
    ),
    (
        "facture",
        [
            "facture", r"n[°o]\s*facture", "montant ttc", "montant ht", r"\btva\b",
            "net a payer", "reglement", "echeance", r"\btotal\s+ttc\b",
        ],
    ),
    (
        "carte_mutuelle",
        [
            "carte mutuelle", "carte de tiers payant", "organisme",
            r"n[°o]\s*adherent", "code organisme", "regime obligatoire", r"\bamc\b",
        ],
    ),
    (
        "bon_livraison",
        [
            "bon de livraison", "livraison", "remis ce jour", r"bl\s*n[°o]",
            "bordereau de livraison", "reception",
        ],
    ),
    (
        "fiche_opticien",
        [
            "fiche opticien", "fiche client", "opticien", "prise de mesure",
            r"ecart\s+pupillaire", "hauteur de montage",
        ],
    ),
    (
        "fiche_ophtalmo",
        [
            "fiche ophtalmo", "ophtalmologue", "examen", "fond d'oeil",
            r"fond\s+d.oeil", "tension oculaire", "bilan ophtalmologique",
        ],
    ),
    (
        "consentement_rgpd",
        [
            "consentement", r"\brgpd\b", r"donn[eé]es personnelles",
            "traitement", "protection des donnees", "droit d'acces",
        ],
    ),
    (
        "feuille_soins",
        [
            "feuille de soins", "feuille de soin", "organisme",
            r"s[eé]curit[eé] sociale", r"\bamo\b",
            r"n[°o]\s*de\s*s[eé]curit[eé]", "assurance maladie",
        ],
    ),
    (
        "prise_en_charge",
        [
            "prise en charge", r"\bpec\b", "accord de prise en charge",
            r"accord\s+pr[eé]alable", "demande de prise en charge",
        ],
    ),
    (
        "courrier",
        [
            "madame, monsieur", "veuillez agr", "cordialement", "objet :",
            r"r[eé]f[eé]rence\s*:", "nous vous prions",
        ],
    ),
    (
        "releve_bancaire",
        [
            r"relev[eé]\s+(de\s+)?compte", r"relev[eé]\s+bancaire",
            "solde crediteur", "solde debiteur", r"\biban\b", r"\bbic\b", "mouvement",
        ],
    ),
]
