"""Helpers internes pour reconciliation_service.

Decoupage extrait pour reduire la taille du service principal :
- normalisation/matching de noms (link_payments_to_customers)
- classification de paiements par type (TPSV/TPMV/CB...)
- determination du statut de reconciliation (machine d'etat)
- detection d'anomalies financieres
- formatage de l'explication humaine
"""
import re
import unicodedata

from app.core.constants import (
    CONFIDENCE_CERTAIN,
    CONFIDENCE_INCERTAIN,
    CONFIDENCE_PARTIEL,
    CONFIDENCE_PROBABLE,
    RECON_EN_ATTENTE,
    RECON_INCOHERENT,
    RECON_INFO_INSUFFISANTE,
    RECON_PARTIELLEMENT_PAYE,
    RECON_SOLDE,
    RECON_SOLDE_NON_RAPPROCHE,
)
from app.domain.schemas.reconciliation import AnomalyItem

# Tolerance pour comparaison financiere (euros).
# float (et non Decimal) : les modeles CosiumInvoice/CosiumPayment utilisent Float,
# les fonctions de ce module recoivent donc des floats. Mixer Decimal+float = TypeError.
TOLERANCE = 0.02

# Payment type → category mapping
_SECU_TYPES = {"TPSV"}
_MUTUELLE_TYPES = {"TPMV"}
_CLIENT_TYPES = {"CB", "CHQ", "ESP", "ALMA", "VIR"}
_AVOIR_TYPES = {"AV"}


def normalize_name(name: str) -> str:
    """Normalize : lowercase, strip accents, replace hyphens with spaces, remove punctuation."""
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Replace hyphens with spaces before removing other punctuation
    spaced = ascii_str.replace("-", " ")
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", spaced.lower())
    return " ".join(cleaned.split())


def names_match(name_a: str, name_b: str) -> bool:
    """Check exact normalized match or token subset match."""
    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    if len(tokens_a) < 2 or len(tokens_b) < 2:
        return False
    shorter, longer = (tokens_a, tokens_b) if len(tokens_a) <= len(tokens_b) else (tokens_b, tokens_a)
    return shorter.issubset(longer)


def classify_payment(payment_type: str) -> str:
    """Classify payment type into category : secu / mutuelle / avoir / client."""
    upper = payment_type.strip().upper()
    if upper in _SECU_TYPES:
        return "secu"
    if upper in _MUTUELLE_TYPES:
        return "mutuelle"
    if upper in _AVOIR_TYPES:
        return "avoir"
    return "client"


def determine_reconciliation_status(
    *,
    total_facture: float,
    total_paid: float,
    total_outstanding: float,
    has_invoices: bool,
    has_payments: bool,
    has_unmatched: bool,
    has_anomalies: bool,
) -> tuple[str, str]:
    """Etat global + niveau de confiance, base sur totaux financiers et flags."""
    if not has_invoices:
        return RECON_INFO_INSUFFISANTE, CONFIDENCE_INCERTAIN

    if abs(total_outstanding) < TOLERANCE:
        if has_unmatched:
            return RECON_SOLDE_NON_RAPPROCHE, CONFIDENCE_PROBABLE
        return RECON_SOLDE, CONFIDENCE_CERTAIN

    if total_paid > TOLERANCE and total_outstanding > TOLERANCE:
        confidence = CONFIDENCE_PROBABLE if not has_anomalies else CONFIDENCE_PARTIEL
        return RECON_PARTIELLEMENT_PAYE, confidence

    if total_paid < TOLERANCE:
        return RECON_EN_ATTENTE, CONFIDENCE_CERTAIN

    return RECON_INCOHERENT, CONFIDENCE_INCERTAIN


def determine_pec_status(invoices, total_secu: float, total_mutuelle: float) -> str | None:
    """Statut PEC selon presence de factures avec part secu/mutuelle."""
    has_pec = any(i.share_social_security > 0 or i.share_private_insurance > 0 for i in invoices)
    if not has_pec:
        return None
    if total_secu > 0 and total_mutuelle > 0:
        return "secu_et_mutuelle"
    if total_secu > 0:
        return "secu_uniquement"
    if total_mutuelle > 0:
        return "mutuelle_uniquement"
    return "en_attente_pec"


def determine_invoice_status(*, settled: bool, outstanding: float, paid: float, total_ti: float) -> str:
    """Statut d'une facture individuelle."""
    if settled or abs(outstanding) < TOLERANCE:
        return RECON_SOLDE
    if paid > TOLERANCE and outstanding > TOLERANCE:
        return RECON_PARTIELLEMENT_PAYE
    return RECON_EN_ATTENTE


def detect_overpayment_anomaly(*, paid: float, total_ti: float, invoice_number: str | None) -> AnomalyItem | None:
    """Detecte un surpaiement sur une facture. None si pas d'anomalie."""
    if paid <= total_ti + TOLERANCE:
        return None
    return AnomalyItem(
        type="surpaiement",
        severity="error",
        message=f"Paiements ({paid:.2f} EUR) superieurs au TTC ({total_ti:.2f} EUR)",
        invoice_number=invoice_number,
        amount=paid - total_ti,
    )


def build_explanation(
    *,
    invoice_count: int,
    total_facture: float,
    total_outstanding: float,
    total_secu: float,
    total_mutuelle: float,
    total_client: float,
    total_avoir: float,
) -> str:
    """Phrase humaine resumant l'etat financier du dossier."""
    parts = [f"{invoice_count} facture(s) pour {total_facture:.2f} EUR TTC."]
    if total_outstanding > TOLERANCE:
        parts.append(f"Solde restant du : {total_outstanding:.2f} EUR.")
    else:
        parts.append("Toutes les factures sont soldees.")
    if total_secu > 0:
        parts.append(f"Secu : {total_secu:.2f} EUR.")
    if total_mutuelle > 0:
        parts.append(f"Mutuelle : {total_mutuelle:.2f} EUR.")
    if total_client > 0:
        parts.append(f"Client : {total_client:.2f} EUR.")
    if total_avoir > 0:
        parts.append(f"Avoirs : {total_avoir:.2f} EUR.")
    return " ".join(parts)
